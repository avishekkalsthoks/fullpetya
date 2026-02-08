"""
Face Recognition Handler for Smart Vision Guide
Supports both online (cloud API) and offline (LBPH) recognition.
Online mode provides better accuracy using deep learning models.
Offline mode uses OpenCV LBPH for local recognition without internet.
"""

from __future__ import annotations

import os
import json
import io
import requests
from typing import List, Dict, Optional, Tuple

import cv2
import numpy as np

from handlers.face_detection import FaceDetector

# Try to import config values
try:
    from config import FACE_API_URL, FACE_API_TIMEOUT, FACE_DB_DIR, FACE_CONFIDENCE_THRESHOLD
except ImportError:
    FACE_API_URL = ''
    FACE_API_TIMEOUT = 15
    FACE_DB_DIR = 'faces'
    FACE_CONFIDENCE_THRESHOLD = 80


class FaceRecognitionHandler:
    """
    Hybrid face recognition supporting online (cloud API) and offline (LBPH) modes.
    Online mode: Sends images to cloud API for deep learning-based recognition.
    Offline mode: Uses OpenCV LBPH for local recognition.
    """

    def __init__(self, faces_dir=None, labels_file="face_labels.json", confidence_threshold=None):
        self.faces_dir = faces_dir or FACE_DB_DIR
        self.labels_file = labels_file
        self.confidence_threshold = confidence_threshold or FACE_CONFIDENCE_THRESHOLD

        # Cloud API configuration
        self.cloud_api_url = FACE_API_URL
        self.cloud_api_timeout = FACE_API_TIMEOUT
        self.cloud_available = bool(self.cloud_api_url)
        
        if self.cloud_available:
            print(f"OK: Cloud face recognition configured: {self.cloud_api_url}")
        else:
            print("INFO: Cloud face API not configured. Using local LBPH only.")

        # LBPH recognizer (OpenCV contrib) for offline mode
        try:
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        except AttributeError:
            try:
                self.recognizer = cv2.face.createLBPHFaceRecognizer()
            except AttributeError:
                print("WARN: OpenCV face module missing. Offline mode disabled.")
                self.recognizer = None

        # Detector (DNN preferred, Haar fallback)
        self.detector = FaceDetector()

        # Label mappings for offline mode
        self.label_to_name: Dict[int, str] = {}
        self.name_to_label: Dict[str, int] = {}

        # Load face database for offline mode
        self._load_face_database()

        # HTTP session for API calls
        self.session = requests.Session()

    def _load_face_database(self) -> None:
        """Load and train LBPH recognizer from directory structure."""
        if self.recognizer is None:
            return
            
        if not os.path.exists(self.faces_dir):
            print(f"WARN: Face database directory '{self.faces_dir}' not found. Creating it...")
            os.makedirs(self.faces_dir)
            print(f"OK: Created {self.faces_dir}. Add face images in person-named folders.")
            return

        faces = []
        labels = []
        current_label = 0

        for person_name in sorted(os.listdir(self.faces_dir)):
            person_path = os.path.join(self.faces_dir, person_name)
            if not os.path.isdir(person_path):
                continue

            self.label_to_name[current_label] = person_name
            self.name_to_label[person_name] = current_label

            person_face_count = 0
            for image_file in os.listdir(person_path):
                if not image_file.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue

                image_path = os.path.join(person_path, image_file)
                try:
                    image = cv2.imread(image_path)
                    if image is None:
                        continue

                    detected_faces = self.detector.detect(image)
                    if len(detected_faces) == 0:
                        continue

                    x, y, w, h = detected_faces[0]
                    face_roi = image[y:y + h, x:x + w]
                    face_gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
                    face_gray = cv2.resize(face_gray, (100, 100))

                    faces.append(face_gray)
                    labels.append(current_label)
                    person_face_count += 1
                except Exception:
                    pass

            if person_face_count > 0:
                current_label += 1
            else:
                if current_label in self.label_to_name:
                    del self.label_to_name[current_label]
                if person_name in self.name_to_label:
                    del self.name_to_label[person_name]

        if len(faces) > 0:
            self.recognizer.train(faces, np.array(labels))
            print(f"OK: Offline face database: {len(faces)} faces for {len(self.label_to_name)} people")
            self._save_labels()
        else:
            print("INFO: No local faces loaded. Use cloud API or add images to faces/ folders.")

    def _save_labels(self) -> None:
        try:
            with open(self.labels_file, "w") as f:
                json.dump(self.label_to_name, f, indent=2)
        except Exception:
            pass

    def _recognize_cloud(self, image_bytes: bytes) -> Tuple[bool, str]:
        """Recognize faces using cloud API."""
        if not self.cloud_available:
            return False, "Cloud API not configured"

        try:
            response = self.session.post(
                f"{self.cloud_api_url}/api/recognize",
                files={'image': ('image.jpg', image_bytes, 'image/jpeg')},
                timeout=self.cloud_api_timeout
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    faces = result.get('faces', [])
                    if not faces or result.get('count', 0) == 0:
                        return True, "I don't see any faces in front of you."
                    
                    return True, self._format_cloud_result(faces)
                else:
                    return False, result.get('message', 'Cloud recognition failed')
            else:
                return False, f"Cloud API error: {response.status_code}"

        except requests.exceptions.Timeout:
            return False, "Cloud API timeout"
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to cloud API"
        except Exception as e:
            return False, f"Cloud error: {str(e)}"

    def _format_cloud_result(self, faces: List[Dict]) -> str:
        """Format cloud API recognition result for speech."""
        identified_people = []
        unknown_count = 0

        for face in faces:
            if face.get('recognized'):
                name = face.get('person', 'Unknown')
                confidence = face.get('confidence', 0)
                # Only accept high confidence matches
                if confidence >= 0.5 and name not in identified_people:
                    identified_people.append(name)
            else:
                unknown_count += 1

        return self._format_result(identified_people, unknown_count)

    def _recognize_offline(self, image_bytes: bytes) -> str:
        """Recognize faces using local LBPH."""
        if self.recognizer is None:
            return "Offline face recognition is not available."
            
        if len(self.label_to_name) == 0:
            return "No faces enrolled in the local database."

        try:
            # Decode image from bytes
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                return "Sorry, I could not load the image."

            # Resize for speed on Pi
            height, width = image.shape[:2]
            if width > 640:
                scale = 640 / width
                new_width = 640
                new_height = int(height * scale)
                image = cv2.resize(image, (new_width, new_height))

            detected_faces = self.detector.detect(image)
            if len(detected_faces) == 0:
                return "I don't see any faces in front of you."

            identified_people = []
            unknown_count = 0

            for (x, y, w, h) in detected_faces:
                face_roi = image[y:y + h, x:x + w]
                face_gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
                face_gray = cv2.resize(face_gray, (100, 100))

                try:
                    label, confidence = self.recognizer.predict(face_gray)
                    if confidence <= self.confidence_threshold:
                        name = self.label_to_name.get(label, "Unknown")
                        if name not in identified_people:
                            identified_people.append(name)
                    else:
                        unknown_count += 1
                except Exception:
                    unknown_count += 1

            return self._format_result(identified_people, unknown_count)
        except Exception:
            return "Sorry, face recognition failed. Please try again."

    def recognize(self, image_path: str) -> str:
        """Recognize faces in a captured image (tries cloud first, then offline)."""
        try:
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            return self.recognize_from_bytes(image_bytes)
        except Exception:
            return "Sorry, I could not load the image."

    def recognize_from_bytes(self, image_bytes: bytes) -> str:
        """Recognize faces from image bytes (tries cloud first, then offline)."""
        # Try cloud API first if available
        if self.cloud_available:
            success, result = self._recognize_cloud(image_bytes)
            if success:
                return result
            # Cloud failed, fall back to offline
            print(f"INFO: Cloud recognition failed ({result}), using offline mode")

        # Use offline recognition
        return self._recognize_offline(image_bytes)

    def _format_result(self, identified: List[str], unknown_count: int) -> str:
        if len(identified) == 0 and unknown_count == 0:
            return "I don't see any faces."
        if len(identified) == 0 and unknown_count > 0:
            return "I see one person, but I don't recognize them." if unknown_count == 1 \
                else f"I see {unknown_count} people, but I don't recognize any of them."

        if len(identified) == 1:
            response = f"I see {identified[0]}"
        elif len(identified) == 2:
            response = f"I see {identified[0]} and {identified[1]}"
        else:
            response = "I see " + ", ".join(identified[:-1]) + f", and {identified[-1]}"

        if unknown_count == 1:
            response += ", and one person I don't recognize"
        elif unknown_count > 1:
            response += f", and {unknown_count} people I don't recognize"

        return response + "."

    def register_cloud(self, image_bytes: bytes, name: str) -> Tuple[bool, str]:
        """Register a new person using cloud API."""
        if not self.cloud_available:
            return False, "Cloud API not configured"

        try:
            response = self.session.post(
                f"{self.cloud_api_url}/api/register",
                files={'image': ('image.jpg', image_bytes, 'image/jpeg')},
                data={'name': name},
                timeout=self.cloud_api_timeout
            )

            if response.status_code == 200:
                result = response.json()
                return True, result.get('message', f"Registered {name}")
            else:
                error = response.json()
                return False, error.get('error', 'Registration failed')

        except Exception as e:
            return False, f"Registration error: {str(e)}"

    def train_cloud(self, images: List[bytes], name: str) -> Tuple[bool, str]:
        """Train with multiple images using cloud API."""
        if not self.cloud_available:
            return False, "Cloud API not configured"

        try:
            files = [('images', ('image.jpg', img, 'image/jpeg')) for img in images]
            response = self.session.post(
                f"{self.cloud_api_url}/api/train",
                files=files,
                data={'name': name},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return True, result.get('message', f"Trained {name}")
            else:
                error = response.json()
                return False, error.get('error', 'Training failed')

        except Exception as e:
            return False, f"Training error: {str(e)}"

    def list_cloud_people(self) -> Tuple[bool, List[str]]:
        """List registered people from cloud API."""
        if not self.cloud_available:
            return False, []

        try:
            response = self.session.get(
                f"{self.cloud_api_url}/api/list",
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                return True, result.get('people', [])
            return False, []
        except Exception:
            return False, []

    def get_enrolled_people(self) -> List[str]:
        """Get list of enrolled people (tries cloud first)."""
        if self.cloud_available:
            success, people = self.list_cloud_people()
            if success:
                return people
        return list(self.label_to_name.values())

    def get_stats(self) -> Dict:
        """Get recognition statistics."""
        people = self.get_enrolled_people()
        return {
            "unique_people": len(people),
            "people": people,
            "cloud_available": self.cloud_available,
            "offline_people": len(self.label_to_name)
        }

    def reload_database(self) -> None:
        """Reload the local face database."""
        self.label_to_name = {}
        self.name_to_label = {}
        if self.recognizer is not None:
            try:
                self.recognizer = cv2.face.LBPHFaceRecognizer_create()
            except AttributeError:
                self.recognizer = cv2.face.createLBPHFaceRecognizer()
        self._load_face_database()

    def test_cloud_connection(self) -> Tuple[bool, str]:
        """Test connection to cloud API."""
        if not self.cloud_available:
            return False, "Cloud API URL not configured"

        try:
            response = self.session.get(
                f"{self.cloud_api_url}/",
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                status = result.get('status', 'unknown')
                people = result.get('registered_people', 0)
                return True, f"Connected! Status: {status}, Registered: {people} people"
            return False, f"API returned error: {response.status_code}"
        except requests.exceptions.Timeout:
            return False, "Connection timeout"
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to API"
        except Exception as e:
            return False, str(e)
