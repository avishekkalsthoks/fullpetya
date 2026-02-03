"""
Local Vision Handler for Smart Vision Guide
Offline-friendly analysis using lightweight OpenCV DNN + Tesseract OCR.
Optimized for Raspberry Pi Zero 2W.
"""

from __future__ import annotations

import os
from typing import List, Dict, Tuple, Optional

import cv2
import numpy as np

from config import (
    LOCAL_MODEL_DIR,
    OBJECT_DNN_PROTO,
    OBJECT_DNN_MODEL,
    OBJECT_DNN_CONFIDENCE,
    TESSERACT_CMD
)


class LocalVisionHandler:
    """
    Offline vision fallback:
    - Object detection (MobileNet-SSD)
    - Scene summary
    - Offline OCR (Tesseract)
    """

    # MobileNet-SSD (Caffe) class labels
    LABELS = [
        "background", "aeroplane", "bicycle", "bird", "boat",
        "bottle", "bus", "car", "cat", "chair", "cow",
        "diningtable", "dog", "horse", "motorbike", "person",
        "pottedplant", "sheep", "sofa", "train", "tvmonitor"
    ]

    # Simple synonym map for search mode
    SYNONYMS = {
        "bike": "bicycle",
        "bicycle": "bicycle",
        "motorcycle": "motorbike",
        "motorbike": "motorbike",
        "tv": "tvmonitor",
        "television": "tvmonitor",
        "sofa": "sofa",
        "couch": "sofa",
        "plant": "pottedplant",
        "table": "diningtable",
        "dining table": "diningtable",
        "person": "person",
        "people": "person"
    }

    def __init__(self, model_dir: Optional[str] = None):
        self.model_dir = model_dir or LOCAL_MODEL_DIR
        self.net = None
        self._load_object_detector()
        self._init_ocr()

    def _load_object_detector(self) -> None:
        """Load MobileNet-SSD object detector if model files exist."""
        proto_path = OBJECT_DNN_PROTO
        model_path = OBJECT_DNN_MODEL

        if not os.path.isfile(proto_path) or not os.path.isfile(model_path):
            print("WARN: Local object detector model not found.")
            print(f"      Expected: {proto_path}")
            print(f"      Expected: {model_path}")
            self.net = None
            return

        try:
            self.net = cv2.dnn.readNetFromCaffe(proto_path, model_path)
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            print("OK: Local object detector initialized (MobileNet-SSD)")
        except Exception as e:
            print(f"WARN: Failed to load object detector: {e}")
            self.net = None

    def _init_ocr(self) -> None:
        """Initialize Tesseract OCR if available."""
        self.ocr_available = False
        try:
            import pytesseract  # type: ignore
            if TESSERACT_CMD:
                pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
            self.pytesseract = pytesseract
            self.ocr_available = True
            print("OK: Tesseract OCR available")
        except Exception as e:
            print(f"WARN: Tesseract OCR not available: {e}")
            self.ocr_available = False

    def _decode_image(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """Decode JPEG/PNG bytes to OpenCV BGR image."""
        if not image_bytes:
            return None
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img

    def _describe_position(self, box: Tuple[int, int, int, int], w: int, h: int) -> str:
        """Return a short position description."""
        x1, y1, x2, y2 = box
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0

        if cx < w * 0.33:
            horiz = "left"
        elif cx > w * 0.66:
            horiz = "right"
        else:
            horiz = "center"

        if cy < h * 0.33:
            vert = "upper"
        elif cy > h * 0.66:
            vert = "lower"
        else:
            vert = "middle"

        if horiz == "center":
            return vert
        if vert == "middle":
            return horiz
        return f"{vert} {horiz}"

    def _estimate_distance(self, box: Tuple[int, int, int, int], w: int, h: int) -> str:
        """Heuristic distance estimate based on bounding box size."""
        x1, y1, x2, y2 = box
        area = max(1, (x2 - x1) * (y2 - y1))
        frame_area = max(1, w * h)
        ratio = area / frame_area

        if ratio > 0.25:
            return "very close, within one step"
        if ratio > 0.12:
            return "close, about one to two steps away"
        if ratio > 0.06:
            return "a few steps away"
        return "farther away"

    def detect_objects(self, image_bytes: bytes, top_k: int = 6) -> List[Dict]:
        """Run object detection and return top detections."""
        if self.net is None:
            return []

        img = self._decode_image(image_bytes)
        if img is None:
            return []

        (h, w) = img.shape[:2]
        blob = cv2.dnn.blobFromImage(
            cv2.resize(img, (300, 300)),
            0.007843,
            (300, 300),
            127.5
        )
        self.net.setInput(blob)
        detections = self.net.forward()

        results = []
        for i in range(detections.shape[2]):
            confidence = float(detections[0, 0, i, 2])
            if confidence < OBJECT_DNN_CONFIDENCE:
                continue

            idx = int(detections[0, 0, i, 1])
            label = self.LABELS[idx] if idx < len(self.LABELS) else "unknown"

            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (x1, y1, x2, y2) = box.astype("int")

            results.append({
                "label": label,
                "confidence": confidence,
                "box": (x1, y1, x2, y2),
                "position": self._describe_position((x1, y1, x2, y2), w, h),
                "distance": self._estimate_distance((x1, y1, x2, y2), w, h)
            })

        results.sort(key=lambda r: r["confidence"], reverse=True)
        return results[:top_k]

    def describe_scene(self, image_bytes: bytes) -> str:
        """Generate a brief offline scene description."""
        detections = self.detect_objects(image_bytes)
        if not detections:
            return "I couldn't identify clear objects offline. Try better lighting or go online."

        # Count people
        people = [d for d in detections if d["label"] == "person"]
        objects = [d for d in detections if d["label"] != "person"]

        parts = []
        if people:
            if len(people) == 1:
                p = people[0]
                parts.append(f"I see one person in the {p['position']}, {p['distance']}.")
            else:
                parts.append(f"I see {len(people)} people nearby.")

        # Describe top objects
        if objects:
            top = objects[:3]
            obj_phrases = []
            for d in top:
                obj_phrases.append(f"{d['label']} on the {d['position']} ({d['distance']})")
            parts.append("Notable objects: " + ", ".join(obj_phrases) + ".")

        # Basic obstacle hint
        obstacles = [d for d in detections if d["label"] in {"chair", "sofa", "diningtable", "person", "bicycle", "motorbike", "car"}]
        if obstacles:
            parts.append("Potential obstacles are ahead. Please move carefully.")

        return " ".join(parts)

    def search_object(self, image_bytes: bytes, query: str) -> str:
        """Offline object search using local detector."""
        if not query:
            return "I didn't hear a search target."

        query_norm = query.strip().lower()
        target = self.SYNONYMS.get(query_norm, query_norm)

        detections = self.detect_objects(image_bytes, top_k=10)
        if not detections:
            return "I couldn't identify objects offline. Try better lighting or go online."

        matches = [d for d in detections if d["label"] == target]
        if matches:
            d = matches[0]
            return f"Yes, I see {query_norm} in the {d['position']}, {d['distance']}."

        # If target not recognized by local model
        if target not in self.LABELS and target not in self.SYNONYMS.values():
            return (
                "Offline search supports common items like person, chair, bottle, car, dog, cat, and bicycle. "
                "Try a simpler word or go online for more detailed search."
            )

        return f"No, I don't see {query_norm} right now."

    def ocr_text(self, image_bytes: bytes) -> str:
        """Offline OCR using Tesseract."""
        if not self.ocr_available:
            return "Offline OCR is not available. Please install Tesseract."

        img = self._decode_image(image_bytes)
        if img is None:
            return "I couldn't read the image."

        # Preprocess for OCR
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 7, 50, 50)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        try:
            text = self.pytesseract.image_to_string(thresh, lang="eng")
        except Exception as e:
            return f"Offline OCR failed: {e}"

        cleaned = " ".join(text.split())
        if not cleaned:
            return "I don't see any readable text."
        return f"I can read: {cleaned}"

    def get_status(self) -> Dict:
        """Return availability status of local vision components."""
        return {
            "object_detector": bool(self.net),
            "ocr": self.ocr_available
        }
