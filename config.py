import os
from dotenv import load_dotenv

load_dotenv()

# ===============================================
# API Configuration (Online AI)
# ===============================================

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '').strip()
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'allenai/molmo-2-8b:free')
OPENROUTER_API_URL = os.getenv('OPENROUTER_API_URL', 'https://openrouter.ai/api/v1/chat/completions')

# Optional: Site URL and name for rankings on openrouter.ai
OPENROUTER_SITE_URL = os.getenv('OPENROUTER_SITE_URL', '').strip()
OPENROUTER_SITE_NAME = os.getenv('OPENROUTER_SITE_NAME', 'Smart Vision Guide').strip()

# ===============================================
# Local / Offline Vision Configuration
# ===============================================

LOCAL_VISION_ONLY = os.getenv('LOCAL_VISION_ONLY', 'false').lower() == 'true'
LOCAL_MODEL_DIR = os.getenv('LOCAL_MODEL_DIR', 'models')

# Object detector (MobileNet-SSD, Caffe)
OBJECT_DNN_PROTO = os.getenv(
    'OBJECT_DNN_PROTO',
    os.path.join(LOCAL_MODEL_DIR, 'mobilenet_ssd_deploy.prototxt')
)
OBJECT_DNN_MODEL = os.getenv(
    'OBJECT_DNN_MODEL',
    os.path.join(LOCAL_MODEL_DIR, 'mobilenet_ssd.caffemodel')
)
OBJECT_DNN_CONFIDENCE = float(os.getenv('OBJECT_DNN_CONFIDENCE', '0.45'))

# Offline OCR (Tesseract)
TESSERACT_CMD = os.getenv('TESSERACT_CMD', '').strip()
OCR_TIMEOUT = int(os.getenv('OCR_TIMEOUT', '8'))

# ===============================================
# Face Recognition Configuration
# ===============================================

FACE_DB_DIR = os.getenv('FACE_DB_DIR', 'faces')
FACE_CONFIDENCE_THRESHOLD = int(os.getenv('FACE_CONFIDENCE_THRESHOLD', '80'))

# Face detector (DNN preferred)
FACE_DNN_PROTO = os.getenv(
    'FACE_DNN_PROTO',
    os.path.join(LOCAL_MODEL_DIR, 'face_detector_deploy.prototxt')
)
FACE_DNN_MODEL = os.getenv(
    'FACE_DNN_MODEL',
    os.path.join(LOCAL_MODEL_DIR, 'face_detector.caffemodel')
)
FACE_DNN_CONFIDENCE = float(os.getenv('FACE_DNN_CONFIDENCE', '0.5'))

# ===============================================
# Performance Tuning for Pi Zero 2W
# ===============================================

REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '45'))  # seconds
RETRY_ATTEMPTS = int(os.getenv('RETRY_ATTEMPTS', '2'))
RETRY_DELAY = float(os.getenv('RETRY_DELAY', '2.0'))

IMAGE_MAX_WIDTH = int(os.getenv('IMAGE_MAX_WIDTH', '512'))
IMAGE_JPEG_QUALITY = int(os.getenv('IMAGE_JPEG_QUALITY', '60'))
ENABLE_PREPROCESSING = os.getenv('ENABLE_PREPROCESSING', 'true').lower() == 'true'

ANALYSIS_TIMEOUT = int(os.getenv('ANALYSIS_TIMEOUT', '60'))

# ===============================================
# Button Configuration (BCM pin numbers)
# ===============================================

BUTTON_MODE_PIN = int(os.getenv('BUTTON_MODE_PIN', '17'))
BUTTON_SELECT_PIN = int(os.getenv('BUTTON_SELECT_PIN', '27'))

# ===============================================
# Ultrasonic Sensor + Buzzer Configuration
# ===============================================

# HC-SR04 Ultrasonic Sensor pins
ULTRASONIC_TRIGGER_PIN = int(os.getenv('ULTRASONIC_TRIGGER_PIN', '23'))
ULTRASONIC_ECHO_PIN = int(os.getenv('ULTRASONIC_ECHO_PIN', '24'))

# Buzzer pin
BUZZER_PIN = int(os.getenv('BUZZER_PIN', '25'))

# Enable/disable ultrasonic obstacle detection
ENABLE_ULTRASONIC = os.getenv('ENABLE_ULTRASONIC', 'true').lower() == 'true'

# Distance thresholds in centimeters
ULTRASONIC_ALERT_DISTANCE = float(os.getenv('ULTRASONIC_ALERT_DISTANCE', '50'))  # Start warning at 50cm
ULTRASONIC_DANGER_DISTANCE = float(os.getenv('ULTRASONIC_DANGER_DISTANCE', '20'))  # Danger zone at 20cm

# Buzzer settings
BUZZER_FREQUENCY = int(os.getenv('BUZZER_FREQUENCY', '2000'))  # Hz (for PWM buzzer)
ULTRASONIC_CHECK_INTERVAL = float(os.getenv('ULTRASONIC_CHECK_INTERVAL', '0.2'))  # Check every 200ms

# ===============================================
# Camera Settings (optimized for Pi Camera)
# ===============================================

CAMERA_WIDTH = int(os.getenv('CAMERA_WIDTH', '512'))
CAMERA_HEIGHT = int(os.getenv('CAMERA_HEIGHT', '384'))
CAMERA_WARMUP_FRAMES = int(os.getenv('CAMERA_WARMUP_FRAMES', '10'))
CAMERA_RETRY_ATTEMPTS = int(os.getenv('CAMERA_RETRY_ATTEMPTS', '3'))
CAMERA_JPEG_QUALITY = int(os.getenv('CAMERA_JPEG_QUALITY', '70'))

