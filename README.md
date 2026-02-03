# Smart Vision Guide (Pi Zero 2W)

An assistive vision device optimized for Raspberry Pi Zero 2W (512MB RAM) with **online + offline** vision modes, a simple 2-button interface, and Bluetooth audio support.

## Highlights

- Works **offline** for all modes using lightweight local models
- Uses **OpenRouter** online AI for higher quality when internet is available
- Stronger face detection via OpenCV DNN + local LBPH recognition
- Offline OCR using Tesseract
- Search mode voice input with offline STT (Vosk)
- Pi Zero 2W tuned: reduced image size, low memory defaults

## Modes (Online + Offline)

| Mode | Online (OpenRouter) | Offline Fallback |
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
OPENROUTER_API_KEY=your_key_here
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

If Vosk fails to install, disable speech input:
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

## Troubleshooting

**No offline objects detected**
- Ensure models downloaded: `bash scripts/download_models.sh`

**OCR not working**
- Confirm Tesseract installed: `tesseract --version`

**Search mode hears nothing**
- Ensure microphone is available: `arecord -l`
- Try a USB mic or headset with HSP/HFP

**Face recognition poor**
- Enroll 3-5 photos in good lighting
- Ensure faces are centered and clear

---

## License

MIT License
