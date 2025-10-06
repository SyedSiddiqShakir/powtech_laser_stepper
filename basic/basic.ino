#include <AccelStepper.h>
#include <EEPROM.h>

#define STEP_PIN 4
#define DIR_PIN 7
#define ENABLE_PIN 8

AccelStepper stepper(AccelStepper::DRIVER, STEP_PIN, DIR_PIN);

void setup() {
  Serial.begin(115200);
  
  stepper.setEnablePin(ENABLE_PIN);
  stepper.setPinsInverted(false, false, true);
  
  stepper.setMaxSpeed(2000.0);
  stepper.setAcceleration(1000.0);
  
  // Load the last saved position from EEPROM on startup.
  // This is good practice for power cycles.
  loadPositionFromEEPROM();
  stepper.disableOutputs();
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();

    switch (cmd) {
      case 'M': // Move to an absolute position
        delay(5);
        if (Serial.available() > 0) {
          long target_steps = Serial.parseInt();
          moveToPoint(target_steps);
        }
        break;
      
      // ✅ NEW: Calibrate command to set the current position without moving.
      case 'C': 
        delay(5);
        if (Serial.available() > 0) {
          long new_current_steps = Serial.parseInt();
          stepper.setCurrentPosition(new_current_steps);
        }
        break;
        
      case 'S': // Stop motor immediately
        stopMotor();
        break;
        
      case 'P': // Persist (save) current position to EEPROM
        savePositionToEEPROM();
        break;
        
      // ✅ MODIFIED: 'R' is now 'L' for Load. It reads from EEPROM and reports back.
      case 'L': 
        loadPositionFromEEPROM();
        break;
    }
    while (Serial.available() > 0) Serial.read();
  }
}

// --- Command Functions ---

void moveToPoint(long absolute_steps) {
  stepper.enableOutputs();
  stepper.moveTo(absolute_steps);
  
  while (stepper.distanceToGo() != 0) {
    stepper.run();
    if (Serial.available() > 0) {
      if (Serial.read() == 'S') {
        stopMotor();
        break;
      }
    }
  }
  
  stepper.runToPosition();
  stepper.disableOutputs();
  Serial.println("OK"); // Handshake to confirm move is done
}

void stopMotor() {
  stepper.stop();
  stepper.runToPosition();
  stepper.disableOutputs();
}

void savePositionToEEPROM() {
  long current_pos = stepper.currentPosition();
  EEPROM.put(0, current_pos);
  // Optional: Send a confirmation back
  Serial.println("SAVED"); 
}

void loadPositionFromEEPROM() {
  long pos_from_eeprom;
  EEPROM.get(0, pos_from_eeprom);
  // Set the stepper's internal counter to this value
  stepper.setCurrentPosition(pos_from_eeprom);
  // Report this value back to Python so it can sync up
  Serial.print("POS:");
  Serial.println(pos_from_eeprom);
}