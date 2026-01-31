import cv2
import numpy as np

class TableGeometryEngine:
    def __init__(self):
        # MEMBER 2 DATA STORAGE
        self.locked_corners = None 
        self.view_status = "UNKNOWN"  # This is the 'Status Flag' for Member 4
        self.manual_points = []
        self.table_locked = False
        self.stability_counter = 0  # To ensure the table is steady before locking

    # sorting corners in sequence top-left,top-right,bottom-right,bottom-left
    def sort_corners(self, pts):
        # Reshape points to (4, 2)
        pts = pts.reshape((4, 2))
        rect = np.zeros((4, 2), dtype="float32")

        # Top-left has the smallest sum, bottom-right has the largest sum
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        # Top-right has the smallest difference, bottom-left has the largest
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        return rect

    # Mouse callback function for manual clicking
    def select_points(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(self.manual_points) < 4:
            self.manual_points.append([x, y])
            print(f"Point {len(self.manual_points)} captured at: {x}, {y}")

    def process_frame(self, frame):
        # --- STAGE 1: HIGH-PRECISION PREPROCESSING ---
        # 1. Gaussian Blur helps ignore small reflections and pixel noise
        blurred = cv2.GaussianBlur(frame, (7, 7), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        
        # 2. Tightened Green Range for more accuracy
        lower_green = np.array([38, 50, 40]) 
        upper_green = np.array([80, 255, 255])
        mask = cv2.inRange(hsv, lower_green, upper_green)

        # 3. Morphology: Close gaps and remove tiny spots
        kernel = np.ones((5,5), np.uint8) # A kernel is a small matrix...
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel) # Morphological operations are used...
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # --- STAGE 2: STRICTER VIEW & CORNER LOGIC ---
        total_area = frame.shape[0] * frame.shape[1] # frame.shape[0] * frame.shape[1] gives...
        green_area = cv2.countNonZero(mask)
        green_ratio = green_area / total_area

        if 0.15 < green_ratio < 0.65:
            self.view_status = "WIDE"
            
            # Only run detection if we haven't locked the table yet
            if not self.table_locked:
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours: # Contours are the outlines...
                    table_cnt = max(contours, key=cv2.contourArea)
                    
                    # Accuracy Check: The table must occupy a significant part of the frame
                    if cv2.contourArea(table_cnt) > (total_area * 0.2):
                        hull = cv2.convexHull(table_cnt) # A convex hull is the tightest...
                        # convex hull creates a clean outer boundary...

                        # Using a stricter epsilon (0.04) ensures it looks...
                        peri = cv2.arcLength(hull, True) # arcLength gives the perimeter...
                        approx = cv2.approxPolyDP(hull, 0.04 * peri, True) # approxPolyDP simplifies...

                        if len(approx) == 4:
                            self.stability_counter += 1
                            # Wait for 15 steady frames before "Freezing"
                            if self.stability_counter > 15:
                                # --- ADDED: CONFIRMATION LOGIC ---
                                confirm_frame = frame.copy()
                                for pt in approx:
                                    cv2.circle(confirm_frame, tuple(pt[0]), 10, (0, 0, 255), -1)
                                cv2.putText(confirm_frame, "Correct? (y/n)", (50, 50), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                cv2.imshow("Confirm Detection", confirm_frame)
                                
                                key = cv2.waitKey(0)
                                if key == ord('y'):
                                    self.locked_corners = approx
                                    self.table_locked = True
                                    print("Success: Geometry LOCKED.")
                                    cv2.destroyWindow("Confirm Detection")
                                elif key == ord('n'):
                                    cv2.destroyWindow("Confirm Detection")
                                    print("Switching to Manual Mode...")
                                    self.manual_points = []
                                    cv2.namedWindow("Manual Mode")
                                    cv2.setMouseCallback("Manual Mode", self.select_points)
                                    
                                    while len(self.manual_points) < 4:
                                        # Redraw frame with points
                                        m_frame = frame.copy()
                                        for p in self.manual_points:
                                            cv2.circle(m_frame, tuple(p), 5, (0, 0, 255), -1)
                                        cv2.imshow("Manual Mode", m_frame)
                                        cv2.waitKey(1)
                                    
                                    # Apply sorting to manual clicks
                                    self.locked_corners = self.sort_corners(np.array(self.manual_points))
                                    self.table_locked = True
                                    cv2.destroyWindow("Manual Mode")
                        else:
                            self.stability_counter = 0 # Reset if the shape is not...
            
        elif green_ratio > 0.85:
            self.view_status = "ZOOM"
            # Use the saved coordinates during zoom

        return mask, self.locked_corners, self.view_status

# --- TEST BLOCK FOR VS CODE ---
if __name__ == "__main__":
    # Member 1's input
    cap = cv2.VideoCapture('../videos/input/snooker_video3.mp4')
    
    # Initialize Engine
    engine = TableGeometryEngine()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: 
            break

        # Process frame through the Engine
        mask, locked_corners, view_status = engine.process_frame(frame)

        # --- STAGE 3: VISUALIZATION ---
        if locked_corners is not None:
            solid_mask = np.zeros_like(mask)
            # Use reshape to ensure sort_corners works for both auto and manual formats
            sorted_for_mask = engine.sort_corners(locked_corners).astype(np.int32)
            cv2.drawContours(solid_mask, [sorted_for_mask], -1, 255, thickness=cv2.FILLED)
            
            only_table = cv2.bitwise_and(frame, frame, mask=solid_mask)
            
            for point in sorted_for_mask:
                x, y = point.ravel() # ravel() flattens things...
                cv2.circle(frame, (x, y), 10, (0, 0, 255), -1) # -1 is thickness here 

        # Display Status for the team
        cv2.putText(frame, f"STATUS: {view_status}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        cv2.imshow("Detection View (Red Dots)", frame)
        
        # --- STAGE 4: PERSPECTIVE WARP (The 2D Map) ---
        if locked_corners is not None:
            # 1. Sort the detected corners
            src_pts = engine.sort_corners(locked_corners)
            # 2. Define the output 2D map size (e.g., 400x800 for a snooker table)
            dst_pts = np.array([[0, 0], [400, 0], [400, 800], [0, 800]], dtype="float32")

            # 3. Calculate the Transformation Matrix
            M = cv2.getPerspectiveTransform(src_pts, dst_pts)
            # 4. Generate the 2D Mini-Map
            mini_map = cv2.warpPerspective(frame, M, (400, 800))
            
            # Show the 2D map to see your progress
            cv2.imshow("2D Analytics Map", mini_map)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

'''First, the system waits for a wide camera view where the snooker table is clearly visible as a trapezoid. 
In this view, the table corners can be detected accurately, so we identify and lock these corners. 
Since the camera position is fixed and the table never moves, this locked geometry remains valid even
 if the camera angle or zoom changes. During zoom views, the table corners are not visible, so no detection 
 is performed and the previously locked data is reused. When the table returns to view, we compare the 
 current ball data with the previously stored data, and if a ball is missing, it is considered potted'''
