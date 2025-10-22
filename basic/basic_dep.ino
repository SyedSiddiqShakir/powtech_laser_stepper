#include <AccelStepper.h>
#include <EEPROM.h>

#define STEP_PIN 4
#define DIR_PIN 7
#define ENABLE_PIN 8

AccelStepper stepper(AccelStepper::DRIVER, STEP_PIN, DIR_PIN);

void setup() {
  Serial.begin(115200);
  pinMode(ENABLE_PIN, OUTPUT);
  
  // ⭐️ FIX #1: Explicitly set the enable pin for the library.
  stepper.setEnablePin(ENABLE_PIN);
  stepper.setPinsInverted(false, false, true); // Invert the enable pin signal (HIGH = disabled)
  
  digitalWrite(ENABLE_PIN, HIGH); // Start with motor disabled

  stepper.setMaxSpeed(2000.0);
  stepper.setAcceleration(1000.0);
  
  long saved_pos;
  EEPROM.get(0, saved_pos);
  stepper.setCurrentPosition(saved_pos);
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();

    switch (cmd) {
      case 'M':
        // ⭐️ FIX #2: Wait briefly for the rest of the serial data to arrive.
        delay(5); // Small delay to ensure the full number is in the buffer
        if (Serial.available() > 0) {
          long target_steps = Serial.parseInt();
          moveToPoint(target_steps);
        }
        break;
      // ... (rest of the cases are fine)
      case 'S':
        stopMotor();
        break;
      case 'P':
        savePosition();
        break;
      case 'R':
        retrievePosition();
        break;
    }
    while (Serial.available() > 0) Serial.read();
  }
}

void moveToPoint(long absolute_steps) {
  // The library now controls the enable pin automatically.
  stepper.enableOutputs(); // Enable the driver
  
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
  
  // Wait until the movement is truly finished before disabling.
  stepper.runToPosition();
  stepper.disableOutputs(); // Disable the driver
}

void stopMotor() {
  stepper.stop();
  stepper.runToPosition();
  stepper.disableOutputs();
}

// ... (savePosition and retrievePosition are fine)
void savePosition() {
  long current_pos = stepper.currentPosition();
  EEPROM.put(0, current_pos);
}

void retrievePosition() {
  long current_pos = stepper.currentPosition();
  Serial.print("POS:");
  Serial.println(current_pos);
}