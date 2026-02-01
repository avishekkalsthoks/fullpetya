# Smart Vision Guide (Raspberry Pi Zero 2W - Optimized)

An enhanced assistive vision device for visually impaired users, **specifically optimized for Raspberry Pi Zero 2W** with 512MB RAM. Features 4 intelligent modes: scene description, text reading (OCR), face recognition, and object search.

## 🎯 Key Optimizations for Pi Zero 2W

- **Memory-Efficient Installation**: Uses apt packages (NOT pip) for heavy libraries to avoid memory exhaustion
- **Reduced Image Processing**: Optimized resolution (512x384) and compression (60% JPEG quality) for faster processing
- **Retry Logic**: Automatic retries for network and API failures
- **Rate Limiting**: Built-in protection for Face++ API 3 QPS limit
- **Watchdog Timer**: Prevents hung operations with 60-second timeout
- **Bluetooth Audio**: Full PulseAudio support for stable Bluetooth headphone connection

## Features

### 4 Operating Modes

| Mode | Description |
|------|-------------|
| **Describe** | Describes the scene, objects, and surroundings |
| **OCR** | Reads visible text (menus, signs, books, labels) |
| **Face** | Identifies enrolled people in the frame |
| **Search** | Answers questions about specific objects in view |

### Simple 2-Button Interface

**Hardware Controls:**
- **Button 1 (GPIO 17) - Mode Toggle**: Cycles through modes
  - Press to cycle: Describe → OCR → Face → Search → Shutdown → (repeat)
  - Device announces each mode as you cycle
  
- **Button 2 (GPIO 27) - Select/Execute**: Runs the current mode
  - Press to execute the currently selected mode
  - In shutdown mode: powers off the system

**Usage Example:**
1. Press Button 1 until you hear "Text reading mode"
2. Press Button 2 to capture and read text

## Quick Start

### 1. Hardware Setup

Connect **2 tactile push-button switches** to the following GPIO pins:
```
Button 1 (Mode Toggle)     → GPIO 17 → Ground
Button 2 (Select/Execute)  → GPIO 27 → Ground
```

Each button connects between the GPIO pin and Ground. The Pi's internal pull-up resistors are used, so no external resistors are needed.

### 2. Software Installation

⚠️ **CRITICAL**: This installation method is specifically designed for Pi Zero 2W to avoid memory exhaustion.

On your Raspberry Pi Zero 2W:

```bash
# Clone the repository
git clone https://github.com/yourusername/smart-vision-guide.git
cd smart-vision-guide

# Run the optimized setup script (apt-based installation)
sudo bash setup_system.sh
```

**What the setup script does:**
- Installs numpy, opencv, pillow, pyaudio via **apt** (pre-compiled binaries)
- Creates venv with `--system-site-packages` to access apt packages
- Installs only pure-Python packages via pip (requests, dotenv, gTTS)
- Configures camera driver (bcm2835-v4l2)
- Sets GPU memory allocation for camera
- Configures PulseAudio for Bluetooth audio

**Estimated time**: ~10-15 minutes (vs hours for pip compilation)

### 3. Configuration

Copy the example environment file and fill in your API credentials:

```bash
cp .env.example .env
nano .env
```

**Required API credentials:**

1. **Hugging Face Token** (for Describe, OCR, Search modes):
   - Get from: https://huggingface.co/settings/tokens
   - Free tier: ~few hundred requests/hour
   - Add to `.env`: `HF_TOKEN=hf_your_token_here`

**Face Recognition** runs fully offline (no API required)!

### 4. Pair Bluetooth Audio

For best experience with Bluetooth headphones/speaker:

```bash
bluetoothctl
scan on
# Find your device address (e.g., AA:BB:CC:DD:EE:FF)
pair AA:BB:CC:DD:EE:FF
trust AA:BB:CC:DD:EE:FF
connect AA:BB:CC:DD:EE:FF
exit
```

The system automatically routes audio to Bluetooth via PulseAudio.

### 5. Test Hardware

```bash
source venv/bin/activate
python3 test_hardware.py
```

This will test: Camera, Audio, GPIO buttons, API connections.

### 6. Run the Application

```bash
source venv/bin/activate
python3 main.py
```

## Face Enrollment (Local Offline System)

The face recognition system runs **completely offline** using the `face_recognition` library (dlib HOG detector). No cloud APIs or internet connection required for face mode!

**Face Database Structure:**
```
faces/
 ├── ram/
 │    ├── img1.jpg
 │    ├── img2.jpg
 │    └── img3.jpg
 ├── sita/
 │    └── img1.jpg
 └── teacher/
      ├── img1.jpg
      └── img2.jpg
```

### Enrollment Methods

#### Option 1: Interactive Camera Enrollment (Recommended)
```bash
source venv/bin/activate

# Enroll a new person (captures 3 photos by default)
python3 enroll_face.py "Ram"

# Capture more photos for better accuracy
python3 enroll_face.py "Sita" --photos 5
```

Follow prompts to capture multiple photos from different angles.

#### Option 2: Import from Existing Images
```bash
# Enroll from a single image file
python3 enroll_face.py "Ram" --image path/to/ram.jpg

# Enroll multiple images manually
mkdir faces/ram
cp photo1.jpg faces/ram/img1.jpg
cp photo2.jpg faces/ram/img2.jpg
```

### Managing Enrolled Faces

```bash
# List all enrolled people
python3 enroll_face.py --list

# Remove a person
python3 enroll_face.py --remove "Ram"
```

### Tips for Best Results
- **Multiple photos**: Enroll 3-5 photos per person from different angles
- **Good lighting**: Ensure face is well-lit
- **Clear face**: No sunglasses, hats, or obstructions
- **One person per photo**: Enrollment works best with single-person photos
- **Similar conditions**: Enroll photos similar to usage conditions

