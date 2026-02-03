#!/usr/bin/env bash
set -euo pipefail

echo "=============================================="
echo "Smart Vision Guide - Download Local Models"
echo "=============================================="

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODELS_DIR="${PROJECT_DIR}/models"
mkdir -p "${MODELS_DIR}"

echo "[1/3] Downloading Face Detector (Res10 SSD)..."
FACE_PROTO_URL="https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt"
FACE_MODEL_URL="https://raw.githubusercontent.com/opencv/opencv_3rdparty/68670b0f0f5d2e102c26931d5c39d3531b7f01aa/dnn_samples_face_detector/res10_300x300_ssd_iter_140000.caffemodel"

curl -L "${FACE_PROTO_URL}" -o "${MODELS_DIR}/face_detector_deploy.prototxt"
curl -L "${FACE_MODEL_URL}" -o "${MODELS_DIR}/face_detector.caffemodel"

echo "[2/3] Downloading MobileNet-SSD (Object Detector)..."
OBJ_PROTO_URL="https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/deploy.prototxt"
OBJ_MODEL_URL="https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/mobilenet_iter_73000.caffemodel"

curl -L "${OBJ_PROTO_URL}" -o "${MODELS_DIR}/mobilenet_ssd_deploy.prototxt"
curl -L "${OBJ_MODEL_URL}" -o "${MODELS_DIR}/mobilenet_ssd.caffemodel"

echo "[3/3] Downloading Vosk Small English Model (Optional)..."
VOSK_ZIP_URL="https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
VOSK_ZIP_PATH="${MODELS_DIR}/vosk-model-small-en-us-0.15.zip"

if [ ! -d "${MODELS_DIR}/vosk-model-small-en-us-0.15" ]; then
    curl -L "${VOSK_ZIP_URL}" -o "${VOSK_ZIP_PATH}"
    unzip -q "${VOSK_ZIP_PATH}" -d "${MODELS_DIR}"
    rm -f "${VOSK_ZIP_PATH}"
    echo "✓ Vosk model downloaded"
else
    echo "✓ Vosk model already present"
fi

echo ""
echo "✅ Model download complete."
echo "Models stored in: ${MODELS_DIR}"
