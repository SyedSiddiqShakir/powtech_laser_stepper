import serial
import time
import dearpygui.dearpygui as dpg
import sys
import win32api
import win32con
import win32gui
from collections import deque

class StepperController:
    # constants
    # changing speed is not available here, that is in the arduino code
    STEPS_PER_REV = 1600
    MM_PER_REV = 0.5
    STEPS_PER_MM = STEPS_PER_REV / MM_PER_REV
    MAX_RANGE_MM = 50.0

    def __init__(self, port='COM5', baudrate=115200):
        self.arduino = None
        self.pos = 0 
        self.command_queue = deque()
        self.is_busy = False
        try:
            self.arduino = serial.Serial(port, baudrate, timeout=0.1)
            print(f"Successfully connected to {port}.")
            time.sleep(2)
        except serial.SerialException as e:
            print(f"Error: Could not open port {port}. {e}")
            self.arduino = None

    def send_command(self, cmd, value=None):
        if self.arduino and self.arduino.is_open:
            message = f"{cmd}\n" if value is None else f"{cmd}{int(value)}\n"
            self.arduino.write(message.encode('ascii'))
        else:
            print("Error: Arduino not connected.")

    def move_relative_mm(self, distance_mm):
        steps_to_move = int(distance_mm * self.STEPS_PER_MM)
        self.pos += steps_to_move
        self.command_queue.append(self.pos)
        self.update_display()

    def move_to_mm(self, target_mm):
        if target_mm is not None:
            target_steps = int(target_mm * self.STEPS_PER_MM)
            self.pos = target_steps
            self.command_queue.append(self.pos)
            self.update_display()

    def _process_queue(self):
        if not self.is_busy and self.command_queue:
            target_pos_steps = self.command_queue.popleft() 
            self.is_busy = True
            self.send_command('M', target_pos_steps)

    def update(self):
        if self.arduino and self.arduino.in_waiting > 0:
            try:
                line = self.arduino.readline().decode('ascii').strip()
                if line.startswith("POS:"):
                    loaded_pos = int(line[4:])
                    self.pos = loaded_pos
                    self.update_display()
                    print(f"Confirmation: Position loaded from EEPROM ({self.pos} steps)")
                elif line == "OK":
                    self.is_busy = False
                elif line == "SAVED":
                    print(f"Confirmation: Position successfully saved to device EEPROM. ({self.pos})")
            except (UnicodeDecodeError, ValueError):
                pass
        self._process_queue()
        
    def update_display(self):
        if not dpg.is_dearpygui_running(): return
        mm_pos = self.pos / self.STEPS_PER_MM
        if dpg.does_item_exist("main_pos_display"):
            dpg.set_value("main_pos_display", f"Current position: {mm_pos:.3f} mm")
        if dpg.does_item_exist("pos_progress_bar"):
            fraction = max(0.0, min(1.0, mm_pos / self.MAX_RANGE_MM))
            dpg.set_value("pos_progress_bar", fraction)
            dpg.configure_item("pos_progress_bar", overlay=f"{mm_pos:.2f} / {self.MAX_RANGE_MM:.1f} mm")

    def stop(self):
        self.command_queue.clear()
        self.send_command('S')
        self.is_busy = False
        
    def save_position_to_eeprom(self):

        if not (self.arduino and self.arduino.is_open):
            return
        
        print("Sending command to save position to Arduino's EEPROM...")
        self.arduino.read_all() #clear input buffer data
        self.send_command('P')

        start_time = time.time()
        while time.time() - start_time < 2.0:
            if self.arduino.in_waiting > 0:
                try:
                    line = self.arduino.readline().decode('ascii').strip()
                    if line == 'SAVED':
                        print("Confirmation received: Position saved")
                        return
                except (UnicodeDecodeError, ValueError):
                    pass
        print("Warning: did not recieve confirmation from arduino") 

    def load_position_from_eeprom(self):
        print("Requesting saved position from Arduino's EEPROM...")
        self.send_command('L')
    
    def close(self):
        #Only closes the serial port. Window cleanup is handled elsewhere
        if self.arduino and self.arduino.is_open:
            self.save_position_to_eeprom()
            self.arduino.close()
            print("Arduino connection closed.")

    def open_set_position_window(self):
        if not dpg.does_item_exist("set_pos_window"):
            with dpg.window(label="Calibrate Position", tag="set_pos_window", width=600, height=400):
                dpg.add_text("Enter the correct current position in mm.")
                dpg.add_input_float(tag="set_pos_input_mm", default_value=(self.pos / self.STEPS_PER_MM), width=240, format="%.3f")
                dpg.add_button(label="Set as Current Position", callback=self._set_position_callback)
        dpg.show_item("set_pos_window")

    def _set_position_callback(self):
        new_mm = dpg.get_value("set_pos_input_mm")
        if new_mm is not None:
            self.pos = int(new_mm * self.STEPS_PER_MM)
            print(f"Calibrating position to {new_mm:.3f} mm ({self.pos} steps).")
            self.send_command('C', self.pos)
            self.command_queue.clear()
            self.is_busy = False
            self.update_display()
            dpg.hide_item("set_pos_window")