## Project Structure

```
smart-vision-guide/
├── main.py                           # Main application (2-button interface)
├── config.py                         # Configuration (Pi Zero tuned)
├── requirements.txt                   # Pure-Python dependencies only
├── setup_system.sh                    # Apt-based setup script (CRITICAL)
├── .env.example                       # Example environment configuration
├── faces/                             # Local face database (folder per person)
│   ├── person1/
│   │    ├── img1.jpg
│   │    └── img2.jpg
│   └── person2/
│        └── img1.jpg
├── handlers/
│   ├── camera_handler.py              # Camera with retry logic and warmup
│   ├── audio_handler.py               # TTS with PulseAudio Bluetooth support
│   ├── ai_handler.py                  # HuggingFace with retry and caching
│   └── face_recognition_handler.py    # Local offline face recognition (dlib HOG)
├── test_hardware.py                   # Hardware test suite
├── enroll_face.py                     # Face enrollment utility
├── scripts/
│   └── reduce_memory.sh               # Memory optimization script
└── README.md                          # This file
```

## Performance

| Mode | Typical Latency | Notes |
|------|-----------------|-------|
| Describe | 5-10 seconds | Includes capture + network + processing |
| OCR | 4-8 seconds | Depends on text amount |
| Face | 2-4 seconds | **Offline, no network required** |
| Search | 5-9 seconds | Depends on query complexity |

*Latency for AI modes includes retry attempts. Face mode is purely local.*

## Troubleshooting

### Camera not working

```bash
# Enable camera interface
sudo raspi-config
# Interface Options → Camera → Enable
sudo reboot

# Manually load driver
sudo modprobe bcm2835-v4l2

# Test camera
vcgencmd get_camera
# Should show: supported=1 detected=1
```

### No audio output / Bluetooth stuttering

```bash
# Check PulseAudio status
pactl info

# List audio sinks
pactl list short sinks

# Check Bluetooth connection
bluetoothctl devices
bluetoothctl info AA:BB:CC:DD:EE:FF

# Restart PulseAudio
pulseaudio -k
pulseaudio --start
```

**Known Issue**: Pi Zero 2W has Bluetooth/WiFi coexistence issues.
**Solution**: Reduce WiFi activity or use USB Bluetooth dongle.

### Out of Memory errors

```bash
# Check memory usage
free -h

# Monitor during operation
htop

# Check swap
sudo swapon --show

# Create/increase swap if needed
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile  # Set CONF_SWAPSIZE=512
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Face recognition not working

1. Verify dlib is installed: `python3 -c "import face_recognition; print('OK')"`
2. Check faces directory exists: `ls -la faces/`
3. Enroll at least one person: `python3 enroll_face.py "Name"`
4. Ensure good image quality (clear face, good lighting)
5. **No internet required** - works completely offline

### API timeout errors

1. Check internet connection: `ping 8.8.8.8`
2. Increase timeout in config.py: `REQUEST_TIMEOUT = 60`
3. Check API status:
   - HuggingFace: https://status.huggingface.co
   - Face++: https://www.faceplusplus.com

### Import errors after installation

If you see "ModuleNotFoundError" for opencv/numpy:

```bash
# Verify apt packages are installed
dpkg -l | grep python3-opencv
dpkg -l | grep python3-numpy

# Check venv has system-site-packages
source venv/bin/activate
python3 -c "import sys; print('system-site-packages' in sys.path)"
# Should print True
```

## Hardware Requirements

- **Raspberry Pi Zero 2W** (512MB RAM)
- Raspberry Pi Camera Module (v2 or HQ recommended)
- **2x Tactile push-button switches** (momentary contact)
- Bluetooth speaker/headphones OR USB audio output
- MicroSD card (16GB+ recommended, Class 10)
- Power supply (2.5A recommended for stability)

## System Requirements

- Raspbian Buster / Legacy (or newer)
- Internet connection (required for AI analysis)
- ~500MB free disk space after installation

## Installation as System Service (Optional)

To run automatically on boot:

```bash
sudo cp smart-vision.service /etc/systemd/system/
sudo systemctl enable smart-vision
sudo systemctl start smart-vision

# Check status
sudo systemctl status smart-vision

# View logs
sudo journalctl -u smart-vision -f
```

## Memory Optimization Tips

1. **Use espeak** instead of gTTS for offline TTS (saves bandwidth and time)
2. **Close other applications** when running
3. **Monitor temperature**: `vcgencmd measure_temp` (should stay < 70°C)
4. **Reduce camera resolution** if needed (edit `config.py`)
5. **Enable swap** if experiencing OOM crashes

## Known Limitations

1. **Internet Required for AI modes**: Describe, OCR, Search require active internet (Face mode works offline)
2. **Bluetooth Issues**: Pi Zero 2W has known WiFi/BT interference
3. **Processing Speed**: Slower than Pi 4 due to limited CPU/RAM
4. **Single Operation**:Only one analysis at a time (enforced by application)
5. **Face Recognition**: Accuracy depends on enrollment photo quality and lighting conditions

## License

MIT License - See LICENSE file for details.

## Acknowledgments

- Hugging Face for the Inference API and Molmo2 model
- Face++ for the face recognition API  
- The Raspberry Pi Foundation
- The assistive technology community

## Support

For issues specific to Pi Zero 2W optimization, check:
1. Logs: `sudo journalctl -u smart-vision -f`
2. Memory: `free -h` and `htop`
3. Temperature: `vcgencmd measure_temp`
4. Camera: `vcgencmd get_camera`

---

**Optimized for Pi Zero 2W** - v2.0