# ===============================================
# Capture Storage (Optional)
# ===============================================

SAVE_CAPTURES = os.getenv('SAVE_CAPTURES', 'false').lower() == 'true'
CAPTURE_DIR = os.getenv('CAPTURE_DIR', 'captures')
CAPTURE_MAX_FILES = int(os.getenv('CAPTURE_MAX_FILES', '200'))

# ===============================================
# Audio/TTS Settings
# ===============================================

TTS_BACKEND = os.getenv('TTS_BACKEND', 'auto')
TTS_RATE = int(os.getenv('TTS_RATE', '120'))
TTS_VOICE = os.getenv('TTS_VOICE', 'en-us+f3')
USE_BLUETOOTH_AUDIO = os.getenv('USE_BLUETOOTH_AUDIO', 'true').lower() == 'true'

# ===============================================
# Speech-to-Text Settings (Search Mode)
# ===============================================

STT_BACKEND = os.getenv('STT_BACKEND', 'auto')  # 'vosk', 'auto', or 'none'
VOSK_MODEL_PATH = os.getenv('VOSK_MODEL_PATH', os.path.join(LOCAL_MODEL_DIR, 'vosk-model-small-en-us-0.15'))
VOICE_INPUT_SECONDS = float(os.getenv('VOICE_INPUT_SECONDS', '4'))
VOICE_INPUT_SAMPLE_RATE = int(os.getenv('VOICE_INPUT_SAMPLE_RATE', '16000'))
SEARCH_DEFAULT_QUERY = os.getenv('SEARCH_DEFAULT_QUERY', 'auto')

# ===============================================
# Search Mode Configuration (Common objects)
# ===============================================

SEARCH_OBJECTS = [
    # Frequently needed items (broad, online-capable list)
    "phone", "wallet", "keys", "glasses", "watch",
    "bottle", "cup", "plate",
    "bag", "backpack", "umbrella",
    "book", "remote", "laptop", "charger",
    "chair", "table", "sofa", "tv",
    "door", "window"
]

# ===============================================
# System Optimization
# ===============================================

ENABLE_GARBAGE_COLLECTION = os.getenv('ENABLE_GARBAGE_COLLECTION', 'true').lower() == 'true'
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
VERBOSE_LOGGING = os.getenv('VERBOSE_LOGGING', 'false').lower() == 'true'

# ===============================================
# Feature Flags
# ===============================================

ENABLE_DESCRIBE_MODE = os.getenv('ENABLE_DESCRIBE_MODE', 'true').lower() == 'true'
ENABLE_OCR_MODE = os.getenv('ENABLE_OCR_MODE', 'true').lower() == 'true'
ENABLE_FACE_MODE = os.getenv('ENABLE_FACE_MODE', 'true').lower() == 'true'
ENABLE_SEARCH_MODE = os.getenv('ENABLE_SEARCH_MODE', 'true').lower() == 'true'


def get_system_info():
    """Get system information for debugging."""
    return {
        'openrouter_configured': bool(OPENROUTER_API_KEY),
        'openrouter_model': OPENROUTER_MODEL,
        'local_vision_only': LOCAL_VISION_ONLY,
        'local_model_dir': LOCAL_MODEL_DIR,
        'tts_backend': TTS_BACKEND,
        'stt_backend': STT_BACKEND
    }


if __name__ == '__main__':
    print("=" * 50)
    print("Smart Vision Guide - Configuration")
    print("=" * 50)
    info = get_system_info()
    print(f"\n🔧 API Configuration:")
    print(f"  OpenRouter: {'✓ Configured' if info['openrouter_configured'] else '✗ Not configured'}")
    print(f"  Model:      {info['openrouter_model']}")
    print(f"\n🧠 Local Vision:")
    print(f"  Offline Only: {info['local_vision_only']}")
    print(f"  Model Dir:    {info['local_model_dir']}")
    print(f"\n🎤 Speech:")
    print(f"  STT Backend:  {info['stt_backend']}")
    print(f"\n🔊 Audio:")
    print(f"  TTS Backend:  {info['tts_backend']}")
    print(f"\n📷 Camera:")
    print(f"  Resolution:   {CAMERA_WIDTH}x{CAMERA_HEIGHT}")
    print(f"  Warmup:       {CAMERA_WARMUP_FRAMES} frames")
    print(f"\n🌐 Network:")
    print(f"  Timeout:      {REQUEST_TIMEOUT}s")
    print(f"  Retries:      {RETRY_ATTEMPTS}")
    print(f"\n🎮 Button Configuration:")
    print(f"  Mode Toggle:  GPIO {BUTTON_MODE_PIN}")
    print(f"  Select:       GPIO {BUTTON_SELECT_PIN}")
    print(f"\n🎯 Enabled Modes:")
    print(f"  Describe:     {'✓' if ENABLE_DESCRIBE_MODE else '✗'}")
    print(f"  OCR:          {'✓' if ENABLE_OCR_MODE else '✗'}")
    print(f"  Face:         {'✓' if ENABLE_FACE_MODE else '✗'}")
    print(f"  Search:       {'✓' if ENABLE_SEARCH_MODE else '✗'}")
    print("\n" + "=" * 50)
    print(f"  JPEG Quality: {IMAGE_JPEG_QUALITY}%")
