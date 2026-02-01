"""
Local Face Recognition Handler for Smart Vision Guide
Uses face_recognition library (dlib-based HOG detector) for offline face recognition.
Optimized for Raspberry Pi Zero 2W with minimal RAM usage.
"""

import os
import face_recognition
import cv2
from typing import List, Dict, Optional


class FaceRecognitionHandler:
    """
    Local offline face recognition using HOG detector.
    Face database stored in directory structure: faces/person_name/image.jpg
    """
    
    def __init__(self, faces_dir="faces", distance_threshold=0.6):
        """
        Initialize face recognition handler.
        
        Args:
            faces_dir: Directory containing face database (folder per person)
            distance_threshold: Maximum distance for face match (0.5-0.6 recommended)
        """
        self.faces_dir = faces_dir
        self.distance_threshold = distance_threshold
        self.known_encodings = []
        self.known_names = []
        
        # Load all known faces at startup
        self._load_face_database()
    
    def _load_face_database(self):
        """
        Load face encodings from directory structure.
        
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
        
        loaded_count = 0
        
        # Iterate through person folders
        for person_name in os.listdir(self.faces_dir):
            person_path = os.path.join(self.faces_dir, person_name)
            
            # Skip if not a directory
            if not os.path.isdir(person_path):
                continue
            
            # Load all images for this person
            for image_file in os.listdir(person_path):
                if not image_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue
                
                image_path = os.path.join(person_path, image_file)
                
                try:
                    # Load image
                    image = face_recognition.load_image_file(image_path)
                    
                    # Detect faces using HOG
                    face_locations = face_recognition.face_locations(image, model="hog")
                    
                    if len(face_locations) == 0:
                        print(f"  ⚠️  No face found in {person_name}/{image_file}")
                        continue
                    
                    if len(face_locations) > 1:
                        print(f"  ⚠️  Multiple faces in {person_name}/{image_file}, using first")
                    
                    # Encode the first face
                    encodings = face_recognition.face_encodings(image, face_locations)
                    if encodings:
                        self.known_encodings.append(encodings[0])
                        self.known_names.append(person_name)
                        loaded_count += 1
                        print(f"  ✓ Loaded {person_name}/{image_file}")
                
                except Exception as e:
                    print(f"  ✗ Error loading {person_name}/{image_file}: {e}")
        
        print(f"✓ Face database loaded: {loaded_count} faces for {len(set(self.known_names))} people")
    
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
            if len(self.known_encodings) == 0:
                return "No faces enrolled in the database. Please add faces to the faces folder."
            
            # Load and process image
            image = face_recognition.load_image_file(image_path)
            
            # Resize if too large (max width 640px for Pi Zero performance)
            height, width = image.shape[:2]
            if width > 640:
                scale = 640 / width
                new_width = 640
                new_height = int(height * scale)
                image = cv2.resize(image, (new_width, new_height))
            
            # Detect faces using HOG (faster than CNN)
            print("  Detecting faces...")
            face_locations = face_recognition.face_locations(image, model="hog")
            
            if len(face_locations) == 0:
                return "I don't see any faces in front of you."
            
            # Encode detected faces
            print(f"  Encoding {len(face_locations)} detected face(s)...")
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            # Identify each face
            identified_people = []
            unknown_count = 0
            
            for face_encoding in face_encodings:
                # Compare with known faces
                face_distances = face_recognition.face_distance(
                    self.known_encodings, 
                    face_encoding
                )
                
                # Find best match
                if len(face_distances) > 0:
                    best_match_index = face_distances.argmin()
                    best_distance = face_distances[best_match_index]
                    
                    if best_distance <= self.distance_threshold:
                        name = self.known_names[best_match_index]
                        confidence = (1 - best_distance) * 100
                        print(f"  ✓ Recognized: {name} ({confidence:.1f}% confidence)")
                        
                        # Avoid duplicates
                        if name not in identified_people:
                            identified_people.append(name)
                    else:
                        print(f"  ? Unknown person (best distance: {best_distance:.2f})")
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
        return list(set(self.known_names))
    
    def get_stats(self) -> Dict:
        """Get face database statistics."""
        return {
            'total_encodings': len(self.known_encodings),
            'unique_people': len(set(self.known_names)),
            'people': self.get_enrolled_people()
        }
