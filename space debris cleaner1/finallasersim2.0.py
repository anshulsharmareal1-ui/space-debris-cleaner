import cv2
import numpy as np
import time
import math

# --- CONFIGURATION ---
IMAGE_SOURCE = 1 
INIT_LASER_X = 15
INIT_LASER_Y = 0
PIXELS_PER_UNIT = 10

def nothing(x): pass

def draw_elegant_hud(frame, target_info, laser_pos, scan_active, valid_targets):
    h, w, _ = frame.shape
    
    # 1. Vignette Effect (Darken corners for elegance)
    # We create a radial gradient mask manually or just darken edges
    # Simple approach: Draw black bars at very top/bottom only for cinematic feel? 
    # User asked to REMOVE black headers, so we keep it clean.
    
    # 2. Top Info Bar (Transparent)
    font = cv2.FONT_HERSHEY_SIMPLEX
    cyan = (255, 255, 0)
    
    # Left: Counts
    cv2.putText(frame, f"TARGETS: {len(valid_targets)}", (30, 40), font, 0.5, cyan, 1)
    
    # Right: Coords
    if target_info:
        tx, ty = target_info['center']
        cv2.putText(frame, f"TRG: [{tx}, {ty}]", (w - 180, 40), font, 0.5, cyan, 1)
    else:
        cv2.putText(frame, "TRG: [---, ---]", (w - 180, 40), font, 0.5, (100,100,100), 1)

    # 3. Center Info (Requested Text)
    # Floating with shadow
    text = "abcde fghij"
    ts = cv2.getTextSize(text, font, 0.6, 2)[0]
    tx = (w - ts[0]) // 2
    cv2.putText(frame, text, (tx + 2, h - 98), font, 0.6, (0,0,0), 2) # Shadow
    cv2.putText(frame, text, (tx, h - 100), font, 0.6, cyan, 2)

    # 4. Bottom Status
    status = "SCANNING SECTOR" if scan_active else "TARGET LOCKED"
    color = (255, 255, 255) if scan_active else (0, 255, 0)
    
    ts2 = cv2.getTextSize(status, font, 0.8, 2)[0]
    tx2 = (w - ts2[0]) // 2
    
    # Glow effect
    cv2.putText(frame, status, (tx2, h - 50), font, 0.8, (0, 100, 0), 4)
    cv2.putText(frame, status, (tx2, h - 50), font, 0.8, color, 2)

    # 5. Mini Map (Bottom Right, Floating)
    map_cx, map_cy = w - 60, h - 60
    # Camera
    cv2.circle(frame, (map_cx, map_cy), 3, (255, 255, 0), -1) 
    # Laser
    lx = map_cx + int(laser_pos[0] * 1.5)
    ly = map_cy + int(-laser_pos[1] * 1.5)
    cv2.line(frame, (map_cx, map_cy), (lx, ly), (100, 100, 100), 1)
    cv2.circle(frame, (lx, ly), 3, (0, 0, 255), -1) 

