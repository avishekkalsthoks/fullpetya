import os
from dotenv import load_dotenv

load_dotenv()

# ===============================================
# API Configuration (Online AI)
# ===============================================

AZURE_VISION_ENDPOINT = os.getenv('AZURE_VISION_ENDPOINT', '').strip()
AZURE_VISION_KEY = os.getenv('AZURE_VISION_KEY', '').strip()

# Azure AI Foundry Configuration (for scene description)
# Endpoint format: https://<resource-name>.services.ai.azure.com
AZURE_FOUNDRY_ENDPOINT = os.getenv('AZURE_FOUNDRY_ENDPOINT', '').strip()
AZURE_FOUNDRY_KEY = os.getenv('AZURE_FOUNDRY_KEY', '').strip()
AZURE_FOUNDRY_MODEL = os.getenv('AZURE_FOUNDRY_MODEL', 'gpt-4o').strip()

# OpenRouter API Configuration (for scene description)
# Get your API key from https://openrouter.ai/keys
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '').strip()
OPENROUTER_MODEL = 'nvidia/nemotron-nano-12b-v2-vl:free'
OPENROUTER_API_URL = 'https://openrouter.ai/api/v1/chat/completions'

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
# Face Recognition Configuration (Cloud Only)
# ===============================================

# Local face database directory (for enrollment)
FACE_DB_DIR = os.getenv('FACE_DB_DIR', 'faces')
FACE_CONFIDENCE_THRESHOLD = int(os.getenv('FACE_CONFIDENCE_THRESHOLD', '80'))

# Cloud Face Recognition API
# Set this to your cloud API endpoint (e.g., GitHub Codespaces URL)
# Face processing happens in the cloud - lightweight for Pi Zero 2W
FACE_API_URL = os.getenv('FACE_API_URL', '').strip()
FACE_API_TIMEOUT = int(os.getenv('FACE_API_TIMEOUT', '15'))

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
# VI-Priority Items (for Visually Impaired Users)
# ===============================================
# These items are automatically scanned and reported with position/distance
# when Search mode is used without a specific query

VI_PRIORITY_ITEMS = {
    # HIGH: Safety-critical and essential personal items
    "high": [
        # Navigation/Safety hazards
        "door", "stairs", "staircase", "steps", "step", "curb", "edge",
        "pole", "post", "obstacle", "wall", "window", "glass",
        # Personal essentials
        "phone", "cell phone", "mobile phone", "wallet", "keys", "key",
        "glasses", "eyeglasses", "sunglasses", "cane", "walking stick",
        "medication", "medicine", "pill bottle",
        # People and pets (for social awareness)
        "person", "people", "man", "woman", "child", "dog", "cat"
    ],
    # MEDIUM: Common household items needed frequently
    "medium": [
        "remote", "remote control", "charger", "cable", "cord",
        "cup", "mug", "glass", "bottle", "water bottle",
        "plate", "bowl", "spoon", "fork", "knife",
        "chair", "table", "desk", "bed", "sofa", "couch", "bench"
    ],
    # LOW: Less urgent but still useful
    "low": [
        "laptop", "computer", "keyboard", "mouse",
        "bag", "backpack", "purse", "handbag",
        "umbrella", "book", "pen", "pencil",
        "watch", "clock", "tv", "television"
    ]
}

# Flattened set for quick lookup
VI_PRIORITY_ALL = set()
for items in VI_PRIORITY_ITEMS.values():
    VI_PRIORITY_ALL.update(item.lower() for item in items)

# ===============================================
# GPS Navigation + Help Configuration
# ===============================================

# Enable GPS-based modes (Navigation and Help)
ENABLE_GPS_MODES = os.getenv('ENABLE_GPS_MODES', 'true').lower() == 'true'

# Phyphox app GPS endpoint (phone connected via WiFi hotspot)
# Format: http://<phone-ip>:8080/get?lat&lon&v
PHYPHOX_URL = os.getenv('PHYPHOX_URL', 'http://192.168.1.108:8080/get?lat&lon&v').strip()

# Home coordinates (destination for navigation)
HOME_LAT = float(os.getenv('HOME_LAT', '27.688441946480275'))
HOME_LON = float(os.getenv('HOME_LON', '85.33542229999999'))

# ntfy.sh configuration for Help mode
# Relatives install ntfy app and subscribe to this topic to receive alerts
NTFY_TOPIC = os.getenv('NTFY_TOPIC', 'smart-vision-help-2026').strip()

# Relatives list (comma-separated names for notification messages)
RELATIVES_STR = os.getenv('RELATIVES', 'Family Member 1,Family Member 2').strip()
RELATIVES = [name.strip() for name in RELATIVES_STR.split(',') if name.strip()]

# GPS check interval during navigation (seconds)
GPS_CHECK_INTERVAL = float(os.getenv('GPS_CHECK_INTERVAL', '2.0'))

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
ENABLE_NAVIGATION_MODE = os.getenv('ENABLE_NAVIGATION_MODE', 'true').lower() == 'true'
ENABLE_HELP_MODE = os.getenv('ENABLE_HELP_MODE', 'true').lower() == 'true'


def get_system_info():
    """Get system information for debugging."""
    return {
        'azure_vision_configured': bool(AZURE_VISION_ENDPOINT and AZURE_VISION_KEY),
        'azure_foundry_configured': bool(AZURE_FOUNDRY_ENDPOINT and AZURE_FOUNDRY_KEY),
        'openrouter_configured': bool(OPENROUTER_API_KEY),
        'gps_configured': bool(PHYPHOX_URL and ENABLE_GPS_MODES),
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
    print(f"  OpenRouter (Describe):   {'✓ Configured' if info['openrouter_configured'] else '✗ Not configured'}")
    print(f"  Azure Vision (OCR/Search): {'✓ Configured' if info['azure_vision_configured'] else '✗ Not configured'}")
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
    print(f"  Navigation:   {'✓' if ENABLE_NAVIGATION_MODE else '✗'}")
    print(f"  Help:         {'✓' if ENABLE_HELP_MODE else '✗'}")
    print(f"\n📍 GPS Configuration:")
    print(f"  Phyphox URL:  {PHYPHOX_URL}")
    print(f"  Home:         {HOME_LAT}, {HOME_LON}")
    print(f"  ntfy Topic:   {NTFY_TOPIC}")
    print(f"  Relatives:    {', '.join(RELATIVES)}")
    print("\n" + "=" * 50)
    print(f"  JPEG Quality: {IMAGE_JPEG_QUALITY}%")

