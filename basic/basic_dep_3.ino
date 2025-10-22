#include <AccelStepper.h>
#include <EEPROM.h>

#define STEP_PIN 4
#define DIR_PIN 7
#define ENABLE_PIN 8  // Enable pin (LOW = enable, HIGH = disable)

AccelStepper stepper(AccelStepper::DRIVER, STEP_PIN, DIR_PIN);

void setup() {
  Serial.begin(115200);
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, HIGH);
  stepper.setMaxSpeed(1000.0);  // Adjust if needed for 160000 steps
  stepper.setAcceleration(500.0);
}

void moveToPoint(long steps) {
  digitalWrite(ENABLE_PIN, LOW);
  stepper.moveTo(stepper.currentPosition() + steps);
  while (stepper.distanceToGo() != 0) {
    if (Serial.available() > 0) {
      char cmd = Serial.read();
      if (cmd == 'S') {
        digitalWrite(ENABLE_PIN, HIGH);
        break;
      }
    }
    stepper.run();
  }
  digitalWrite(ENABLE_PIN, HIGH);
}

void stopMotor() {
  stepper.stop();
  digitalWrite(ENABLE_PIN, HIGH);
}

void calibrate() {
  digitalWrite(ENABLE_PIN, LOW);
  stepper.moveTo(-10000);  // Placeholder: move to find home
  while (stepper.distanceToGo() != 0) {
    stepper.run();
  }
  stepper.setCurrentPosition(0);
  digitalWrite(ENABLE_PIN, HIGH);
}

void savePosition() {
  long pos = stepper.currentPosition();
  EEPROM.put(0, pos);
}

void retrievePosition() {
  long pos;
  EEPROM.get(0, pos);
  stepper.moveTo(pos);
  while (stepper.distanceToGo() != 0) {
    stepper.run();
  }
  Serial.print("POS:");
  Serial.println(pos);  // Send position to Python
}



void loop() {

  if (Serial.available() > 0) {
    char cmd = Serial.read();
    Serial.print("Received command: ");
    Serial.println(cmd);
    switch (cmd) {
      case 'M':
        if (Serial.available() > 0) {
          long steps = Serial.parseInt();  // Use long for large step values
          Serial.print("Received steps: ");
          Serial.println(steps);
          moveToPoint(steps);
        }
        break;

      case 'S':
        stopMotor();
        break;

      case 'C':
        calibrate();
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