def simulation():
    cap = cv2.VideoCapture(IMAGE_SOURCE)
    
    cv2.namedWindow("Weapon Simulation")
    cv2.createTrackbar("Laser X", "Weapon Simulation", INIT_LASER_X, 100, nothing)
    cv2.createTrackbar("Laser Y", "Weapon Simulation", 50 + INIT_LASER_Y, 100, nothing) 
    cv2.createTrackbar("Vert Speed", "Weapon Simulation", 5, 50, nothing) 
    cv2.createTrackbar("Scan Speed", "Weapon Simulation", 2, 20, nothing)

    current_servo_x = 0 
    current_servo_y = 0
    scan_angle = 0
    
    target_lock_time = 0
    current_target_id = None
    cooldown_list = {}
    
    lower_color = np.array([0, 0, 0])
    upper_color = np.array([180, 255, 60]) 

    while True:
        ret, frame = cap.read()
        if not ret: break
        
        frame = cv2.flip(frame, 1) 
        h, w, _ = frame.shape
        center_x, center_y = w // 2, h // 2

        # Settings
        laser_offset_x = cv2.getTrackbarPos("Laser X", "Weapon Simulation")
        laser_offset_y = cv2.getTrackbarPos("Laser Y", "Weapon Simulation") - 50
        vert_speed = cv2.getTrackbarPos("Vert Speed", "Weapon Simulation") / 50.0 
        if vert_speed < 0.01: vert_speed = 0.01
        scan_speed = cv2.getTrackbarPos("Scan Speed", "Weapon Simulation")

        # --- DETECTION & BORDER MASK ---
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower_color, upper_color)
        
        # *** BORDER MASK ***
        border = 20
        mask[0:border, :] = 0
        mask[-border:, :] = 0
        mask[:, 0:border] = 0
        mask[:, -border:] = 0

        kernel = np.ones((5,5), np.uint8)
        mask = cv2.erode(mask, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=2)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        valid_targets = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 800:
                x, y, cw, ch = cv2.boundingRect(cnt)
                t_id = f"{x//50}_{y//50}"
                valid_targets.append({
                    "id": t_id, "area": area, 
                    "center": (x+cw//2, y+ch//2), "rect": (x,y,cw,ch)
                })
        
        valid_targets.sort(key=lambda k: k['area'], reverse=True)

        # Logic
        chosen_target = None
        current_time = time.time()
        cooldown_list = {k:v for k,v in cooldown_list.items() if v > current_time}

        for t in valid_targets:
            if t['id'] not in cooldown_list:
                chosen_target = t
                break

        scanning = True
        aim_x, aim_y = 0, 0

        if chosen_target:
            scanning = False
            tx, ty = chosen_target['center']
            
            if chosen_target['id'] != current_target_id:
                current_target_id = chosen_target['id']
                target_lock_time = current_time
            
            elapsed = current_time - target_lock_time
            
            if elapsed > 3.0:
                cooldown_list[current_target_id] = current_time + 5.0
                current_target_id = None
                chosen_target = None
                scanning = True
            else:
                pixel_offset_x = laser_offset_x * 2 
                pixel_offset_y = laser_offset_y * 2
                aim_x = tx - pixel_offset_x
                aim_y = ty - pixel_offset_y

        if scanning:
            scan_angle += scan_speed * 0.1
            oscillation = math.sin(scan_angle) * (w // 2 - 50)
            aim_x = center_x + oscillation
            aim_y = center_y 

        # Smooth
        h_factor = 0.2 if not scanning else 0.1
        current_servo_x += (aim_x - current_servo_x) * h_factor
        current_servo_y += (aim_y - current_servo_y) * vert_speed

        # Visuals
        origin_x = center_x + (laser_offset_x * PIXELS_PER_UNIT)
        origin_y = h 
        beam_end_x = int(current_servo_x)
        beam_end_y = int(current_servo_y)
        
        color = (0, 0, 255) if scanning else (0, 255, 0)
        
        # Targets
        for t in valid_targets:
            rx, ry, rw, rh = t['rect']
            if t['id'] in cooldown_list:
                # Minimal marker for ignored
                cv2.line(frame, (rx, ry), (rx+rw, ry+rh), (0,0,50), 1)
                cv2.line(frame, (rx+rw, ry), (rx, ry+rh), (0,0,50), 1)
            elif t == chosen_target:
                # Bracket style
                l = 15
                cv2.line(frame, (rx, ry), (rx+l, ry), (0,255,0), 2)
                cv2.line(frame, (rx, ry), (rx, ry+l), (0,255,0), 2)
                cv2.line(frame, (rx+rw, ry+rh), (rx+rw-l, ry+rh), (0,255,0), 2)
                cv2.line(frame, (rx+rw, ry+rh), (rx+rw, ry+rh-l), (0,255,0), 2)
            else:
                # Faint box for potentials
                cv2.rectangle(frame, (rx, ry), (rx+rw, ry+rh), (60,60,60), 1)

        cv2.line(frame, (int(origin_x), int(origin_y)), (beam_end_x, beam_end_y), color, 2)
        cv2.circle(frame, (beam_end_x, beam_end_y), 5, color, -1)
        
        draw_elegant_hud(frame, chosen_target, (laser_offset_x, laser_offset_y), scanning, valid_targets)
        
        cv2.imshow("Weapon Simulation", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    simulation()
