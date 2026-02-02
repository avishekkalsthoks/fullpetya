import os
from dotenv import load_dotenv

load_dotenv()

# ===============================================
# API Configuration
# ===============================================

# OpenRouter Configuration (for Describe, OCR, and Search modes)
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '').strip()
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'allenai/molmo-2-8b:free')
import os
from dotenv import load_dotenv

load_dotenv()

# ===============================================
# API Configuration
# ===============================================

# OpenRouter Configuration (for Describe, OCR, and Search modes)
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '').strip()
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'allenai/molmo-2-8b:free')
OPENROUTER_API_URL = os.getenv('OPENROUTER_API_URL', 'https://openrouter.ai/api/v1/chat/completions')

# Optional: Site URL and name for rankings on openrouter.ai
OPENROUTER_SITE_URL = os.getenv('OPENROUTER_SITE_URL', '').strip()
OPENROUTER_SITE_NAME = os.getenv('OPENROUTER_SITE_NAME', 'Smart Vision Guide').strip()

# ===============================================
# Local Face Recognition Configuration
# ===============================================

# Face database directory (folder per person, multiple images per person)
FACE_DB_DIR = os.getenv('FACE_DB_DIR', 'faces')

# Face recognition distance threshold (0.5-0.6 recommended, lower = stricter)
FACE_DISTANCE_THRESHOLD = float(os.getenv('FACE_DISTANCE_THRESHOLD', '0.6'))

# ===============================================
# Performance Tuning for Pi Zero 2W
# ===============================================

# Network Settings (optimized for slow connections)
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '45'))  # seconds
RETRY_ATTEMPTS = int(os.getenv('RETRY_ATTEMPTS', '2'))
RETRY_DELAY = float(os.getenv('RETRY_DELAY', '2.0'))

# Image Processing (reduced for faster processing and smaller payloads)
IMAGE_MAX_WIDTH = int(os.getenv('IMAGE_MAX_WIDTH', '512'))
IMAGE_JPEG_QUALITY = int(os.getenv('IMAGE_JPEG_QUALITY', '60'))

# Analysis Timeout (watchdog timer)
ANALYSIS_TIMEOUT = int(os.getenv('ANALYSIS_TIMEOUT', '60'))

# ===============================================
# Button Configuration (BCM pin numbers)
# ===============================================

BUTTON_MODE_PIN = int(os.getenv('BUTTON_MODE_PIN', '17'))
BUTTON_SELECT_PIN = int(os.getenv('BUTTON_SELECT_PIN', '27'))

# ===============================================
# Camera Settings (optimized for Pi Camera)
# ===============================================

CAMERA_WIDTH = int(os.getenv('CAMERA_WIDTH', '512'))
CAMERA_HEIGHT = int(os.getenv('CAMERA_HEIGHT', '384'))
CAMERA_WARMUP_FRAMES = int(os.getenv('CAMERA_WARMUP_FRAMES', '10'))
CAMERA_RETRY_ATTEMPTS = int(os.getenv('CAMERA_RETRY_ATTEMPTS', '3'))

# ===============================================
# Audio/TTS Settings
# ===============================================

# TTS options: espeak (offline, recommended) or gtts (online)
TTS_BACKEND = os.getenv('TTS_BACKEND', 'espeak')
USE_BLUETOOTH_AUDIO = os.getenv('USE_BLUETOOTH_AUDIO', 'true').lower() == 'true'

# Note: This project uses local offline face recognition via `face_recognition` (dlib).
# Remove any cloud Face++ integrations to keep the codebase minimal for offline use.

# ===============================================
# Search Mode Configuration
# ===============================================

SEARCH_OBJECTS = [
    "person", "people", "man", "woman", "child", "baby",
    "chair", "table", "bed", "couch", "sofa",
    "door", "window", "stairs", "elevator",
    "car", "bus", "bicycle", "motorcycle",
    "dog", "cat", "bird", "animal",
    "phone", "laptop", "tv", "remote",
    "book", "bottle", "cup", "plate",
    "bag", "backpack", "umbrella",
    "glasses", "keys", "wallet"
]

# ===============================================
# System Optimization (Pi Zero 2W specific)
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

# ===============================================
# System Information
# ===============================================

def get_system_info():
    """Get system information for debugging."""
    return {
        'openrouter_configured': bool(OPENROUTER_API_KEY),
        'openrouter_model': OPENROUTER_MODEL,
        'face_recognition': 'Local (dlib)'
    }


if __name__ == '__main__':
    print("=" * 50)
    print("Smart Vision Guide - Configuration")
    print("=" * 50)
    info = get_system_info()
    print(f"\n🔧 API Configuration:")
    print(f"  OpenRouter: {'✓ Configured' if info['openrouter_configured'] else '✗ Not configured'}")
    print(f"  Model:      {info['openrouter_model']}")
    print(f"  Face Recognition: {info['face_recognition']}")
    print(f"\n📷 Camera Settings:")
    print(f"  Resolution:   {CAMERA_WIDTH}x{CAMERA_HEIGHT}")
    print(f"  Warmup:       {CAMERA_WARMUP_FRAMES} frames")
    print(f"\n🌐 Network:")
    print(f"  Timeout:      {REQUEST_TIMEOUT}s")
    print(f"  Retries:      {RETRY_ATTEMPTS}")
    print(f"\n🔊 Audio:")
    print(f"  TTS Backend:  {TTS_BACKEND}")
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
