import cv2
import numpy as np

class SnookerEngine:
    def __init__(self, initial_corners):
        """
        Initializes the scoring engine with a vertical 400x800 coordinate system.
        """
        self.corners = initial_corners
        self.score = 0
        self.ball_memory = {}  # Persistence for tracking balls that vanish
        self.previous_frame_ids = set() # For instant drop detection
        
        # 6 Pocket locations on a vertical 400x800 table map
        self.pockets = [
            (0,0), (400,0),     # Top Corners
            (0,400), (400,400), # Middle Pockets
            (0,800), (400,800)  # Bottom Corners
        ]

    def get_homography(self, current_corners):
        """Calculates transformation matrix to flatten camera perspective."""
        dst_pts = np.array([[0,0], [400,0], [400,800], [0,800]], dtype="float32")
        return cv2.getPerspectiveTransform(np.array(current_corners, dtype="float32"), dst_pts)

    def to_2d(self, pos, M):
        """Transforms pixel coordinates (x,y) to flat table coordinates."""
        pt = np.array([[[pos[0], pos[1]]]], dtype="float32")
        transformed = cv2.perspectiveTransform(pt, M)[0][0]
        return int(transformed[0]), int(transformed[1])

    def is_near_pocket(self, pos_2d, radius=45):
        """Validates if a point is within a pocket's effective scoring area."""
        for px, py in self.pockets:
            if np.sqrt((pos_2d[0]-px)**2 + (pos_2d[1]-py)**2) < radius: 
                return True
        return False

    def get_value(self, color_label):
        """Maps ball color strings to standard Snooker point values."""
        vals = {
            "red-ball": 1, "yellow-ball": 2, "green-ball": 3, "brown-ball": 4,
            "blue-ball": 5, "pink-ball": 6, "black-ball": 7, "white-ball": 0
        }
        return vals.get(color_label, 0)

    def process_frame(self, detected_balls, current_corners, is_replay=False):
        """
        Primary logic loop: Updates ball positions and detects pots based on 
        ID drops and pocket proximity.
        """
        if is_replay: return self.score
        
        M = self.get_homography(current_corners)
        current_ids = {ball['id'] for ball in detected_balls}
        
        # Update/Initialize memory for all visible balls
        for ball in detected_balls:
            b_id, pos, color = ball['id'], ball['coords'], ball['label']
            pos_2d = self.to_2d(pos, M)
            self.ball_memory[b_id] = {"missing": 0, "last_2d": pos_2d, "color": color}

        # INSTANT DROP DETECTION: Checks balls that disappeared in this specific frame
        dropped_ids = self.previous_frame_ids - current_ids

        for b_id in dropped_ids:
            if b_id in self.ball_memory:
                data = self.ball_memory[b_id]
                
                # Use a larger detection radius (85) to catch high-velocity balls
                if self.is_near_pocket(data["last_2d"], radius=85):
                    self.score += self.get_value(data["color"])
                    del self.ball_memory[b_id]

        # CLEANUP: Remove balls that have been missing for too long (likely occlusion, not a pot)
        for b_id, data in list(self.ball_memory.items()):
            if b_id not in current_ids:
                data["missing"] += 1
                if data["missing"] >= 15: 
                    del self.ball_memory[b_id]

        self.previous_frame_ids = current_ids
        return self.score
