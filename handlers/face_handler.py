"""
Face Recognition Handler using Face++ API
Optimized for Pi Zero 2W with rate limiting protection and error handling.
"""

import requests
import json
import os
import time
from typing import Optional, List, Dict
from config import FACEPP_API_KEY, FACEPP_API_SECRET, FACEPP_API_URL, FACE_DB_FILE


class FaceHandler:
    """Handler for face detection and recognition using Face++ API with rate limiting."""
    
    # Face++ free tier: 3 QPS (queries per second) = 0.33s minimum between calls
    MIN_API_DELAY = 0.4  # 400ms delay to stay safely under 3 QPS limit
    
    def __init__(self):
        if not FACEPP_API_KEY or not FACEPP_API_SECRET:
            raise RuntimeError("FACEPP_API_KEY and FACEPP_API_SECRET are required for face recognition.")
        
        self.api_key = FACEPP_API_KEY
        self.api_secret = FACEPP_API_SECRET
        self.base_url = FACEPP_API_URL
        
        # Rate limiting tracking
        self.last_api_call_time = 0
        
        # Load face database
        self.face_db = self._load_face_database()
    
    def _load_face_database(self) -> Dict:
        """Load the face database from JSON file."""
        if os.path.exists(FACE_DB_FILE):
            try:
                with open(FACE_DB_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading face database: {e}")
        return {}
    
    def _save_face_database(self):
        """Save the face database to JSON file."""
        try:
            with open(FACE_DB_FILE, 'w') as f:
                json.dump(self.face_db, f, indent=2)
        except Exception as e:
            print(f"Error saving face database: {e}")
    
    def _rate_limit_delay(self):
        """
        Enforce rate limiting delay to prevent hitting Face++ 3 QPS limit.
        Critical for Pi Zero 2W to avoid API blocking.
        """
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call_time
        
        if time_since_last_call < self.MIN_API_DELAY:
            sleep_time = self.MIN_API_DELAY - time_since_last_call
            print(f"Rate limiting: waiting {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_api_call_time = time.time()
    
    def detect_faces(self, image_bytes: bytes, retry_attempts=2) -> List[Dict]:
        """
        Detect faces in an image with rate limiting and retry logic.
        
        Args:
            image_bytes: Image data
            retry_attempts: Number of retry attempts on failure
            
        Returns:
            List of face dictionaries with face_token, bounding box, and attributes
        """
        self._rate_limit_delay()
        
        url = f"{self.base_url}/detect"
        files = {'image_file': ('image.jpg', image_bytes, 'image/jpeg')}
        data = {
            'api_key': self.api_key,
            'api_secret': self.api_secret,
            'return_attributes': 'gender,age,emotion'
        }
        
        for attempt in range(retry_attempts + 1):
            try:
                response = requests.post(url, files=files, data=data, timeout=30)
                
                # Handle rate limiting
                if response.status_code == 403:
                    print("Rate limit hit. Waiting longer...")
                    time.sleep(self.MIN_API_DELAY * 3)
                    continue
                
                response.raise_for_status()
                result = response.json()
                
                # Check for API errors
                if 'error_message' in result:
                    print(f"Face++ API error: {result['error_message']}")
                    if attempt < retry_attempts:
                        time.sleep(1)
                        continue
                    return []
                
                faces = result.get('faces', [])
                print(f"✓ Detected {len(faces)} face(s)")
                return faces
                
            except requests.exceptions.RequestException as e:
                print(f"Face detection error (attempt {attempt + 1}): {e}")
                if attempt < retry_attempts:
                    time.sleep(2)
                    continue
                return []
        
        return []
    
    def compare_faces(self, face_token1: str, face_token2: str, retry_attempts=2) -> float:
        """
        Compare two faces and return confidence score with rate limiting.
        
        Args:
            face_token1: First face token
            face_token2: Second face token
            retry_attempts: Number of retry attempts
            
        Returns:
            Confidence score between 0 and 100
        """
        self._rate_limit_delay()
        
        url = f"{self.base_url}/compare"
        data = {
            'api_key': self.api_key,
            'api_secret': self.api_secret,
            'face_token1': face_token1,
            'face_token2': face_token2
        }
        
        for attempt in range(retry_attempts + 1):
            try:
                response = requests.post(url, data=data, timeout=30)
                
                # Handle rate limiting
                if response.status_code == 403:
                    print("Rate limit hit. Waiting longer...")
                    time.sleep(self.MIN_API_DELAY * 3)
                    continue
                
                response.raise_for_status()
                result = response.json()
                
                # Check for API errors
                if 'error_message' in result:
                    print(f"Face compare error: {result['error_message']}")
                    return 0
                
                confidence = result.get('confidence', 0)
                return confidence
                
            except requests.exceptions.RequestException as e:
                print(f"Face comparison error (attempt {attempt + 1}): {e}")
                if attempt < retry_attempts:
                    time.sleep(2)
                    continue
                return 0
        
        return 0
    
    def enroll_face(self, image_bytes: bytes, person_name: str) -> bool:
        """
        Enroll a new face for a person.
        
        Args:
            image_bytes: Image containing the face
            person_name: Name to associate with the face
            
        Returns:
            True if enrollment successful
        """
        faces = self.detect_faces(image_bytes)
        
        if not faces:
            print("No faces detected for enrollment")
            return False
        
        if len(faces) > 1:
            print(f"Warning: {len(faces)} faces detected. Using the first one.")
        
        # Use the first detected face
        face_token = faces[0]['face_token']
        
        # Store in database
        self.face_db[person_name.lower()] = {
            'name': person_name,
            'face_token': face_token
        }
        
        self._save_face_database()
        print(f"✓ Enrolled {person_name}")
        return True
    
    def identify_faces(self, image_bytes: bytes, confidence_threshold: float = 70.0) -> List[Dict]:
        """
        Identify faces in an image against enrolled faces with optimized rate limiting.
        
        Args:
            image_bytes: Image to analyze
            confidence_threshold: Minimum confidence to consider a match
            
        Returns:
            List of identified people with confidence scores
        """
        detected_faces = self.detect_faces(image_bytes)
        
        if not detected_faces:
            return []
        
        identified = []
        enrolled_count = len(self.face_db)
        
        print(f"Comparing {len(detected_faces)} detected face(s) against {enrolled_count} enrolled face(s)")
        
        for face_idx, face in enumerate(detected_faces):
            face_token = face['face_token']
            
            # Compare against all enrolled faces (with rate limiting)
            best_match = None
            best_confidence = 0
            
            for person_idx, (person_name, person_data) in enumerate(self.face_db.items()):
                enrolled_token = person_data['face_token']
                
                # Progress indicator for multiple comparisons
                if enrolled_count > 3:
                    print(f"  Comparing face {face_idx + 1} with person {person_idx + 1}/{enrolled_count}...")
                
                confidence = self.compare_faces(face_token, enrolled_token)
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = person_data['name']
            
            if best_match and best_confidence >= confidence_threshold:
                print(f"✓ Identified: {best_match} ({best_confidence:.1f}% confidence)")
                identified.append({
                    'name': best_match,
                    'confidence': best_confidence,
                    'attributes': face.get('attributes', {})
                })
            else:
                print(f"  Unknown person (best match: {best_confidence:.1f}%)")
                identified.append({
                    'name': None,
                    'confidence': 0,
                    'attributes': face.get('attributes', {})
                })
        
        return identified
    
    def get_enrolled_people(self) -> List[str]:
        """Get list of enrolled people's names."""
        return [data['name'] for data in self.face_db.values()]
    
    def remove_person(self, person_name: str) -> bool:
        """Remove a person from the face database."""
        key = person_name.lower()
        if key in self.face_db:
            del self.face_db[key]
            self._save_face_database()
            print(f"✓ Removed {person_name}")
            return True
        return False
    
    def format_identification_result(self, identified: List[Dict]) -> str:
        """
        Format identification results into a natural language response.
        
        Args:
            identified: List of identified people from identify_faces()
            
        Returns:
            Human-readable description
        """
        if not identified:
            return "I don't see any faces in front of you."
        
        known_people = [p for p in identified if p['name']]
        unknown_count = len(identified) - len(known_people)
        
        if not known_people and unknown_count > 0:
            if unknown_count == 1:
                return "I see one person, but I don't recognize them."
            else:
                return f"I see {unknown_count} people, but I don't recognize any of them."
        
        parts = []
        
        # Describe known people
        for person in known_people:
            name = person['name']
            attrs = person.get('attributes', {})
            
            # Get age if available
            age_data = attrs.get('age', {})
            age = age_data.get('value') if age_data else None
            
            description = name
            if age:
                description += f", who appears to be around {age} years old"
            
            parts.append(description)
        
        # Build response
        if len(parts) == 1:
            response = f"I see {parts[0]}"
        elif len(parts) == 2:
            response = f"I see {parts[0]} and {parts[1]}"
        else:
            response = "I see " + ", ".join(parts[:-1]) + f", and {parts[-1]}"
        
        # Add unknown people
        if unknown_count == 1:
            response += ", and one person I don't recognize"
        elif unknown_count > 1:
            response += f", and {unknown_count} people I don't recognize"
        
        response += "."
        
        return response
