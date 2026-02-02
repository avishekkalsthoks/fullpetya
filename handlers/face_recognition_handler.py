"""
Local Face Recognition Handler for Smart Vision Guide
Uses OpenCV LBPH (Local Binary Patterns Histograms) for offline face recognition.
Optimized for Raspberry Pi Zero 2W - NO dlib required.
"""

import os
import cv2
import numpy as np
from typing import List, Dict, Optional
import json


class FaceRecognitionHandler:
    """
    Local offline face recognition using OpenCV LBPH.
    Face database stored in directory structure: faces/person_name/image.jpg
    
    LBPH is lightweight and works well on Pi Zero 2W:
    - No compilation required (pre-built in python3-opencv)
    - Low memory usage (~50MB vs 500MB+ for dlib)
    - Fast enough for single-face recognition
    """
    
    def __init__(self, faces_dir="faces", labels_file="face_labels.json", confidence_threshold=80):
        """
        Initialize face recognition handler.
        
        Args:
            faces_dir: Directory containing face database (folder per person)
            labels_file: JSON file mapping label IDs to names
            confidence_threshold: Maximum confidence for match (lower = stricter, 50-100 typical)
        """
        self.faces_dir = faces_dir
        self.labels_file = labels_file
        self.confidence_threshold = confidence_threshold
        
        # LBPH recognizer (support both OpenCV 3 and 4)
        try:
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        except AttributeError:
            try:
                self.recognizer = cv2.face.createLBPHFaceRecognizer()
            except AttributeError:
                raise ImportError("❌ OpenCV face module is installed but recognizer functions are missing. Try: pip install opencv-contrib-python-headless")
        
        # Haar cascade for face detection (faster than HOG on Pi)
        # Support both old and new OpenCV versions
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        except AttributeError:
            # Fallback for older OpenCV versions (e.g., OpenCV 3.x on Buster)
            cascade_path = '/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml'
            if not os.path.exists(cascade_path):
                # Try alternative path
                cascade_path = '/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml'
        
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # Label mappings
        self.label_to_name = {}  # {0: "ram", 1: "sita", ...}
        self.name_to_label = {}  # {"ram": 0, "sita": 1, ...}
        
        # Load face database
        self._load_face_database()
    
    def _load_face_database(self):
        """
        Load and train LBPH recognizer from directory structure.
        
        Directory structure:
        faces/
         ├── ram/
         │    ├── img1.jpg
         │    └── img2.jpg
         ├── sita/
         │    └── img1.jpg
         └── teacher/
              └── img1.jpg
        """
        if not os.path.exists(self.faces_dir):
            print(f"⚠️  Face database directory '{self.faces_dir}' not found. Creating it...")
            os.makedirs(self.faces_dir)
            print(f"✓ Created {self.faces_dir}. Add face images in person-named folders.")
            return
        
        faces = []
        labels = []
        current_label = 0
        
        # Iterate through person folders
        for person_name in sorted(os.listdir(self.faces_dir)):
            person_path = os.path.join(self.faces_dir, person_name)
            
            # Skip if not a directory
            if not os.path.isdir(person_path):
                continue
            
            # Assign label to this person
            self.label_to_name[current_label] = person_name
            self.name_to_label[person_name] = current_label
            
            person_face_count = 0
            
            # Load all images for this person
            for image_file in os.listdir(person_path):
                if not image_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue
                
                image_path = os.path.join(person_path, image_file)
                
                try:
                    # Load image in grayscale
                    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                    
                    if image is None:
                        print(f"  ⚠️  Could not load {person_name}/{image_file}")
                        continue
                    
                    # Detect faces
                    detected_faces = self.face_cascade.detectMultiScale(
                        image,
                        scaleFactor=1.1,
                        minNeighbors=5,
                        minSize=(30, 30)
                    )
                    
                    if len(detected_faces) == 0:
                        print(f"  ⚠️  No face found in {person_name}/{image_file}")
                        continue
                    
                    if len(detected_faces) > 1:
                        print(f"  ⚠️  Multiple faces in {person_name}/{image_file}, using first")
                    
                    # Extract face region
                    x, y, w, h = detected_faces[0]
                    face_roi = image[y:y+h, x:x+w]
                    
                    # Resize to standard size for consistency
                    face_roi = cv2.resize(face_roi, (100, 100))
                    
                    faces.append(face_roi)
                    labels.append(current_label)
                    person_face_count += 1
                    print(f"  ✓ Loaded {person_name}/{image_file}")
                
                except Exception as e:
                    print(f"  ✗ Error loading {person_name}/{image_file}: {e}")
            
            if person_face_count > 0:
                current_label += 1
            else:
                # Remove label if no valid faces loaded
                del self.label_to_name[current_label]
                del self.name_to_label[person_name]
        
        # Train the recognizer
        if len(faces) > 0:
            print(f"  Training LBPH recognizer with {len(faces)} face samples...")
            self.recognizer.train(faces, np.array(labels))
            print(f"✓ Face database loaded: {len(faces)} faces for {len(self.label_to_name)} people")
            
            # Save labels mapping
            self._save_labels()
        else:
            print("⚠️  No faces loaded. Add images to faces/<person_name>/ folders.")
    
    def _save_labels(self):
        """Save label-to-name mapping to JSON file."""
        try:
            with open(self.labels_file, 'w') as f:
                json.dump(self.label_to_name, f, indent=2)
        except Exception as e:
            print(f"  ⚠️  Could not save labels: {e}")
    
    def recognize(self, image_path: str) -> str:
        """
        Recognize faces in a single captured image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Human-readable result string for TTS
        """
        try:
            # Check if we have any known faces
            if len(self.label_to_name) == 0:
                return "No faces enrolled in the database. Please add faces to the faces folder."
            
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                return "Sorry, I could not load the image."
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Resize if too large (max width 640px for Pi Zero performance)
            height, width = gray.shape[:2]
            if width > 640:
                scale = 640 / width
                new_width = 640
                new_height = int(height * scale)
                gray = cv2.resize(gray, (new_width, new_height))
            
            # Detect faces
            print("  Detecting faces...")
            detected_faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            if len(detected_faces) == 0:
                return "I don't see any faces in front of you."
            
            print(f"  Found {len(detected_faces)} face(s), recognizing...")
            
            # Identify each face
            identified_people = []
            unknown_count = 0
            
            for (x, y, w, h) in detected_faces:
                # Extract face region
                face_roi = gray[y:y+h, x:x+w]
                face_roi = cv2.resize(face_roi, (100, 100))
                
                # Predict using LBPH
                try:
                    label, confidence = self.recognizer.predict(face_roi)
                    
                    # Lower confidence = better match in LBPH
                    if confidence <= self.confidence_threshold:
                        name = self.label_to_name.get(label, "Unknown")
                        print(f"  ✓ Recognized: {name} (confidence: {confidence:.1f})")
                        
                        # Avoid duplicates
                        if name not in identified_people:
                            identified_people.append(name)
                    else:
                        print(f"  ? Unknown person (confidence: {confidence:.1f} > threshold {self.confidence_threshold})")
                        unknown_count += 1
                        
                except Exception as e:
                    print(f"  ✗ Recognition error: {e}")
                    unknown_count += 1
            
            # Format result
            return self._format_result(identified_people, unknown_count)
        
        except Exception as e:
            print(f"✗ Face recognition error: {e}")
            import traceback
            traceback.print_exc()
            return "Sorry, face recognition failed. Please try again."
    
    def recognize_from_bytes(self, image_bytes: bytes) -> str:
        """
        Recognize faces from image bytes (from camera handler).
        
        Args:
            image_bytes: JPEG image bytes
            
        Returns:
            Human-readable result string for TTS
        """
        import tempfile
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        
        try:
            result = self.recognize(tmp_path)
        finally:
            # Clean up temp file
            try:
                os.remove(tmp_path)
            except:
                pass
        
        return result
    
    def _format_result(self, identified: List[str], unknown_count: int) -> str:
        """
        Format recognition result into natural language.
        
        Args:
            identified: List of recognized people names
            unknown_count: Number of unknown faces
            
        Returns:
            Human-readable description
        """
        if len(identified) == 0 and unknown_count == 0:
            return "I don't see any faces."
        
        if len(identified) == 0 and unknown_count > 0:
            if unknown_count == 1:
                return "I see one person, but I don't recognize them."
            else:
                return f"I see {unknown_count} people, but I don't recognize any of them."
        
        # Build response for known people
        if len(identified) == 1:
            response = f"I see {identified[0]}"
        elif len(identified) == 2:
            response = f"I see {identified[0]} and {identified[1]}"
        else:
            response = "I see " + ", ".join(identified[:-1]) + f", and {identified[-1]}"
        
        # Add unknown people
        if unknown_count == 1:
            response += ", and one person I don't recognize"
        elif unknown_count > 1:
            response += f", and {unknown_count} people I don't recognize"
        
        response += "."
        
        return response
    
    def get_enrolled_people(self) -> List[str]:
        """Get list of enrolled people (unique names)."""
        return list(self.label_to_name.values())
    
    def get_stats(self) -> Dict:
        """Get face database statistics."""
        return {
            'unique_people': len(self.label_to_name),
            'people': self.get_enrolled_people()
        }
    
    def reload_database(self):
        """Reload face database (call after adding new faces)."""
        self.label_to_name = {}
        self.name_to_label = {}
        
        # Re-initialize recognizer
        try:
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        except AttributeError:
            self.recognizer = cv2.face.createLBPHFaceRecognizer()
            
        self._load_face_database()
