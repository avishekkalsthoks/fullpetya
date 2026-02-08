# Smart Vision Guide (Pi Zero 2W)

An assistive vision device optimized for Raspberry Pi Zero 2W (512MB RAM) with **online + offline** vision modes, a simple 2-button interface, and Bluetooth audio support.

## Highlights

- Works **offline** for all modes using lightweight local models
- Uses **OpenRouter API** (nvidia/nemotron model) for detailed scene description
- Uses **Azure Computer Vision** for OCR and Object Search
- Stronger face detection via OpenCV DNN + local LBPH recognition
- Offline OCR using Tesseract
- Search mode voice input with offline STT (Vosk)
- **Ultrasonic obstacle detection** with buzzer alerts
- Pi Zero 2W tuned: reduced image size, low memory defaults

## Modes (Online + Offline)

| Mode | Online | Offline Fallback |
|------|--------|------------------|
| Describe | Full scene description (OpenRouter AI) | Object summary + positions + distance hints |
| OCR | Azure Vision OCR | Tesseract OCR |
| Face | Cloud API (deep learning) | *Cloud only - lightweight for Pi* |
| Search | AI object search | MobileNet-SSD object detection |

Set `LOCAL_VISION_ONLY=true` in `.env` to **force offline-only** mode.

---

## How Online vs Offline Works

By default, the system **tries online first** and falls back to offline if online fails.

- It does **not** specifically check Wi-Fi first.
- If the online API returns an error or times out, it immediately falls back to offline.
- If you want **offline-only**, set:
  ```
  LOCAL_VISION_ONLY=true
  ```

---

## Hardware Requirements

- Raspberry Pi Zero 2W (512MB RAM)
- Raspberry Pi Camera Module (v2 or HQ recommended)
- 2 tactile push buttons (GPIO 17 + 27)
- Bluetooth headset/speaker (mic recommended for Search)
- MicroSD card (16GB+)
- **HC-SR04 Ultrasonic Sensor** (optional, for obstacle detection)
- **Buzzer** (optional, for obstacle alerts)

---

## Quick Start (Pi Zero 2W)

### 1) Install system dependencies (Buster 10 safe)
```bash
sudo bash setup_system.sh
```

This script:
- Uses **apt** for heavy packages (OpenCV, Tesseract, audio)
- Uses **piwheels** for pip to avoid compilation on 512MB RAM

### 2) Download local models (offline support)
```bash
bash scripts/download_models.sh
```

### 3) Configure environment
```bash
cp .env.example .env
nano .env
```

Set at least:
```
AZURE_VISION_ENDPOINT=https://your-resource.cognitiveservices.azure.com
AZURE_VISION_KEY=your_key_here

# For Scene Description (OpenRouter):
OPENROUTER_API_KEY=your_openrouter_key_here
```
Optional for offline-only:
```
LOCAL_VISION_ONLY=true
```

### 4) Enroll faces (offline)
```bash
source venv/bin/activate
python3 enroll_face.py "Alice"
```

### 5) Run the app
```bash
source venv/bin/activate
python3 main.py
```

---

## Search Mode Behavior

Search mode is optimized for visually impaired users. When used without a specific query, it automatically scans for **VI-priority items** - common items that blind users frequently need to locate.

### VI-Priority Items

Items are categorized by importance:

| Priority | Items |
|----------|-------|
| **High** | doors, stairs, curbs, phone, wallet, keys, glasses, cane, medication, people, pets |
| **Medium** | remote, charger, cup, bottle, plate, chair, table, bed, sofa |
| **Low** | laptop, bag, umbrella, book, watch, tv |

### Output Format

Detected items are grouped by position with distance estimates:

```
"In front of you: chair, close about 2 arm lengths. To your left: bottle, very close about 1 arm length."
```

Distance estimates use arm lengths for intuitive understanding:
- **Very close**: ~1 arm length (2-3 feet)
- **Close**: ~2 arm lengths (4-6 feet)  
- **Farther**: 3+ arm lengths (7+ feet)

### Configuration

The default behavior is controlled by:
```
SEARCH_DEFAULT_QUERY=auto
```

You can set a specific default item instead:
```
SEARCH_DEFAULT_QUERY=bottle
```

---

## Search Mode Voice Input (Microphone)

Search mode uses **offline speech-to-text (Vosk)** by default.

Important:
- Your Bluetooth headset must support **HSP/HFP** (microphone profile)
- If your headset is output-only, use a **USB microphone**

The app switches Bluetooth profile automatically between music and chat modes.

---

## Offline Model Notes (Pi Zero 2W Friendly)

These models are chosen to be lightweight and Pi-safe:

- **MobileNet-SSD** (object detection, offline search/describe)
- **Res10 SSD** (face detection)
- **LBPH** (face recognition)
- **Tesseract** (OCR)
- **Vosk small** (speech-to-text)

Tesseract **is Pi-friendly** on 512MB RAM, but slower than online OCR.
Keeping the image resolution at 512x384 makes OCR much faster and safer.

---

## Buster 10 + 512MB Install Tips (Important)

On Pi Zero 2W, pip builds can fail due to low RAM. Use piwheels:
```bash
pip install --no-cache-dir --prefer-binary --index-url https://www.piwheels.org/simple -r requirements.txt
```

If Vosk fails to install (common on Python 3.7), disable speech input:
```bash
STT_BACKEND=none
```

OCR still works offline if:
```bash
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng
```

---

## Auto-Start on Boot

Use the included systemd service file:

```bash
sudo cp smart-vision.service /etc/systemd/system/
sudo systemctl enable smart-vision
sudo systemctl start smart-vision
```

Important: edit `smart-vision.service` to match your installation path.
Default path assumes:
```
/home/pi/smart-vision-guide
```

