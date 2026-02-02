#!/usr/bin/env bash
set -euo pipefail

# Smart Vision Guide - Raspberry Pi Zero 2 W Setup
# Local face recognition using OpenCV LBPH (NO dlib)
# Optimized for low memory systems

echo "=============================================="
echo "Smart Vision Guide - Pi Zero 2W Setup"
echo "Local Face Recognition (OpenCV LBPH)"
echo "Optimized for minimal memory footprint"
echo "=============================================="

# Check Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "⚠️  Warning: Not running on Raspberry Pi"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
fi

echo ""
echo "[1/8] Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

echo ""
echo "[2/8] Installing system dependencies..."
echo "NOTE: Heavy packages installed via apt to avoid compilation"

sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-numpy \
    python3-opencv \
    python3-pil \
    python3-pyaudio \
    python3-requests \
    python3-rpi.gpio \
    opencv-data \
    libatlas-base-dev \
    libopenblas-dev \
    libportaudio2 \
    portaudio19-dev \
    libasound2-dev \
    pulseaudio \
    pulseaudio-module-bluetooth \
    bluez \
    bluetooth \
    libbluetooth-dev \
    sox \
    espeak \
    ffmpeg \
    mpg123 \
    alsa-utils \
    libraspberrypi0 \
    libraspberrypi-dev \
    libraspberrypi-bin \
    libgfortran5 \
    git \
    wget \
    curl

echo ""
echo "[3/8] Loading legacy Pi camera driver..."
sudo modprobe bcm2835-v4l2 || true

if ! grep -q bcm2835-v4l2 /etc/modules 2>/dev/null; then
    echo "bcm2835-v4l2" | sudo tee -a /etc/modules
fi

echo ""
echo "[4/8] Configuring GPU memory & camera..."
if [ -f /boot/config.txt ]; then
    sudo cp /boot/config.txt /boot/config.txt.bak.$(date +%s)

    grep -q "gpu_mem=128" /boot/config.txt || echo "gpu_mem=128" | sudo tee -a /boot/config.txt
    grep -q "start_x=1" /boot/config.txt || echo "start_x=1" | sudo tee -a /boot/config.txt
fi

echo ""
echo "[5/8] Enabling interfaces..."
sudo raspi-config nonint do_camera 0 || true
sudo raspi-config nonint do_i2c 0 || true
sudo raspi-config nonint do_spi 0 || true

echo ""
echo "[6/8] Creating Python virtual environment..."
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

rm -rf venv
python3 -m venv venv --system-site-packages
source venv/bin/activate

echo "✓ Virtual environment created"

echo ""
echo "[7/8] Installing pure-Python dependencies..."
python3 -m pip install --upgrade pip setuptools wheel

# requirements.txt should ONLY contain pure-Python libs
pip install -r requirements.txt

# Verify OpenCV face module
python3 - <<EOF
import cv2
if not hasattr(cv2, "face"):
    raise SystemExit("❌ OpenCV face module missing")
print("✓ OpenCV face module available (LBPH ready)")
EOF

echo ""
echo "[8/8] Final setup..."

# Environment file
[ -f .env ] || cp .env.example .env

# Face database directory
mkdir -p faces
[ -f face_labels.json ] || echo "{}" > face_labels.json

# Audio permissions
sudo usermod -a -G audio "$USER" || true

# Enable Bluetooth audio
if [ -f /etc/pulse/default.pa ]; then
    grep -q module-bluetooth-discover /etc/pulse/default.pa || \
    echo "load-module module-bluetooth-discover" | sudo tee -a /etc/pulse/default.pa
fi

echo ""
echo "=============================================="
echo "✅ Setup complete (Pi Zero 2 W safe)"
echo "Local Face Recognition: OpenCV LBPH"
echo "=============================================="

echo ""
echo "⚠️ Reboot required to finish setup"
read -p "Reboot now? (y/n) " -n 1 -r
echo
[[ $REPLY =~ ^[Yy]$ ]] && sudo reboot
