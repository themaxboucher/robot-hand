#include <Servo.h>

const int NUM_SERVOS = 6;

const int BOTTOM_THUMB_PIN = 6;
const int THUMB_PIN = 7;
const int INDEX_PIN = 2;
const int MIDDLE_PIN = 3;
const int RING_PIN = 4;
const int PINKY_PIN = 5;

const int SERVO_PINS[NUM_SERVOS] = {BOTTOM_THUMB_PIN, THUMB_PIN, INDEX_PIN, MIDDLE_PIN, RING_PIN, PINKY_PIN};
const long BAUD = 115200; // Must match the baud rate in the Python script

Servo servos[NUM_SERVOS];
String buffer;

void setup() {
  Serial.begin(BAUD); // Start the serial communication with the Python script

  const int MAX_STRING_LENGTH = 23; // "180,180,180,180,180,180" is 23 characters
  buffer.reserve(MAX_STRING_LENGTH);

  for (int i = 0; i < NUM_SERVOS; i++) {
    servos[i].attach(SERVO_PINS[i]);
    servos[i].write(0); // Open all fingers fully to start
  }
}

void loop() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n') {
      applyAngles(buffer);
      buffer = "";
    } else if (c != '\r') {
      buffer += c;
    }
  }
}

// Takes a string of comma-separated angles and applies them to the servos
void applyAngles(const String& line) {
  int idx = 0;
  int start = 0;

  for (unsigned int i = 0; i <= line.length() && idx < NUM_SERVOS; i++) {
    if (i == line.length() || line[i] == ',') {
      int value = line.substring(start, i).toInt();
      value = constrain(value, 0, 180);
      servos[idx].write(value);
      start = i + 1;
      idx++;
    }
  }
}
