import cv2
import numpy as np
import time
import math
import serial

# --- CONFIGURATION ---
IMAGE_SOURCE = 1 
SERIAL_PORT = 'COM3' 
BAUD_RATE = 9600

# Defaults
INIT_LASER_X = 15 
INIT_LASER_Y = 1
PIXELS_PER_MM = 2 

def nothing(x): pass

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print("Connected to Arduino Turret")
except:
    print("Warning: Arduino not connected.")
    ser = None

def send_coordinates(x, y):
    if ser is None: return
    x = max(0, min(640, x))
    y = max(0, min(480, y))
    command = f"X{int(x)}Y{int(y)}\n"
    ser.write(command.encode('utf-8'))

def draw_futuristic_hud(frame, target, state_text, current_pos):
    h, w, _ = frame.shape
    
    # 1. Corner Brackets (Decor)
    c_len = 30
    color = (255, 255, 0) # Cyan
    th = 2
    
    # Top Left
    cv2.line(frame, (20, 20), (20 + c_len, 20), color, th)
    cv2.line(frame, (20, 20), (20, 20 + c_len), color, th)
    # Top Right
    cv2.line(frame, (w-20, 20), (w-20-c_len, 20), color, th)
    cv2.line(frame, (w-20, 20), (w-20, 20 + c_len), color, th)
    # Bottom Left
    cv2.line(frame, (20, h-20), (20 + c_len, h-20), color, th)
    cv2.line(frame, (20, h-20), (20, h-20-c_len), color, th)
    # Bottom Right
    cv2.line(frame, (w-20, h-20), (w-20-c_len, h-20), color, th)
    cv2.line(frame, (w-20, h-20), (w-20, h-20-c_len), color, th)

    # 2. Center Crosshair (Current Servo Pos)
    cx, cy = int(current_pos[0]), int(current_pos[1])
    cv2.circle(frame, (cx, cy), 15, (0, 255, 255), 1) # Ring
    cv2.line(frame, (cx-20, cy), (cx+20, cy), (0, 255, 255), 1)
    cv2.line(frame, (cx, cy-20), (cx, cy+20), (0, 255, 255), 1)
    
    # 3. Status Text (Floating Bottom Center)
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(state_text, font, 0.7, 2)[0]
    text_x = (w - text_size[0]) // 2
    
    # Text Glow
    cv2.putText(frame, state_text, (text_x, h - 40), font, 0.7, (0, 100, 0), 4)
    cv2.putText(frame, state_text, (text_x, h - 40), font, 0.7, (0, 255, 0), 2)

