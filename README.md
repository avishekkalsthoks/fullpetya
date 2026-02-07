# Smart Vision Guide (Pi Zero 2W)

An assistive vision device optimized for Raspberry Pi Zero 2W (512MB RAM) with **online + offline** vision modes, a simple 2-button interface, and Bluetooth audio support.

## Highlights

- Works **offline** for all modes using lightweight local models
- Uses **Azure Computer Vision** online analysis for higher quality when internet is available
- Stronger face detection via OpenCV DNN + local LBPH recognition
- Offline OCR using Tesseract
- Search mode voice input with offline STT (Vosk)
- **Ultrasonic obstacle detection** with buzzer alerts
- Pi Zero 2W tuned: reduced image size, low memory defaults

## Modes (Online + Offline)

| Mode | Online (Azure Vision) | Offline Fallback |
|------|----------------------|------------------|
| Describe | Full scene description | Object summary + positions + distance hints |
| OCR | Vision OCR | Tesseract OCR |
| Face | Local LBPH | Local LBPH (always offline) |
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

If speech input is not available, Search mode will **scan for common items** and tell you where one is found.
The default behavior is controlled by:
```
SEARCH_DEFAULT_QUERY=auto
```

You can set a specific default item instead:
```
SEARCH_DEFAULT_QUERY=bottle
```

Common items list (online): phone, wallet, keys, glasses, bottle, bag, backpack, book, remote, laptop, chair, table, sofa, tv.

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

## Face Enrollment

```bash
source venv/bin/activate
python3 enroll_face.py "Alice" --photos 5
```

Faces are stored in:
```
faces/<name>/img1.jpg
faces/<name>/img2.jpg
```

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
