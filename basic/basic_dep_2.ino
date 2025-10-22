#include <AccelStepper.h>
#include <EEPROM.h>

// motor connections
#define STEP_PIN 4
#define DIR_PIN 7
#define ENABLE_PIN 8 // LOW = enable, HIGH = disable
AccelStepper stepper(AccelStepper::DRIVER, STEP_PIN, DIR_PIN);

void setup() {
  Serial.begin(115200);
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, HIGH); // start with motor disabled

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
      case 'M': // Move to an absolute position
        if (Serial.available() > 0) {
          long target_steps = Serial.parseInt();
          moveToPoint(target_steps);
        }
        break;
      case 'S': // Stop motor immediately
        stopMotor();
        break;
      case 'P': // Persist (save) current position to EEPROM
        savePosition();
        break;
      case 'R': // Retrieve (report) current position
        retrievePosition();
        break;
    }
    // Flush any remaining characters from the serial buffer
    while (Serial.available() > 0) Serial.read();
  }
  
}


void moveToPoint(long absolute_steps) {
  digitalWrite(ENABLE_PIN, LOW); // Enable motor driver
  stepper.moveTo(absolute_steps); 
  
  while (stepper.distanceToGo() != 0) {
    stepper.run(); // This steps the motor
    if (Serial.available() > 0) {
      if (Serial.read() == 'S') {
        stopMotor();
        break;
      }
    }
  }
  digitalWrite(ENABLE_PIN, HIGH); // Disable motor driver to save power and reduce heat
}

void stopMotor() {
  stepper.stop(); // Decelerate to a stop
  stepper.runToPosition(); // Finish the stop
  digitalWrite(ENABLE_PIN, HIGH);
}

void savePosition() {
  long current_pos = stepper.currentPosition();
  EEPROM.put(0, current_pos);
}

void retrievePosition() {
  long current_pos = stepper.currentPosition();
  Serial.print("POS:");
  Serial.println(current_pos); // Send position back to Python
}