import cv2
import face_recognition
import os
import numpy as np
from pathlib import Path
import logging
from typing import Tuple, List

# ============ LOGGING SETUP ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AdminFaceLock:
    """Admin Face Recognition Lock System"""
    
    def __init__(self, admin_image_path: str = "images/admin.jpg", tolerance: float = 0.6):
        """
        Initialize the face lock system
        
        Args:
            admin_image_path: Path to admin photo
            tolerance: Face matching tolerance (0.6 = strict, 0.6+ = lenient)
        """
        self.admin_image_path = admin_image_path
        self.tolerance = tolerance
        self.known_face_encodings = []
        self.known_face_names = []
        self.process_every_n_frames = 2  # Process every 2nd frame for speed
        self.frame_count = 0
        self.match_threshold = 3  # Require 3 consecutive matches for verification
        self.consecutive_matches = 0
        
        self.load_admin_image()
    
    def load_admin_image(self) -> bool:
        """Load and encode admin image with error handling"""
        
        if not os.path.exists(self.admin_image_path):
            logger.error(f"❌ Error: {self.admin_image_path} sapadli nahi!")
            logger.error(f"📁 Krupaya 'images' folder create kara ani admin.jpg add kara.")
            return False
        
        try:
            admin_image = face_recognition.load_image_file(self.admin_image_path)
            
            # Check if face is detected
            face_encodings = face_recognition.face_encodings(admin_image)
            
            if len(face_encodings) == 0:
                logger.error("❌ Admin photo madhe koi chehra samajla nahi!")
                logger.error("✅ Clear photo use kara jyat chehra clearly dikhte ahe.")
                return False
            
            if len(face_encodings) > 1:
                logger.warning("⚠️ Admin photo madhe 1 peksha jasta chehre ahet. Pahila chehra use hoil.")
            
            self.known_face_encodings = [face_encodings[0]]
            self.known_face_names = ["Admin"]
            logger.info("✅ Admin photo successfully load ho'la!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Admin photo load karte error: {str(e)}")
            return False
    
    def verify_admin(self, face_encoding) -> Tuple[bool, str, float]:
        """
        Verify if face matches admin with confidence score
        
        Returns:
            (is_match: bool, name: str, confidence: float)
        """
        matches = face_recognition.compare_faces(
            self.known_face_encodings, 
            face_encoding, 
            tolerance=self.tolerance
        )
        
        # Get face distances (lower = better match)
        face_distances = face_recognition.face_distance(
            self.known_face_encodings, 
            face_encoding
        )
        
        if len(face_distances) > 0:
            best_match_index = np.argmin(face_distances)
            confidence = 1 - face_distances[best_match_index]
            
            if matches[best_match_index]:
                return True, self.known_face_names[best_match_index], confidence
        
        return False, "Unknown", 0.0
    
    def run(self, on_success_callback=None):
        """
        Run the face recognition system
        
        Args:
            on_success_callback: Function to call when admin verified
        """
        
        # Camera open kara with error handling
        video_capture = cv2.VideoCapture(0)
        
        if not video_capture.isOpened():
            logger.error("❌ Camera open holay nahi! Camera properly connected ahe ka check kara.")
            return
        
        # Camera resolution set kara (performance improve karayasathi)
        video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        video_capture.set(cv2.CAP_PROP_FPS, 30)
        
        logger.info("✅ Camera chalu hot ahe... Chehra samor ana.")
        
        try:
            while True:
                ret, frame = video_capture.read()
                
                if not ret:
                    logger.error("❌ Frame capture failed!")
                    break
                
                self.frame_count += 1
                
                # Process every nth frame for better performance
                if self.frame_count % self.process_every_n_frames != 0:
                    cv2.imshow('Admin Face Lock - Live Scanner', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                    continue
                
                # BGR -> RGB conversion
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Resize for faster processing
                small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.25, fy=0.25)
                
                # Face detection
                face_locations = face_recognition.face_locations(small_frame, model="hog")  # "cnn" = slow but accurate
                face_encodings = face_recognition.face_encodings(small_frame, face_locations)
                
                # Scale face locations back
                face_locations = [(top*4, right*4, bottom*4, left*4) 
                                 for (top, right, bottom, left) in face_locations]
                
                admin_detected = False
                max_confidence = 0.0
                
                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    is_match, name, confidence = self.verify_admin(face_encoding)
                    
                    if is_match:
                        admin_detected = True
                        max_confidence = confidence
                        self.consecutive_matches += 1
                    else:
                        self.consecutive_matches = 0
                    
                    # Draw rectangle and name
                    color = (0, 255, 0) if is_match else (0, 0, 255)  # Green = match, Red = unknown
                    cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                    
                    # Add confidence score
                    label = f"{name} ({confidence:.2f})" if is_match else "Unknown"
                    cv2.putText(frame, label, (left, top - 10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
                
                # Status bar add kara
                status_text = f"Matches: {self.consecutive_matches}/{self.match_threshold}"
                cv2.putText(frame, status_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Verification complete when consecutive matches reach threshold
                if self.consecutive_matches >= self.match_threshold:
                    logger.info(f"✅ Success: Admin Verified! (Confidence: {max_confidence:.2f})")
                    
                    # Show success message
                    cv2.putText(frame, "ACCESS GRANTED!", (100, 240), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
                    cv2.imshow('Admin Face Lock - Live Scanner', frame)
                    cv2.waitKey(2000)  # Show success for 2 seconds
                    
                    if on_success_callback:
                        on_success_callback()
                    
                    break
                
                # Display frame
                cv2.imshow('Admin Face Lock - Live Scanner', frame)
                
                # Press 'q' to quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logger.info("User quit the application.")
                    break
        
        except Exception as e:
            logger.error(f"❌ Error during face recognition: {str(e)}")
        
        finally:
            video_capture.release()
            cv2.destroyAllWindows()
            logger.info("Camera closed.")


def on_admin_verified():
    """Called when admin is verified - customize as needed"""
    logger.info("🎉 Loading Admin Dashboard...")
    # Example:
    # os.system('python dashboard.py')
    # or trigger your NexDeal application here


if __name__ == "__main__":
    # Create images folder if it doesn't exist
    Path("images").mkdir(exist_ok=True)
    
    # Initialize and run
    face_lock = AdminFaceLock(
        admin_image_path="images/admin.jpg",
        tolerance=0.6  # Adjust: 0.5=strict, 0.6=moderate, 0.7=loose
    )
    
    # Check if admin image loaded successfully
    if face_lock.known_face_encodings:
        face_lock.run(on_success_callback=on_admin_verified)
    else:
        logger.error("Cannot start without admin image. Exiting...")