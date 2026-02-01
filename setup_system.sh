#!/usr/bin/env bash
set -euo pipefail

# Smart Vision Guide - Raspberry Pi Zero 2W Optimized Setup Script
# CRITICAL: This script installs heavy binary packages (numpy, opencv, pillow, pyaudio) via apt
# to avoid memory exhaustion and compilation failures on Pi Zero 2W (512MB RAM).

echo "=============================================="
echo "Smart Vision Guide - Pi Zero 2W Setup"
echo "Optimized for minimal memory footprint"
echo "=============================================="

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "⚠️  Warning: This script is designed for Raspberry Pi."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "[1/8] Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

echo ""
echo "[2/8] Installing system dependencies..."
echo "NOTE: Installing numpy, opencv, pillow, and pyaudio via apt (not pip)"
echo "This prevents memory exhaustion during compilation on Pi Zero 2W"
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-numpy \
    python3-opencv \
    python3-pil \
    python3-pyaudio \
    python3-requests \
    python3-rpi.gpio \
    libatlas-base-dev \
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
    libopenblas-dev \
    git \
    wget \
    curl \
    cmake \
    libboost-python-dev \
    python3-dlib

echo ""
echo "[3/8] Loading camera driver for legacy Pi Camera..."
sudo modprobe bcm2835-v4l2 || true

# Ensure driver loads at boot
if ! grep -q bcm2835-v4l2 /etc/modules 2>/dev/null; then
    echo "bcm2835-v4l2" | sudo tee -a /etc/modules
    echo "✓ Added bcm2835-v4l2 to /etc/modules"
fi

echo ""
echo "[4/8] Configuring camera and GPU memory..."
# Backup config.txt
if [ -f /boot/config.txt ]; then
    sudo cp /boot/config.txt /boot/config.txt.bak.$(date +%Y%m%d_%H%M%S) || true
    
    # Set GPU memory for camera
    if ! grep -q "gpu_mem=128" /boot/config.txt; then
        echo "gpu_mem=128" | sudo tee -a /boot/config.txt
        echo "✓ Set gpu_mem=128"
    fi
    
    # Enable camera
    if ! grep -q "start_x=1" /boot/config.txt; then
        echo "start_x=1" | sudo tee -a /boot/config.txt
        echo "✓ Enabled camera (start_x=1)"
    fi
fi

# Enable camera via raspi-config
echo ""
echo "[5/8] Enabling interfaces..."
sudo raspi-config nonint do_camera 0 2>/dev/null || true
sudo raspi-config nonint do_i2c 0 2>/dev/null || true
sudo raspi-config nonint do_spi 0 2>/dev/null || true

echo ""
echo "[6/8] Creating Python virtual environment..."
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists. Removing old venv..."
    rm -rf venv
fi

# CRITICAL: Use --system-site-packages to access apt-installed packages
python3 -m venv venv --system-site-packages
echo "✓ Created venv with --system-site-packages"

source venv/bin/activate

echo ""
echo "[7/8] Installing pure-Python packages..."
python3 -m pip install --upgrade pip setuptools wheel

# Install only pure-Python packages (requirements.txt)
pip install -r requirements.txt

echo ""
echo "[8/8] Setting up configuration..."

# Create .env from example
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ Created .env file from example"
    echo "⚠️  IMPORTANT: Edit .env with your API credentials!"
else
    echo "✓ .env file already exists"
fi

# Create face database
if [ ! -f "face_database.json" ]; then
    echo "{}" > face_database.json
    echo "✓ Created empty face database"
fi

# Set up audio permissions
sudo usermod -a -G audio "$USER" 2>/dev/null || true

# Configure pulseaudio for Bluetooth
if [ -f /etc/pulse/default.pa ]; then
    if ! grep -q "load-module module-bluetooth-discover" /etc/pulse/default.pa; then
        echo "load-module module-bluetooth-discover" | sudo tee -a /etc/pulse/default.pa
        echo "✓ Enabled Bluetooth audio in PulseAudio"
    fi
fi

# Create systemd service file
echo ""
echo "Creating systemd service file (optional)..."
cat > smart-vision.service <<EOF
[Unit]
Description=Smart Vision Guide - Assistive Device for Visually Impaired
After=network.target sound.target bluetooth.target
Wants=bluetooth.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PYTHONUNBUFFERED=1
ExecStart=$PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Created smart-vision.service"

echo ""
echo "=============================================="
echo "✅ Setup Complete!"
echo "=============================================="
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Configure API credentials:"
echo "   nano .env"
echo ""
echo "2. Get your API keys:"
echo "   • Hugging Face: https://huggingface.co/settings/tokens"
echo "   • Face++ (optional): https://www.faceplusplus.com/"
echo ""
echo "3. Pair Bluetooth audio device:"
echo "   bluetoothctl"
echo "   > scan on"
echo "   > pair XX:XX:XX:XX:XX:XX"
echo "   > trust XX:XX:XX:XX:XX:XX"
echo "   > connect XX:XX:XX:XX:XX:XX"
echo ""
echo "4. Test hardware:"
echo "   source venv/bin/activate"
echo "   python3 test_hardware.py"
echo ""
echo "5. Run the application:"
echo "   python3 main.py"
echo ""
echo "📦 Optional: Install as system service:"
echo "   sudo cp smart-vision.service /etc/systemd/system/"
echo "   sudo systemctl enable smart-vision"
echo "   sudo systemctl start smart-vision"
echo ""
echo "💡 Memory Optimization Tips:"
echo "   • The venv uses --system-site-packages for apt packages"
echo "   • This saves ~200MB RAM vs pip-compiled packages"
echo "   • Monitor memory: free -h or htop"
echo "   • Monitor temperature: vcgencmd measure_temp"
echo ""
echo "=============================================="

# Check if reboot is required
if [ -f /var/run/reboot-required ] || ! lsmod | grep -q bcm2835_v4l2; then
    echo ""
    echo "⚠️  A reboot is required to complete setup."
    echo "    (Camera driver or system updates)"
    read -p "Reboot now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo reboot
    else
        echo "⚠️  Please reboot manually: sudo reboot"
    fi
fi

echo ""
echo "Setup script finished successfully!"
