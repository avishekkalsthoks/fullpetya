"""
Local Face Recognition Handler for Smart Vision Guide
Uses OpenCV LBPH (Local Binary Patterns Histograms) for offline recognition.
Improved detection via DNN (Res10 SSD) with Haar fallback.
"""

from __future__ import annotations

import os
import json
from typing import List, Dict

import cv2
import numpy as np

from handlers.face_detection import FaceDetector


class FaceRecognitionHandler:
    """
    Local offline face recognition using OpenCV LBPH.
    Face database stored in directory structure: faces/person_name/image.jpg
    """

    def __init__(self, faces_dir="faces", labels_file="face_labels.json", confidence_threshold=80):
        self.faces_dir = faces_dir
        self.labels_file = labels_file
        self.confidence_threshold = confidence_threshold

        # LBPH recognizer (OpenCV contrib)
        try:
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        except AttributeError:
            try:
                self.recognizer = cv2.face.createLBPHFaceRecognizer()
            except AttributeError:
                raise ImportError("❌ OpenCV face module missing. Install opencv-contrib or python3-opencv.")

        # Detector (DNN preferred, Haar fallback)
        self.detector = FaceDetector()

        # Label mappings
        self.label_to_name: Dict[int, str] = {}
        self.name_to_label: Dict[str, int] = {}

        # Load face database
        self._load_face_database()

    def _load_face_database(self) -> None:
        """Load and train LBPH recognizer from directory structure."""
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
                        print(f"  WARN: Could not load {person_name}/{image_file}")
                        continue

                    detected_faces = self.detector.detect(image)
                    if len(detected_faces) == 0:
                        print(f"  WARN: No face found in {person_name}/{image_file}")
                        continue
                    if len(detected_faces) > 1:
                        print(f"  WARN: Multiple faces in {person_name}/{image_file}, using first")

                    x, y, w, h = detected_faces[0]
                    face_roi = image[y:y + h, x:x + w]
                    face_gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
                    face_gray = cv2.resize(face_gray, (100, 100))

                    faces.append(face_gray)
                    labels.append(current_label)
                    person_face_count += 1
                    print(f"  OK: Loaded {person_name}/{image_file}")
                except Exception as e:
                    print(f"  WARN: Error loading {person_name}/{image_file}: {e}")

            if person_face_count > 0:
                current_label += 1
            else:
                del self.label_to_name[current_label]
                del self.name_to_label[person_name]

        if len(faces) > 0:
            print(f"  Training LBPH recognizer with {len(faces)} face samples...")
            self.recognizer.train(faces, np.array(labels))
            print(f"OK: Face database loaded: {len(faces)} faces for {len(self.label_to_name)} people")
            self._save_labels()
        else:
            print("WARN: No faces loaded. Add images to faces/<person_name>/ folders.")

    def _save_labels(self) -> None:
        try:
            with open(self.labels_file, "w") as f:
                json.dump(self.label_to_name, f, indent=2)
        except Exception as e:
            print(f"WARN: Could not save labels: {e}")

    def recognize(self, image_path: str) -> str:
        """Recognize faces in a single captured image."""
        try:
            if len(self.label_to_name) == 0:
                return "No faces enrolled in the database. Please add faces to the faces folder."

            image = cv2.imread(image_path)
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

    def recognize_from_bytes(self, image_bytes: bytes) -> str:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        try:
            return self.recognize(tmp_path)
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

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

    def get_enrolled_people(self) -> List[str]:
        return list(self.label_to_name.values())

    def get_stats(self) -> Dict:
        return {
            "unique_people": len(self.label_to_name),
            "people": self.get_enrolled_people()
        }

    def reload_database(self) -> None:
        self.label_to_name = {}
        self.name_to_label = {}
        try:
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        except AttributeError:
            self.recognizer = cv2.face.createLBPHFaceRecognizer()
        self._load_face_database()
