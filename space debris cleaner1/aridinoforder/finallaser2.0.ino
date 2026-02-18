#include <Servo.h>

Servo servoPan;  
Servo servoTilt; 

// Pins based on your wiring
const int PAN_PIN = 9;
const int TILT_PIN = 10;

// Screen Resolution
int screenW = 640;
int screenH = 480; 

// --- CALIBRATION ---
// Adjust these so the laser covers your whole screen
// Pan: 160 (Left) -> 20 (Right)
int panLeft = 160;   
int panRight = 20;

// Tilt: 45 (Top) -> 135 (Bottom)
int tiltTop = 45;
int tiltBottom = 135;

void setup() {
  Serial.begin(9600);
  servoPan.attach(PAN_PIN);
  servoTilt.attach(TILT_PIN);
  
  // Start Center
  servoPan.write(90);
  servoTilt.write(90);
}

void loop() {
  if (Serial.available() > 0) {
    // Read command from Python
    String data = Serial.readStringUntil('\n');
    
    int xIndex = data.indexOf('X');
    int yIndex = data.indexOf('Y');
    
    if (xIndex != -1 && yIndex != -1) {
      String xStr = data.substring(xIndex + 1, yIndex);
      String yStr = data.substring(yIndex + 1);
      
      int valX = xStr.toInt();
      int valY = yStr.toInt();
      
      // Clamp to screen
      valX = constrain(valX, 0, screenW);
      valY = constrain(valY, 0, screenH);
      
      // Map Pixel to Angle
      int panAngle = map(valX, 0, screenW, panLeft, panRight);
      int tiltAngle = map(valY, 0, screenH, tiltTop, tiltBottom);
      
      // Move Servos
      // Since Python handles the "Smoothing", we just write directly here.
      servoPan.write(panAngle);
      servoTilt.write(tiltAngle);
    }
  }
}