---

## Auto-Connect Wi-Fi and Bluetooth

### Wi-Fi
Wi-Fi auto-connect is handled by the OS. Use:
```bash
sudo raspi-config
```
Then set your network in the OS network settings.

### Bluetooth
Pair + trust your headset once:
```bash
bluetoothctl
scan on
pair AA:BB:CC:DD:EE:FF
trust AA:BB:CC:DD:EE:FF
connect AA:BB:CC:DD:EE:FF
```

Optional auto-connect script:
```bash
BT_DEVICE_MAC=AA:BB:CC:DD:EE:FF bash scripts/bt_autoconnect.sh
```

The systemd service can run this automatically on boot.

---

## Face Recognition (Cloud Only)

Face recognition uses a **cloud API** hosted on GitHub Codespaces. This keeps the Raspberry Pi lightweight - it just captures and sends images to the cloud for processing.

### Setup

1. Create a GitHub Codespaces with the face recognition API
2. Make port 5000 **PUBLIC** in the Codespaces settings
3. Add to your `.env`:
   ```
   FACE_API_URL=https://your-codespace-name-5000.app.github.dev
   ```

### How It Works

- Pi captures image → Sends to cloud API
- Cloud uses deep learning models to analyze faces
- Results include name and confidence
- Very lightweight on the Pi (no local processing)

### Registering Faces (from Pi)

Use the included enrollment script to register faces directly from your Pi camera:

```bash
# Activate environment
source venv/bin/activate

# Quick registration (1 photo)
python3 enroll_face_online.py "Alice"

# Training mode (5 photos - recommended)
python3 enroll_face_online.py "Alice" --train
```

### Best Practices for Accuracy

- **Capture 5-10 images** per person with different angles
- **Vary lighting**: bright, normal, dim
- **Face angles**: front, left profile, right profile
- **Face should fill 40-60%** of the frame

---

## Tuning and Tips

- For clearer speech, use:
  - `TTS_BACKEND=auto` (pico2wave -> espeak-ng -> espeak)
  - Adjust `TTS_RATE` and `TTS_VOICE`
- If you want offline only, set:
  - `LOCAL_VISION_ONLY=true`
- If Search speech input is unreliable:
  - Use a USB mic or ensure HSP/HFP profile is supported

---

## Image Quality vs Speed (Important)

By default, the app **preprocesses images** before sending to the online API:
- Downscales to reduce payload
- Recompresses to reduce upload time

If you want **maximum image quality** (higher resolution, no preprocessing), set:
```
ENABLE_PREPROCESSING=false
CAMERA_WIDTH=640
CAMERA_HEIGHT=480
CAMERA_JPEG_QUALITY=85
```

Note: higher resolution and quality **increase upload size and RAM usage**, which can slow responses on Pi Zero 2W. You can experiment to find your best balance.

---

## Capture Storage (Optional)

To save every captured image to disk:
```
SAVE_CAPTURES=true
CAPTURE_DIR=captures
CAPTURE_MAX_FILES=200
```

Files are saved as `YYYYMMDD_HHMMSS_mode.jpg`.

---

## Troubleshooting

**No offline objects detected**
- Ensure models downloaded: `bash scripts/download_models.sh`

**OCR not working**
- Confirm Tesseract installed: `tesseract --version`
 - If OCR times out on blurry images, move closer or improve lighting and retry

**Search mode hears nothing**
- Ensure microphone is available: `arecord -l`
- Try a USB mic or headset with HSP/HFP

**Face recognition poor**
- Enroll 3-5 photos in good lighting
- Ensure faces are centered and clear

**Ultrasonic sensor not working**
- Check wiring: TRIG -> GPIO 23, ECHO -> GPIO 24 (with voltage divider!)
- Ensure buzzer is connected to GPIO 25
- Test with `python3 -c "from handlers.ultrasonic_handler import UltrasonicHandler; u = UltrasonicHandler(23,24,25); print(u.measure_distance())"`

---

## Ultrasonic Obstacle Detection

The device can detect nearby obstacles using an **HC-SR04 ultrasonic sensor** and alert the user with a **buzzer**.

### Wiring Diagram

```
HC-SR04 Ultrasonic Sensor:
  VCC  -> Pi 5V
  GND  -> Pi GND
  TRIG -> GPIO 23
  ECHO -> GPIO 24 (⚠️ Use voltage divider! See below)

Buzzer:
  Positive (+) -> GPIO 25
  Negative (-) -> Pi GND
```

**Important:** The HC-SR04 ECHO pin outputs 5V, but Pi GPIO is 3.3V tolerant only!
Use a simple voltage divider:
```
ECHO pin ----[1kΩ]----+----[2kΩ]---- GND
                      |
                GPIO 24
```

### Configuration

In your `.env` file:
```bash
# Enable ultrasonic obstacle detection
ENABLE_ULTRASONIC=true

# Pins (BCM numbering)
ULTRASONIC_TRIGGER_PIN=23
ULTRASONIC_ECHO_PIN=24
BUZZER_PIN=25

# Distance thresholds (cm)
ULTRASONIC_ALERT_DISTANCE=50   # Start beeping at 50cm
ULTRASONIC_DANGER_DISTANCE=20  # Rapid beeping at 20cm

# Check interval
ULTRASONIC_CHECK_INTERVAL=0.2  # Check every 200ms
```

### How It Works

- **No beep**: Object is more than 50cm away (safe zone)
- **Slow beep**: Object is 25-50cm away (alert zone)
- **Fast beep**: Object is 20-25cm away (close)
- **Rapid beep**: Object is less than 20cm away (danger zone)

To disable ultrasonic detection:
```
ENABLE_ULTRASONIC=false
```

---

## License

MIT License