# init controller
controller = StepperController()

# windows shutdown and sleep events handlers
def console_handler(event):
    if event in (win32con.CTRL_SHUTDOWN_EVENT, win32con.CTRL_LOGOFF_EVENT):
        print("Shutdown/Logoff detected. Saving position...")
        controller.save_position_to_eeprom()
        #time.sleep(0.5) # giving the save command time to send and process #removed it to add the delay in save function
        return True # Indicate that we've handled it (~handshake)
    return False

win32api.SetConsoleCtrlHandler(console_handler, True)

def wnd_proc(hwnd, msg, wparam, lparam):
    if msg == win32con.WM_POWERBROADCAST:
        if wparam == win32con.PBT_APMSUSPEND:
            print("Sleep detected. Saving position...")
            controller.save_position_to_eeprom()
            time.sleep(0.5)
    # call the default handler
    return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

# invisible window to receive messages
wc = win32gui.WNDCLASS()
wc.lpszClassName = 'ShutdownHandler'
wc.lpfnWndProc = wnd_proc
class_atom = win32gui.RegisterClass(wc)
hwnd = win32gui.CreateWindow(class_atom, "Shutdown Handler", 0, 0, 0, 0, 0, 0, 0, 0, None)

# GUI Setup
dpg.create_context()

if controller.arduino is None:
    dpg.destroy_context()
    # Clean up the invisible window before exiting
    win32gui.DestroyWindow(hwnd)
    win32gui.UnregisterClass(class_atom, None)
    sys.exit()

# font(optional) and main window setup
try:
    with dpg.font_registry():
        big_font = dpg.add_font("C:/Windows/Fonts/segoeui.ttf", 40)
except Exception as e:
    big_font = dpg.add_font(dpg.get_default_font(), 20)

with dpg.window(label="Control Panel", tag="main_window"):
    with dpg.group(horizontal=True):
        dpg.add_spacer(width=12)
        dpg.add_text("0.000 mm", tag="main_pos_display")
    dpg.bind_font(big_font)
    dpg.add_progress_bar(tag="pos_progress_bar", overlay="0.00 / 50.0 mm", width=-1)
    dpg.add_separator()
    dpg.add_text("Relative Move", color=(128,0,128))
    with dpg.tooltip(dpg.last_item()):
        dpg.add_text("Moves the desired Distance")
    with dpg.group(horizontal=True):
        dpg.add_button(label="<-- Left", callback=lambda: controller.move_relative_mm(-dpg.get_value("custom_mm")))
        dpg.add_input_float(tag="custom_mm", default_value=1.0, width=240, label="mm", format="%.3f", step=0.1)
        dpg.add_button(label="Right -->", callback=lambda: controller.move_relative_mm(dpg.get_value("custom_mm")))
    dpg.add_separator()
    dpg.add_text("Absolute Move", color=(128, 0, 128))
    with dpg.tooltip(dpg.last_item()):
        dpg.add_text("Moves to the desired position")
    with dpg.group(horizontal=True):
        dpg.add_input_float(tag="absolute_mm_input", default_value=25.0, label="Go to (mm)", format="%.3f", step=1.0)
        dpg.add_button(label="Go", callback=lambda: controller.move_to_mm(dpg.get_value("absolute_mm_input")))
    dpg.add_separator()
    with dpg.group(horizontal=True):
        dpg.add_button(label="STOP", callback=controller.stop, width=-1, height=150)
    dpg.add_separator()
    dpg.add_text("Position Memory", color=(128,0,128))
    with dpg.tooltip(dpg.last_item()):
        dpg.add_text("Manage positional memory")
    with dpg.group(horizontal=True):
        dpg.add_button(label="Calibrate Position", callback=controller.open_set_position_window)
        dpg.add_button(label="Save Position to Device", callback=controller.save_position_to_eeprom)
        dpg.add_button(label="Load Position from Device", callback=controller.load_position_from_eeprom)

controller.update_display()
dpg.create_viewport(title="Stepper Motor Control", width=900, height=700)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("main_window", True)

# main loop
while dpg.is_dearpygui_running():
    # pumping the Windows messages inside the main GUI loop.
    win32gui.PumpWaitingMessages()
    
    controller.update()
    dpg.render_dearpygui_frame()

# cleanip
controller.close()
dpg.destroy_context()

# cleaning the invisible window at last to still account for runtime event possibilities
win32gui.DestroyWindow(hwnd)
win32gui.UnregisterClass(class_atom, None)
print("Application closed.")