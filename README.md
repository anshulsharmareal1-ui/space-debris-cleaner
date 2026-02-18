# space-debris-cleaner
a place debris cleaner laser based tracker
# Automated Laser Tracking Turret 🎯

An automated sentry system that uses Computer Vision to detect targets, calculates their coordinates in real-time, and directs a 2-axis servo turret to neutralize them with a laser pointer.
(https://github.com/user-attachments/assets/21f01995-9b04-486c-b67d-70f9a4da802a)



## 🌟 Features
* **Computer Vision Core:** Uses OpenCV HSV color filtering to detect targets (specifically black/dark objects) while ignoring background noise and camera borders.
* **Real-Time Tracking:** Calculates the trajectory and smooths servo movement using a proportional control algorithm.
* **Intelligent Logic:** * **Multi-Target Memory:** Remembers neutralized targets.
    * **3-Second Lock:** Tracks a target for 3 seconds before switching to the next threat.
    * **Cooldown System:** Ignores neutralized targets for 5 seconds to prevent re-locking.
* **Hardware Parallax Correction:** Mathematically corrects the offset between the camera lens and the laser emitter.

## 🛠️ Hardware Requirements
* **Microcontroller:** Arduino Uno (or compatible)
* **Actuators:** 2x SG90 Servo Motors (Pan & Tilt)
* **Vision:** Webcam (Laptop integrated or external USB)
* **Power:** 4x AA Batteries (6V External Power for Servos)
* **Laser:** 5mW Red Laser Pointer
* **Structure:** Custom Pan-Tilt Bracket

## 🔌 Wiring Diagram

| Component | Pin / Connection |
| :--- | :--- |
| **Horizontal Servo (Pan)** | Digital Pin 9 |
| **Vertical Servo (Tilt)** | Digital Pin 10 |
| **Laser (+)** | Arduino 5V |
| **Laser (-)** | Arduino GND |
| **Battery (+)** | Breadboard Red Rail (Powers Servos) |
| **Battery (-)** | Breadboard Blue Rail (Connects to Arduino GND) |

**⚠️ Critical:** Ensure the Battery Negative is connected to the Arduino GND (Common Ground).

## 💻 Software Installation

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/](https://github.com/)[YourUsername]/Automated-Laser-Turret.git
    ```

2.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Upload Firmware:**
    * Open `Arduino_Firmware/controller/controller.ino` in the Arduino IDE.
    * Select your Board and Port.
    * Upload the sketch.

## 🚀 Usage

1.  Connect the Arduino to your PC via USB.
2.  Run the **Hardware Tracker**:
    ```bash
    python Python_Software/hardware_tracker.py
    ```
3.  **Controls:**
    * `Offset X/Y`: Calibrate the laser alignment.
    * `Vert Speed`: Adjust how fast the turret moves vertically.
    * `Scan Speed`: Adjust the idle scanning speed.

## 🧠 How It Works
1.  **Detection:** Python captures video frames and processes them to find contours of specific colors.
2.  **Logic:** The system sorts targets by size and selects the largest valid target.
3.  **Communication:** Python calculates the required servo angles and sends coordinate data (e.g., `X320Y240`) via Serial (USB) to the Arduino.
4.  **Actuation:** The Arduino maps these coordinates to servo angles and moves the turret.

## 📄 License
This project is open-source.