def main():
    cap = cv2.VideoCapture(IMAGE_SOURCE)
    
    cv2.namedWindow("Turret Commander")
    cv2.createTrackbar("Offset X", "Turret Commander", 50 + INIT_LASER_X, 100, nothing) 
    cv2.createTrackbar("Offset Y", "Turret Commander", 50 + INIT_LASER_Y, 100, nothing) 
    cv2.createTrackbar("Vert Speed", "Turret Commander", 5, 50, nothing) 
    cv2.createTrackbar("Scan Speed", "Turret Commander", 5, 50, nothing) 
    
    lower_color = np.array([0, 0, 0])
    upper_color = np.array([180, 255, 60]) 

    current_x = 320.0
    current_y = 240.0
    scan_angle = 0.0
    
    target_lock_time = 0
    current_target_id = None
    cooldown_list = {} 

    while True:
        ret, frame = cap.read()
        if not ret: break
        
        h, w, _ = frame.shape
        center_x, center_y = w // 2, h // 2

        # Settings
        off_x = (cv2.getTrackbarPos("Offset X", "Turret Commander") - 50) * PIXELS_PER_MM
        off_y = (cv2.getTrackbarPos("Offset Y", "Turret Commander") - 50) * PIXELS_PER_MM
        v_speed = cv2.getTrackbarPos("Vert Speed", "Turret Commander") / 100.0 
        if v_speed < 0.005: v_speed = 0.005
        scan_speed = cv2.getTrackbarPos("Scan Speed", "Turret Commander") / 10.0

        # --- DETECTION & BORDER MASKING ---
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower_color, upper_color)
        
        # *** FIX: IGNORE BORDERS & LETTERBOXING ***
        # Increased to 60px to ignore thicker camera black bars
        border_top_bottom = 60 
        border_side = 20
        
        mask[0:border_top_bottom, :] = 0   # Top
        mask[-border_top_bottom:, :] = 0   # Bottom
        mask[:, 0:border_side] = 0         # Left
        mask[:, -border_side:] = 0         # Right

        # Clean noise
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.erode(mask, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=2)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        valid_targets = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Min area lowered to 300 to detect smaller objects
            if area > 300:
                x, y, cw, ch = cv2.boundingRect(cnt)
                
                # *** FILTER: ASPECT RATIO ***
                # If the object is too wide (like a bar), ignore it.
                # Standard small objects (phones, wallets) usually have ratio < 3.0
                aspect_ratio = float(cw) / ch
                if aspect_ratio > 4.0:
                    continue
                
                # *** FILTER: SCREEN SPAN ***
                # If object is wider than 50% of screen, it's likely a border artifact
                if cw > (w * 0.5):
                    continue

                t_id = f"{x//50}_{y//50}"
                valid_targets.append({
                    "id": t_id, "area": area,
                    "center": (x + cw//2, y + ch//2), "rect": (x, y, cw, ch)
                })

        valid_targets.sort(key=lambda k: k['area'], reverse=True)

        # Selection Logic
        chosen_target = None
        current_time = time.time()
        cooldown_list = {k:v for k,v in cooldown_list.items() if v > current_time}

        for t in valid_targets:
            if t['id'] not in cooldown_list:
                chosen_target = t
                break
        
        # State Logic
        aim_x, aim_y = 0, 0
        state_text = "SCANNING SECTOR"
        
        if chosen_target:
            if chosen_target['id'] != current_target_id:
                current_target_id = chosen_target['id']
                target_lock_time = current_time
            
            elapsed = current_time - target_lock_time
            
            cx, cy = chosen_target['center']
            rx, ry, rw, rh = chosen_target['rect']
            
            if elapsed > 3.0:
                cooldown_list[current_target_id] = current_time + 5.0 
                current_target_id = None
                state_text = "TARGET NEUTRALIZED"
            else:
                state_text = f"LOCKED :: {elapsed:.1f}s"
                aim_x = cx - off_x
                aim_y = cy - off_y
                
                # Draw Bracket
                color = (0, 255, 0) if elapsed < 2.0 else (0, 0, 255)
                cv2.line(frame, (rx, ry), (rx+20, ry), color, 2)
                cv2.line(frame, (rx, ry), (rx, ry+20), color, 2)
                cv2.line(frame, (rx+rw, ry+rh), (rx+rw-20, ry+rh), color, 2)
                cv2.line(frame, (rx+rw, ry+rh), (rx+rw, ry+rh-20), color, 2)

        else:
            current_target_id = None
            scan_angle += scan_speed * 0.1
            oscillation = math.sin(scan_angle) * (w / 2 - 80)
            aim_x = center_x + oscillation
            aim_y = center_y 

        # Smoothing
        if chosen_target and current_target_id:
            current_x += (aim_x - current_x) * 0.2
            current_y += (aim_y - current_y) * v_speed
        else:
            current_x += (aim_x - current_x) * 0.1
            current_y += (aim_y - current_y) * 0.05

        send_coordinates(current_x, current_y)
        
        # Draw New UI
        draw_futuristic_hud(frame, chosen_target, state_text, (current_x, current_y))
        
        # Draw Ignored targets (Subtle)
        for t in valid_targets:
            if t['id'] in cooldown_list:
                rx, ry, rw, rh = t['rect']
                cv2.rectangle(frame, (rx, ry), (rx+rw, ry+rh), (0, 0, 80), 1)
        
        cv2.imshow("Turret Commander", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    if ser: ser.close()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
