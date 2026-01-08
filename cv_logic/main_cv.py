
import cv2
import numpy as np
from ultralytics import YOLO
from table_geometry import TableGeometryEngine
from database.database_config import get_db_connection
from datetime import datetime  # Added for TTL logic
from threading import Thread # Added for background syncing

# Initialize Database
collection = get_db_connection()

# --- NEW: BACKGROUND SYNC FUNCTION ---
def sync_to_mongodb_async(packet):
    """Function to run in a separate thread to prevent video lag"""
    try:
        collection.insert_one(packet)
    except Exception as e:
        print(f"Cloud Sync Error: {e}")

# 1. Initialize Engines
engine = TableGeometryEngine()
model = YOLO('best.pt') 

# 2. EXACT labels from your screenshot with BGR colors
BALL_COLORS = {
    "white-ball": (255, 255, 255),  # White
    "red-ball": (0, 0, 255),        # Red
    "yellow-ball": (0, 255, 255),   # Yellow
    "green-ball": (0, 255, 0),      # Green
    "brown-ball": (30, 42, 165),    # Brown
    "blue-ball": (255, 0, 0),       # Blue
    "pink-ball": (180, 105, 255),   # Pink
    "black-ball": (0, 0, 0)         # Black
}

video_path = 'snooker_video3.mp4'
cap = cv2.VideoCapture(video_path)

frame_count = 0  # Initialize a counter before the loop
last_sync_data = None # Store the previous frame's data to detect movement

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break
    frame_count += 1

    mask, corners, view_status = engine.process_frame(frame)
    results = model.predict(frame, conf=0.4, save=False, verbose=False)

    if engine.table_locked:
        # Create the 2D Analytics Canvas
        mini_map = np.zeros((800, 400, 3), dtype="uint8")
        mini_map[:] = (20, 80, 20) # Deep green table

        # Setup Matrix M
        src_pts = engine.sort_corners(corners)
        dst_pts = np.array([[0,0], [400,0], [400,800], [0,800]], dtype="float32")
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)

        # --- MEMBER 4: LIST TO HOLD BALL DATA FOR SYNC ---
        balls_to_sync = []

        for result in results:
            for box in result.boxes:
                # Get center from YOLO
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
                
                # Get the exact label (e.g., "red-ball")
                label = model.names[int(box.cls[0])]

                # Transform to 2D
                pixel = np.array([[[cx, cy]]], dtype="float32")
                transformed = cv2.perspectiveTransform(pixel, M)
                mx, my = int(transformed[0][0][0]), int(transformed[0][0][1])

                # --- MEMBER 4: ADD DATA TO LIST ---
                balls_to_sync.append({
                    "label": label,
                    "x": mx,
                    "y": my
                })

                # --- NEW DRAWING LOGIC ---
                # Get color from dictionary (defaults to White if not found)
                line_color = BALL_COLORS.get(label, (255, 255, 255))

                # DRAW OUTLINE ONLY (thickness=2 instead of -1)
                cv2.circle(mini_map, (mx, my), 12, line_color, 2)
                
                # DRAW TEXT (matches the outline color)
                cv2.putText(mini_map, label, (mx + 15, my + 5), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, line_color, 1)

        # --- MEMBER 4: SYNC TO MONGODB ATLAS (THREADED & OPTIMIZED) ---
        # 1. Only check every 10 frames
        if frame_count % 10 == 0: 
            # 2. Only sync if balls are detected and they HAVE MOVED since the last sync
            if len(balls_to_sync) > 0 and balls_to_sync != last_sync_data:
                data_packet = {
                    "createdAt": datetime.utcnow(),
                    "balls": balls_to_sync
                }
                
                # 3. Start a background thread so the video doesn't freeze
                Thread(target=sync_to_mongodb_async, args=(data_packet,)).start()
                
                # 4. Update the last_sync_data tracker
                last_sync_data = balls_to_sync

        cv2.imshow("Member 4: 2D Analytics Dashboard", mini_map)
    
    cv2.imshow("Original Broadcast", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
