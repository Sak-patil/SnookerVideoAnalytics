import cv2
import numpy as np
from ultralytics import YOLO
from table_geometry import TableGeometryEngine
from database_config import get_db_connection
from datetime import datetime 
from threading import Thread 
from snooker_engine import SnookerEngine 

# --- DATABASE CONNECTION ---
# Establish connection to MongoDB Atlas for cloud-based score tracking
collection = get_db_connection()

def sync_to_mongodb_async(packet):
    """Offloads database insertion to a background thread to maintain video FPS."""
    try:
        collection.insert_one(packet)
    except Exception as e:
        print(f"Cloud Sync Error: {e}")

# --- ENGINE INITIALIZATION ---
engine = TableGeometryEngine()
model = YOLO('best.pt') 
snooker_logic = None 

BALL_COLORS = {
    "white-ball": (255, 255, 255), "red-ball": (0, 0, 255), 
    "yellow-ball": (0, 255, 255), "green-ball": (0, 255, 0),
    "brown-ball": (30, 42, 165), "blue-ball": (255, 0, 0),
    "pink-ball": (180, 105, 255), "black-ball": (0, 0, 0)
}

video_path = 'demo_snooker_video.mp4'
cap = cv2.VideoCapture(video_path)
frame_count = 0 
last_sync_data = None 
current_score = 0      

# PERFORMANCE: Process every N frames to optimize CPU/GPU usage
process_every_n_frames = 2 

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break
    frame_count += 1

    # Main Processing Block
    if frame_count % process_every_n_frames == 0:
        mask, corners, view_status = engine.process_frame(frame)
        results = model.track(frame, conf=0.3, persist=True, verbose=False, imgsz=640)
        
        if engine.table_locked:
            # Initialize scoring logic once table geometry is established
            if snooker_logic is None:
                snooker_logic = SnookerEngine(engine.sort_corners(corners))

            # Initialize 2D Mini-Map (Vertical 400x800)
            mini_map = np.zeros((800, 400, 3), dtype="uint8")
            mini_map[:] = (20, 80, 20) 
            
            src_pts = engine.sort_corners(corners)
            dst_pts = np.array([[0,0], [400,0], [400,800], [0,800]], dtype="float32")
            M = cv2.getPerspectiveTransform(src_pts, dst_pts)

            balls_to_sync = [] 
            balls_for_logic = [] 

            # Draw pocket indicators on the mini-map
            for px, py in snooker_logic.pockets:
                cv2.circle(mini_map, (px, py), 30, (0, 255, 255), 2)

            for result in results:
                if result.boxes.id is not None:
                    boxes = result.boxes.xyxy.cpu().numpy()
                    ids = result.boxes.id.cpu().numpy().astype(int)
                    cls = result.boxes.cls.cpu().numpy().astype(int)

                    for box, b_id, b_cls in zip(boxes, ids, cls):
                        x1, y1, x2, y2 = box
                        cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
                        label = model.names[b_cls]

                        # Project ball position into 2D table space
                        pixel = np.array([[[cx, cy]]], dtype="float32")
                        transformed = cv2.perspectiveTransform(pixel, M)
                        mx, my = int(transformed[0][0][0]), int(transformed[0][0][1])

                        balls_for_logic.append({"id": b_id, "coords": (cx, cy), "label": label})
                        balls_to_sync.append({"label": label, "x": mx, "y": my})
                        
                        # Render balls on the analytics mini-map
                        line_color = BALL_COLORS.get(label, (255, 255, 255))
                        cv2.circle(mini_map, (mx, my), 12, line_color, 2)

            # Update score via logic engine
            current_score = snooker_logic.process_frame(balls_for_logic, src_pts)

            # DATABASE SYNC: Throttled to every 10 frames to reduce network traffic
            if frame_count % 10 == 0: 
                if len(balls_to_sync) > 0 and balls_to_sync != last_sync_data:
                    data_packet = {
                        "createdAt": datetime.utcnow(),
                        "balls": balls_to_sync,
                        "match_score": current_score 
                    }
                    # Trigger background cloud sync
                    Thread(target=sync_to_mongodb_async, args=(data_packet,)).start()
                    last_sync_data = balls_to_sync

            cv2.imshow("2D Analytics Dashboard", mini_map)
    
    # Overlay live scoreboard on the original video feed
    cv2.putText(frame, f"LIVE SCORE: {current_score}", (50, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.imshow("AI Broadcast Stream", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
