"""
Face Recognition Handler for Smart Vision Guide
Cloud-only mode - sends images to cloud API for recognition.
Optimized for Raspberry Pi Zero 2W (no local processing).
"""

import requests
from typing import List, Dict, Tuple

# Try to import config values
try:
    from config import FACE_API_URL, FACE_API_TIMEOUT
except ImportError:
    FACE_API_URL = ''
    FACE_API_TIMEOUT = 15


class FaceRecognitionHandler:
    """
    Cloud-based face recognition handler.
    Sends images to cloud API for processing - no local computation.
    Optimized for lightweight devices like Raspberry Pi Zero 2W.
    """

    def __init__(self, faces_dir=None, labels_file=None, confidence_threshold=None):
        # Cloud API configuration
        self.cloud_api_url = FACE_API_URL
        self.cloud_api_timeout = FACE_API_TIMEOUT
        
        if not self.cloud_api_url:
            print("ERROR: FACE_API_URL not configured. Face recognition will not work.")
            print("       Set FACE_API_URL in your .env file.")
        else:
            print(f"OK: Cloud face recognition: {self.cloud_api_url}")

        # HTTP session for API calls
        self.session = requests.Session()

    def recognize_from_bytes(self, image_bytes: bytes) -> str:
        """Recognize faces from image bytes using cloud API."""
        if not self.cloud_api_url:
            return "Face recognition is not configured. Please set FACE_API_URL."

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
                        return "I don't see any faces in front of you."
                    
                    return self._format_result(faces)
                else:
                    return result.get('message', 'Face recognition failed.')
            else:
                return "Could not connect to face recognition service."

        except requests.exceptions.Timeout:
            return "Face recognition timed out. Please try again."
        except requests.exceptions.ConnectionError:
            return "Cannot connect to face recognition service. Check your internet."
        except Exception as e:
            return f"Face recognition error. Please try again."

    def recognize(self, image_path: str) -> str:
        """Recognize faces in a captured image."""
        try:
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            return self.recognize_from_bytes(image_bytes)
        except Exception:
            return "Sorry, I could not load the image."

    def _format_result(self, faces: List[Dict]) -> str:
        """Format cloud API recognition result for speech."""
        identified_people = []
        unknown_count = 0

        for face in faces:
            if face.get('recognized'):
                name = face.get('person', 'Unknown')
                confidence = face.get('confidence', 0)
                # Only accept matches with decent confidence
                if confidence >= 0.4 and name not in identified_people:
                    identified_people.append(name)
            else:
                unknown_count += 1

        # Build response
        if len(identified_people) == 0 and unknown_count == 0:
            return "I don't see any faces."
        
        if len(identified_people) == 0 and unknown_count > 0:
            if unknown_count == 1:
                return "I see one person, but I don't recognize them."
            return f"I see {unknown_count} people, but I don't recognize any of them."

        if len(identified_people) == 1:
            response = f"I see {identified_people[0]}"
        elif len(identified_people) == 2:
            response = f"I see {identified_people[0]} and {identified_people[1]}"
        else:
            response = "I see " + ", ".join(identified_people[:-1]) + f", and {identified_people[-1]}"

        if unknown_count == 1:
            response += ", and one person I don't recognize"
        elif unknown_count > 1:
            response += f", and {unknown_count} people I don't recognize"

        return response + "."

    def register_cloud(self, image_bytes: bytes, name: str) -> Tuple[bool, str]:
        """Register a new person using cloud API."""
        if not self.cloud_api_url:
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
        if not self.cloud_api_url:
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

    def get_enrolled_people(self) -> List[str]:
        """Get list of enrolled people from cloud API."""
        if not self.cloud_api_url:
            return []

        try:
            response = self.session.get(
                f"{self.cloud_api_url}/api/list",
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                return result.get('people', [])
            return []
        except Exception:
            return []

    def get_stats(self) -> Dict:
        """Get recognition statistics from cloud."""
        people = self.get_enrolled_people()
        return {
            "unique_people": len(people),
            "people": people,
            "cloud_available": bool(self.cloud_api_url)
        }

    def test_cloud_connection(self) -> Tuple[bool, str]:
        """Test connection to cloud API."""
        if not self.cloud_api_url:
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

    # Legacy method stubs for compatibility
    def reload_database(self) -> None:
        """No-op for cloud-only mode."""
        pass
