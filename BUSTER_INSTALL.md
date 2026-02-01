# Raspberry Pi OS Buster 10 Installation Guide

This guide provides specific instructions for installing Smart Vision Guide on Raspberry Pi OS Buster (Debian 10) with Python 3.7.3.

## System Requirements

- **Hardware**: Raspberry Pi Zero 2W (or newer)
- **OS**: Raspberry Pi OS Buster (Debian 10)
- **Python**: 3.7.3 (default on Buster)
- **Memory**: At least 512MB RAM

## Pre-Installation: System Dependencies

Buster 10 requires additional system packages for compilation of certain Python libraries.

```bash
# Update package lists
sudo apt-get update

# Install build essentials and compilation tools
sudo apt-get install -y \
  build-essential \
  cmake \
  pkg-config \
  python3-dev \
  python3-pip

# Install libraries for image processing and face recognition
sudo apt-get install -y \
  libatlas-base-dev \
  libopenblas-dev \
  liblapack-dev \
  libjpeg-dev \
  libpng-dev \
  libtiff-dev

# Install audio dependencies (for TTS with espeak)
sudo apt-get install -y espeak

# Install PulseAudio (for Bluetooth audio routing)
sudo apt-get install -y pulseaudio pulseaudio-module-bluetooth
```

## Python Environment Setup

### Option 1: Virtual Environment (Recommended)

```bash
# Navigate to project directory
cd /path/to/fullpetya-enhanced

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

### Option 2: System-wide Installation

```bash
# Upgrade pip
sudo pip3 install --upgrade pip setuptools wheel
```

## Installing Dependencies

### dlib Compilation (Most Time-Consuming)

`dlib` is required for face recognition and needs compilation on ARM devices.

**Estimated time on Pi Zero 2W: 30-60 minutes**

```bash
# Try using pre-built wheel from piwheels first
pip install dlib --index-url https://www.piwheels.org/simple

# If piwheels fails, compile from source (slower)
pip install dlib
```

**Troubleshooting dlib:**
- If compilation fails with memory errors, increase swap:
  ```bash
  sudo dphys-swapfile swapoff
  sudo nano /etc/dphys-swapfile
  # Change CONF_SWAPSIZE to 1024
  sudo dphys-swapfile setup
  sudo dphys-swapfile swapon
  ```

### Install All Requirements

```bash
# Install from requirements.txt
pip install -r requirements.txt

# This will install:
# - requests (HTTP client for API)
# - Pillow (image processing)
# - python-dotenv (environment variables)
# - gTTS (text-to-speech)
# - RPi.GPIO (GPIO control)
# - opencv-python-headless (computer vision, ARM-optimized)
# - dlib (face detection/recognition)
# - face-recognition (face recognition library)
```

**Estimated total installation time on Pi Zero 2W: 45-90 minutes**

## Configuration

1. **Copy environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file:**
   ```bash
   nano .env
   ```

3. **Set required variables:**
   ```bash
   # OpenRouter API for vision analysis
   OPENROUTER_API_KEY=your_api_key_here
   OPENROUTER_MODEL=allenai/molmo-2-8b:free
   
   # Optional: Site tracking
   OPENROUTER_SITE_URL=https://yoursite.com
   OPENROUTER_SITE_NAME=Smart Vision Guide
   
   # TTS backend (espeak is offline and faster on Pi Zero)
   TTS_BACKEND=espeak
   
   # GPIO pins (BCM numbering)
   BUTTON_MODE_PIN=17
   BUTTON_SELECT_PIN=27
   ```

4. **Test configuration:**
   ```bash
   python3 config.py
   ```

## Hardware Setup

See the main README for hardware connections. Quick reference:

- **Button 1 (Mode)**: GPIO 17 → GND
- **Button 2 (Select)**: GPIO 27 → GND
- **Camera**: Connect to CSI port

## First Run

```bash
# Test hardware components
python3 test_hardware.py

# Run the application
python3 main.py
```

## Performance Optimization for Buster 10

### 1. Reduce Image Resolution (Already Configured)

The config is pre-optimized for Pi Zero 2W:
- Camera: 512x384 (reduced from 640x480)
- Image processing: Max width 512px
- JPEG quality: 60%

### 2. Disable Desktop Environment (Headless Mode)

Free up memory by running headless:

```bash
# Disable GUI boot
sudo raspi-config
# Select: Boot Options → Console

# Or manually:
sudo systemctl set-default multi-user.target
sudo reboot
```

### 3. Enable Hardware Acceleration

```bash
# Increase GPU memory for camera
sudo raspi-config
# Select: Advanced Options → Memory Split → Set to 128
```

### 4. Optimize Network

```bash
# Use 5GHz WiFi if available (faster for API calls)
# Or use USB Ethernet adapter for more reliable connection
```

## Known Limitations on Buster 10

1. **Python 3.7.3**: Some newer libraries may not be compatible
   - Pillow capped at <10.0.0
   - OpenCV capped at <5.0.0

2. **armv6l Architecture**: Limited pre-built wheels
   - Most packages require compilation
   - Installation times are longer

3. **Limited RAM**: Pi Zero 2W has 512MB
   - One mode at a time (no concurrent analysis)
   - Garbage collection enabled after each operation

## Upgrading to Newer OS (Optional)

If you experience issues, consider upgrading to Bullseye or Bookworm:

```bash
# Check current version
cat /etc/os-release

# To upgrade (BACKUP FIRST):
# Follow official Raspberry Pi upgrade guides
```

## Troubleshooting

### ImportError: No module named 'cv2'

```bash
# Reinstall opencv-python-headless
pip uninstall opencv-python opencv-python-headless
pip install opencv-python-headless --index-url https://www.piwheels.org/simple
```

### "Cannot import name '_dlib_pybind11'"

```bash
# dlib compilation failed, rebuild:
pip uninstall dlib face-recognition
pip install dlib --no-cache-dir
pip install face-recognition
```

### "espeak: command not found"

```bash
sudo apt-get install espeak
```

### API Timeouts

- Increase timeout in config.py: `REQUEST_TIMEOUT = 60`
- Check WiFi signal strength
- Consider using Ethernet adapter

### Camera Not Detected

```bash
# Enable camera interface
sudo raspi-config
# Select: Interface Options → Camera → Enable

# Verify camera connection
vcgencmd get_camera
# Should show: supported=1 detected=1
```

## Support

For Buster 10 specific issues, check:
- Raspberry Pi forums
- piwheels.org for ARM wheel availability
- Project GitHub issues

## Performance Benchmarks (Pi Zero 2W on Buster 10)

Typical operation times:
- Camera capture: ~1 second
- Image preprocessing: ~0.5 seconds  
- API call (describe/OCR): 10-30 seconds (network dependent)
- Face recognition (local): 2-3 seconds
- TTS (espeak): <1 second

**Total workflow: 15-35 seconds per operation**
