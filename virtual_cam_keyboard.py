import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import warnings
warnings.filterwarnings("ignore")

import cv2
import mediapipe as mp
import pyautogui
import time
import math

# ------------------- Mediapipe Setup -------------------
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

# ------------------- Keyboard Layout -------------------
# A more realistic keyboard layout to mimic the image.
keyboard_layout = [
    ["esc","1","2","3","4","5","6","7","8","9","0","-","=","delete"],
    ["tab","q","w","e","r","t","y","u","i","o","p","[","]","\\"],
    ["capslock","a","s","d","f","g","h","j","k","l",";","'","return"],
    ["shift","z","x","c","v","b","n","m",",",".","/","shift"],
    ["control","option","command","Space","command","option","<"]
]

# ------------------- Helper Variables -------------------
last_tap_time = 0
text_buffer = ""
caps = False
shift = False

# Colors
BG_COLOR = (240, 240, 240)        # light gray background
KEY_COLOR = (255, 230, 235)       # soft pink keys
HOVER_COLOR = (255, 182, 193)     # darker pink hovered key
BORDER_COLOR = (200, 200, 200)    # key borders

# ------------------- Functions -------------------

def draw_rounded_rect(img, x, y, w, h, color, radius=15, thickness=-1):
    """Draw a rectangle with rounded corners."""
    cv2.rectangle(img, (x+radius, y), (x+w-radius, y+h), color, thickness)
    cv2.rectangle(img, (x, y+radius), (x+w, y+h-radius), color, thickness)
    cv2.circle(img, (x+radius, y+radius), radius, color, thickness)
    cv2.circle(img, (x+w-radius, y+radius), radius, color, thickness)
    cv2.circle(img, (x+radius, y+h-radius), radius, color, thickness)
    cv2.circle(img, (x+w-radius, y+h-radius), radius, color, thickness)

def draw_rounded_key(img, x, y, w, h, text, hover=False):
    """Draw a single key with text."""
    color = HOVER_COLOR if hover else KEY_COLOR
    draw_rounded_rect(img, x, y, w, h, color, radius=15)
    # Border
    cv2.rectangle(img, (x, y), (x+w, y+h), BORDER_COLOR, 2)
    
    # Fit text inside key
    font_scale = min(0.8, (w-10) / (len(text)*15))  # scale to fit width
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)[0]
    text_x = x + (w - text_size[0]) // 2
    text_y = y + (h + text_size[1]) // 2
    cv2.putText(img, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (50,50,50), 2)

def draw_keyboard(img, hover_key=None):
    """Draw the whole keyboard and return positions of keys."""
    h, w, _ = img.shape
    key_positions = {}
    
    # Dynamic sizing and spacing
    key_w = w // 16
    key_h = h // 12
    x_spacing = key_w // 10
    y_spacing = key_h // 5
    start_x = w // 2 - (len(keyboard_layout[0]) * (key_w + x_spacing)) // 2
    start_y = h // 3
    
    y = start_y
    for row in keyboard_layout:
        x = start_x
        for key in row:
            # Adjust key width for special keys
            current_key_w = key_w
            if key in ["tab", "delete", "capslock", "return", "shift", "Space"]:
                current_key_w = int(key_w * 1.5) if key != "Space" else int(key_w * 4)
            
            hover = key == hover_key
            draw_rounded_key(img, x, y, current_key_w, key_h, key, hover)
            key_positions[key] = (x, y, x+current_key_w, y+key_h)
            x += current_key_w + x_spacing
        y += key_h + y_spacing
    return key_positions

def distance(p1, p2):
    return math.hypot(p1[0]-p2[0], p1[1]-p2[1])

# ------------------- Main -------------------
# A more robust way to find an available camera
cap = None
for i in range(4): # Try indices 0, 1, 2, 3
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print(f"Successfully opened camera at index {i}")
        break
    else:
        print(f"Failed to open camera at index {i}")

if not cap or not cap.isOpened():
    print("Error: Could not open any camera. Please check your camera connection and permissions.")
else:
    cv2.namedWindow("Virtual Pinch Keyboard", cv2.WINDOW_NORMAL)

    with mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7) as hands:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            frame[:] = BG_COLOR  # fill background with very light pink
            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb)

            hover_key = None
            key_positions = draw_keyboard(frame)

            if result.multi_hand_landmarks:
                for handLms in result.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(frame, handLms, mp_hands.HAND_CONNECTIONS)

                    # Finger coordinates
                    index_tip = handLms.landmark[8]
                    thumb_tip = handLms.landmark[4]
                    ix, iy = int(index_tip.x * w), int(index_tip.y * h)
                    tx, ty = int(thumb_tip.x * w), int(thumb_tip.y * h)

                    cv2.circle(frame, (ix, iy), 8, (255,0,0), -1)
                    cv2.circle(frame, (tx, ty), 8, (0,0,255), -1)

                    # Hover detection
                    for key, (x1, y1, x2, y2) in key_positions.items():
                        if x1 < ix < x2 and y1 < iy < y2:
                            hover_key = key
                            break

                    # Pinch detection for key press (more stable)
                    pinch_dist = distance((ix, iy), (tx, ty))
                    if pinch_dist < 25 and hover_key and (time.time()-last_tap_time)>0.5:
                        if hover_key in ["Space", "delete", "return"]:
                            pyautogui.press(hover_key)
                            if hover_key == "Space":
                                 text_buffer += " "
                            elif hover_key == "delete":
                                 text_buffer = text_buffer[:-1]
                            elif hover_key == "return":
                                 text_buffer += "\n"
                        elif hover_key == "capslock":
                            caps = not caps
                        elif hover_key == "shift":
                            shift = True
                        else:
                            char = hover_key
                            if caps or shift:
                                 char = char.upper()
                            pyautogui.typewrite(char)
                            text_buffer += char
                            shift = False # Reset shift after a keypress
                        last_tap_time = time.time()

            # Redraw keyboard with hover
            draw_keyboard(frame, hover_key)

            # Draw text buffer (last 50 chars)
            display_text = text_buffer[-50:]
            cv2.putText(frame, display_text, (20,100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)

            cv2.imshow("Virtual Pinch Keyboard", frame)
            if cv2.waitKey(1) & 0xFF==ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()
