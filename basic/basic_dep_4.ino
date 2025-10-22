#include <AccelStepper.h>
#include <EEPROM.h>

#define STEP_PIN 4
#define DIR_PIN 7
#define ENABLE_PIN 8

AccelStepper stepper(AccelStepper::DRIVER, STEP_PIN, DIR_PIN);

void setup() {
  Serial.begin(115200);
  pinMode(ENABLE_PIN, OUTPUT);
  
  stepper.setEnablePin(ENABLE_PIN);
  stepper.setPinsInverted(false, false, true); // Original direction
  
  digitalWrite(ENABLE_PIN, HIGH); 

  stepper.setMaxSpeed(2000.0); // Original speed
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
        delay(5); 
        if (Serial.available() > 0) {
          long target_steps = Serial.parseInt();
          moveToPoint(target_steps);
        }
        break;
      case 'S':
        stopMotor();
        break;
      case 'P':
        savePositionToEEPROM(); // This function now sends "SAVED"
        break;
      case 'R':
        retrievePosition();
        break;
    }
    while (Serial.available() > 0) Serial.read();
  }
}

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
  Serial.println("SAVED"); // Handshake to confirm save is done
}

void retrievePosition() {
  long current_pos = stepper.currentPosition();
  Serial.print("POS:");
  Serial.println(current_pos);
}