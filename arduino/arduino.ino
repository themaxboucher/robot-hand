// Robot-hand servo controller with debug output.
//
// Wire format from the host: a single line of comma-separated angles
// (0-180) terminated with '\n', e.g. "90,45,135,0\n".
// Each value drives the servo on pins 2, 3, 4, 5 respectively.
//
// Debug output is printed back over the same serial port so you can
// follow what the Arduino is doing in the Arduino IDE Serial Monitor
// (set the monitor to 115200 baud and "Newline" line ending).

#include <Servo.h>

const int SERVO_PINS[4] = {2, 3, 4, 5};
const long BAUD = 115200;

Servo servos[4];
String buffer;

void setup() {
  Serial.begin(BAUD);
  buffer.reserve(32);

  for (int i = 0; i < 4; i++) {
    servos[i].attach(SERVO_PINS[i]);
    servos[i].write(90);
  }

  Serial.println();
  Serial.println(F("[boot] robot-hand sketch ready"));
  Serial.print(F("[boot] servos attached on pins "));
  for (int i = 0; i < 4; i++) {
    Serial.print(SERVO_PINS[i]);
    if (i < 3) Serial.print(F(", "));
  }
  Serial.println();
  Serial.print(F("[boot] all servos parked at 90 deg, listening @ "));
  Serial.print(BAUD);
  Serial.println(F(" baud"));
}

void loop() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n') {
      Serial.print(F("[rx] '"));
      Serial.print(buffer);
      Serial.println('\'');
      applyAngles(buffer);
      buffer = "";
    } else if (c != '\r') {
      buffer += c;
    }
  }
}

void applyAngles(const String& line) {
  int values[4];
  int idx = 0;
  int start = 0;

  for (unsigned int i = 0; i <= line.length() && idx < 4; i++) {
    if (i == line.length() || line[i] == ',') {
      int value = line.substring(start, i).toInt();
      value = constrain(value, 0, 180);
      values[idx] = value;
      servos[idx].write(value);
      start = i + 1;
      idx++;
    }
  }

  if (idx != 4) {
    Serial.print(F("[warn] expected 4 angles, got "));
    Serial.println(idx);
    return;
  }

  Serial.print(F("[set] "));
  for (int i = 0; i < 4; i++) {
    Serial.print(F("pin"));
    Serial.print(SERVO_PINS[i]);
    Serial.print('=');
    Serial.print(values[i]);
    if (i < 3) Serial.print(' ');
  }
  Serial.println();
}
