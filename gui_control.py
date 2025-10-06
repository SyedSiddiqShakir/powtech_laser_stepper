import serial
import time
import dearpygui.dearpygui as dpg
import sys
from collections import deque

class StepperController:
    # --- Constants ---
    STEPS_PER_REV = 1600
    MM_PER_REV = 0.5
    STEPS_PER_MM = STEPS_PER_REV / MM_PER_REV
    MAX_RANGE_MM = 50.0

    def __init__(self, port='COM5', baud=115200):
        self.arduino = None
        self.pos = 0 # ✅ MODIFIED: Always start at 0. User must explicitly load position.
        
        self.command_queue = deque()
        self.is_busy = False

        try:
            self.arduino = serial.Serial(port, baud, timeout=0.1)
            print(f"Successfully connected to {port}.")
            time.sleep(2)
            # ⛔️ REMOVED: No longer automatically retrieves position on startup.
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
                    # This handles the response from the 'L' (Load) command
                    loaded_pos = int(line[4:])
                    self.pos = loaded_pos
                    self.update_display()
                    print(f"Position loaded from EEPROM: {self.pos} steps")
                elif line == "OK":
                    self.is_busy = False
                elif line == 'SAVED':
                    print('Postion saved to EEPROM')
            except (UnicodeDecodeError, ValueError):
                pass
        self._process_queue()
        
    def update_display(self):
        if not dpg.is_dearpygui_running(): return
        mm_pos = self.pos / self.STEPS_PER_MM
        if dpg.does_item_exist("main_pos_display"):
            dpg.set_value("main_pos_display", f"{mm_pos:.3f} mm")
        if dpg.does_item_exist("pos_progress_bar"):
            fraction = max(0.0, min(1.0, mm_pos / self.MAX_RANGE_MM))
            dpg.set_value("pos_progress_bar", fraction)
            dpg.configure_item("pos_progress_bar", overlay=f"{mm_pos:.2f} / {self.MAX_RANGE_MM:.1f} mm")

    def stop(self):
        self.command_queue.clear()
        self.send_command('S')
        self.is_busy = False

    def close(self):
        if self.arduino and self.arduino.is_open:
            # ⛔️ REMOVED: No longer automatically saves position on close.
            self.arduino.close()
            print("Arduino connection closed.")
            
    # ✅ NEW: Explicit function to save the current position to EEPROM.
    def save_position_to_eeprom(self):
        """Sends the command to persist the current position on the Arduino."""
        print("Sending command to save position to Arduino's EEPROM...")
        self.send_command('P')

    # ✅ NEW: Explicit function to load the position from EEPROM.
    def load_position_from_eeprom(self):
        """Asks Arduino to load position from its EEPROM and report it back."""
        print("Requesting saved position from Arduino's EEPROM...")
        self.send_command('L') # Send the new 'L' command

    def open_set_position_window(self):
        if not dpg.does_item_exist("set_pos_window"):
            with dpg.window(label="Calibrate Position", tag="set_pos_window", width=800, height=400):
                dpg.add_text("Enter the correct current position in mm.")
                dpg.add_input_float(tag="set_pos_input_mm", default_value=(self.pos / self.STEPS_PER_MM), width=240, format="%.3f")
                dpg.add_button(label="Set as Current Position", callback=self._set_position_callback)
        dpg.show_item("set_pos_window")

    # ✅ MODIFIED: This now calibrates the position without moving the motor.
    def _set_position_callback(self):
        """Updates the software and Arduino's position without physical movement."""
        new_mm = dpg.get_value("set_pos_input_mm")
        if new_mm is not None:
            # 1. Update Python's internal position
            self.pos = int(new_mm * self.STEPS_PER_MM)
            print(f"Calibrating position to {new_mm:.3f} mm ({self.pos} steps).")
            
            # 2. Tell Arduino to update its internal position
            self.send_command('C', self.pos)
            
            # 3. Clear any pending moves to avoid confusion
            self.command_queue.clear()
            self.is_busy = False
            
            # 4. Update the display
            self.update_display()
            dpg.hide_item("set_pos_window")


# --- GUI Setup ---
dpg.create_context()
controller = StepperController()
if controller.arduino is None:
    dpg.destroy_context()
    sys.exit()

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
    dpg.add_text("Relative Move")
    with dpg.group(horizontal=True):
        dpg.add_button(label="<-- Left", callback=lambda: controller.move_relative_mm(-dpg.get_value("custom_mm")))
        dpg.add_input_float(tag="custom_mm", default_value=1.0, width=240, label="mm", format="%.3f", step=0.1)
        dpg.add_button(label="Right -->", callback=lambda: controller.move_relative_mm(dpg.get_value("custom_mm")))
    dpg.add_separator()
    with dpg.group(horizontal=True):
        dpg.add_button(label="STOP", callback=controller.stop, width=-1)
        
    dpg.add_separator()
    dpg.add_text("Position Memory")
    with dpg.group(horizontal=True):
        # ✅ MODIFIED: Button callbacks point to the new explicit functions
        dpg.add_button(label="Calibrate Position", callback=controller.open_set_position_window)
        dpg.add_button(label="Save Position to Device", callback=controller.save_position_to_eeprom)
        dpg.add_button(label="Load Position from Device", callback=controller.load_position_from_eeprom)

controller.update_display()
dpg.create_viewport(title="Stepper Motor Control", width=1000, height=500)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("main_window", True)

while dpg.is_dearpygui_running():
    controller.update()
    dpg.render_dearpygui_frame()

controller.close()
dpg.destroy_context()