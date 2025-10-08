import serial
import time
import dearpygui.dearpygui as dpg
import sys
from collections import deque

#direction change DONE
#speed reduce DONE

#grip
#wobble

class StepperController:
    # --- Constants ---
    STEPS_PER_REV = 1600
    MM_PER_REV = 0.5
    STEPS_PER_MM = STEPS_PER_REV / MM_PER_REV
    MAX_RANGE_MM = 50.0

    def __init__(self, port='COM5', baud=115200):
        self.arduino = None
        self.pos = 0 
        
        self.command_queue = deque()
        self.is_busy = False

        try:
            self.arduino = serial.Serial(port, baud, timeout=0.1)
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
        # This function moves BY a certain amount
        steps_to_move = int(distance_mm * self.STEPS_PER_MM)
        self.pos += steps_to_move
        self.command_queue.append(self.pos)
        self.update_display()

    # ✅ NEW: Function to move TO a specific millimeter position.
    def move_to_mm(self, target_mm):
        """Calculates an absolute target position and adds it to the command queue."""
        if target_mm is not None:
            # You can add checks here to constrain the motion, e.g.:
            # if not (0 <= target_mm <= self.MAX_RANGE_MM):
            #     print(f"Error: Target {target_mm} mm is outside the valid range.")
            #     return

            # Convert the absolute mm target to an absolute step target
            target_steps = int(target_mm * self.STEPS_PER_MM)
            
            # Update the internal position to the new target
            self.pos = target_steps
            
            # Add the absolute step position to the queue
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
                    print("Confirmation: Position successfully saved to device EEPROM.")
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
            self.arduino.close()
            print("Arduino connection closed.")
            
    def save_position_to_eeprom(self):
        print("Sending command to save position to Arduino's EEPROM...")
        self.send_command('P')

    def load_position_from_eeprom(self):
        print("Requesting saved position from Arduino's EEPROM...")
        self.send_command('L')

    def open_set_position_window(self):
        if not dpg.does_item_exist("set_pos_window"):
            with dpg.window(label="Calibrate Position", tag="set_pos_window", width=350, height=150):
                dpg.add_text("Enter the correct current position in mm.")
                dpg.add_input_float(tag="set_pos_input_mm", default_value=(self.pos / self.STEPS_PER_MM), width=150, format="%.3f")
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
        dpg.add_input_float(tag="custom_mm", default_value=1.0, width=120, label="mm", format="%.3f", step=0.1)
        dpg.add_button(label="Right -->", callback=lambda: controller.move_relative_mm(dpg.get_value("custom_mm")))
    
    # ✅ NEW: GUI section for moving to an absolute position.
    dpg.add_separator()
    dpg.add_text("Absolute Move")
    with dpg.group(horizontal=True):
        dpg.add_input_float(tag="absolute_mm_input", default_value=25.0, label="Go to (mm)", format="%.3f", step=1.0)
        dpg.add_button(label="Go", callback=lambda: controller.move_to_mm(dpg.get_value("absolute_mm_input")))

    dpg.add_separator()
    with dpg.group(horizontal=True):
        dpg.add_button(label="STOP", callback=controller.stop, width=-1)
        
    dpg.add_separator()
    dpg.add_text("Position Memory")
    with dpg.group(horizontal=True):
        dpg.add_button(label="Calibrate Position", callback=controller.open_set_position_window)
        dpg.add_button(label="Save Position to Device", callback=controller.save_position_to_eeprom)
        dpg.add_button(label="Load Position from Device", callback=controller.load_position_from_eeprom)

controller.update_display()
dpg.create_viewport(title="Stepper Motor Control", width=500, height=420) # Increased height for the new section
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("main_window", True)

while dpg.is_dearpygui_running():
    controller.update()
    dpg.render_dearpygui_frame()

controller.close()
dpg.destroy_context()