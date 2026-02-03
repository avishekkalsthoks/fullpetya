"""
Face Detection Utility
Uses OpenCV DNN (Res10 SSD) when available, falls back to Haar cascade.
Optimized for Raspberry Pi Zero 2W.
"""

from __future__ import annotations

import os
from typing import List, Tuple

import cv2
import numpy as np

from config import FACE_DNN_PROTO, FACE_DNN_MODEL, FACE_DNN_CONFIDENCE


class FaceDetector:
    def __init__(self):
        self.dnn_net = None
        self.haar = None
        self._load_dnn()
        if self.dnn_net is None:
            self._load_haar()

    def _load_dnn(self) -> None:
        if not os.path.isfile(FACE_DNN_PROTO) or not os.path.isfile(FACE_DNN_MODEL):
            return
        try:
            self.dnn_net = cv2.dnn.readNetFromCaffe(FACE_DNN_PROTO, FACE_DNN_MODEL)
            self.dnn_net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.dnn_net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            print("OK: DNN face detector initialized")
        except Exception as e:
            print(f"WARN: Failed to load DNN face detector: {e}")
            self.dnn_net = None

    def _load_haar(self) -> None:
        local_path = "haarcascade_frontalface_default.xml"
        path = None

        # OpenCV data path
        try:
            candidate = cv2.data.haarcascades + local_path
            if os.path.exists(candidate):
                path = candidate
        except AttributeError:
            pass

        # Common system paths
        if path is None:
            for candidate in [
                "/usr/share/opencv/haarcascades/" + local_path,
                "/usr/share/opencv4/haarcascades/" + local_path,
                "/usr/local/share/opencv/haarcascades/" + local_path,
                local_path
            ]:
                if os.path.exists(candidate):
                    path = candidate
                    break

        if path is None:
            print("WARN: Haar cascade not found.")
            self.haar = None
            return

        self.haar = cv2.CascadeClassifier(path)
        if self.haar.empty():
            print(f"WARN: Could not load Haar cascade from {path}")
            self.haar = None
        else:
            print("OK: Haar cascade loaded")

    def detect(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Return face bounding boxes (x, y, w, h)."""
        if image is None:
            return []

        if self.dnn_net is not None:
            return self._detect_dnn(image)

        if self.haar is not None:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = self.haar.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            return list(faces)

        return []

    def _detect_dnn(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        h, w = image.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))
        self.dnn_net.setInput(blob)
        detections = self.dnn_net.forward()

        boxes = []
        for i in range(detections.shape[2]):
            confidence = float(detections[0, 0, i, 2])
            if confidence < FACE_DNN_CONFIDENCE:
                continue
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (x1, y1, x2, y2) = box.astype("int")
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w - 1, x2), min(h - 1, y2)
            boxes.append((x1, y1, x2 - x1, y2 - y1))
        return boxes
