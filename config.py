import os
from dotenv import load_dotenv

load_dotenv()

# ===============================================
# API Configuration
# ===============================================

# OpenRouter Configuration (for Describe, OCR, and Search modes)
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '').strip()
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'allenai/molmo-2-8b:free')
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Optional: Site URL and name for rankings on openrouter.ai
OPENROUTER_SITE_URL = os.getenv('OPENROUTER_SITE_URL', '').strip()
OPENROUTER_SITE_NAME = os.getenv('OPENROUTER_SITE_NAME', 'Smart Vision Guide').strip()

# ===============================================
# Local Face Recognition Configuration
# ===============================================

# Face database directory (folder per person, multiple images per person)
FACE_DATABASE_DIR = os.getenv('FACE_DATABASE_DIR', 'faces')

# Face recognition distance threshold (0.5-0.6 recommended, lower = stricter)
FACE_DISTANCE_THRESHOLD = float(os.getenv('FACE_DISTANCE_THRESHOLD', '0.6'))

# ===============================================
# Performance Tuning for Pi Zero 2W
# ===============================================

# Network Settings (optimized for slow connections)
REQUEST_TIMEOUT = 45  # Increased from 30s for Pi Zero WiFi
RETRY_ATTEMPTS = 2    # Number of retries for failed API calls
RETRY_DELAY = 2.0     # Seconds between retries

# Image Processing (reduced for faster processing and smaller payloads)
IMAGE_MAX_WIDTH = 512       # Reduced from 640 to match camera
IMAGE_JPEG_QUALITY = 60     # Reduced from 70 for smaller upload size

# Analysis Timeout (watchdog timer)
ANALYSIS_TIMEOUT = 60  # Maximum seconds for any analysis operation

# ===============================================
# Button Configuration (BCM pin numbers)
# SIMPLIFIED: 2-Button Interface
# ===============================================

# Button 1: Mode Toggle (cycles through modes)
BUTTON_MODE_PIN = int(os.getenv('BUTTON_MODE_PIN', '17'))

# Button 2: Select/Execute (runs current mode)
BUTTON_SELECT_PIN = int(os.getenv('BUTTON_SELECT_PIN', '27'))

# ===============================================
# Camera Settings (optimized for Pi Camera)
# ===============================================

# Reduced resolution for faster processing
CAMERA_WIDTH = int(os.getenv('CAMERA_WIDTH', '512'))   # Reduced from 640
CAMERA_HEIGHT = int(os.getenv('CAMERA_HEIGHT', '384'))  # Reduced from 480

# Camera optimization parameters
CAMERA_WARMUP_FRAMES = 10  # Number of frames to capture for warmup
CAMERA_RETRY_ATTEMPTS = 3  # Retry attempts for camera initialization

# ===============================================
# Audio/TTS Settings
# ===============================================

# TTS options: espeak (offline, recommended) or gtts (online)
TTS_BACKEND = os.getenv('TTS_BACKEND', 'espeak')

# Bluetooth audio routing via PulseAudio
USE_BLUETOOTH_AUDIO = os.getenv('USE_BLUETOOTH_AUDIO', 'true').lower() == 'true'

# ===============================================
# Local Face Recognition Settings
# ===============================================

# Face database directory
FACE_DB_DIR = os.getenv('FACE_DB_DIR', 'faces')

# Distance threshold for face matching (0.0 = identical, 1.0 = very different)
FACE_DISTANCE_THRESHOLD = float(os.getenv('FACE_DISTANCE_THRESHOLD', '0.6'))

# ===============================================
# Search Mode Configuration
# ===============================================

# Common objects that can be detected in search mode
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

# Memory optimization
ENABLE_GARBAGE_COLLECTION = True  # Run gc.collect() after analysis

# Logging
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
VERBOSE_LOGGING = os.getenv('VERBOSE_LOGGING', 'false').lower() == 'true'

# ===============================================
# Feature Flags
# ===============================================

# Enable/disable specific modes if resources are constrained
ENABLE_DESCRIBE_MODE = True
ENABLE_OCR_MODE = True
ENABLE_FACE_MODE = True  # Local face recognition, no API required
ENABLE_SEARCH_MODE = True

# ===============================================
# System Information
# ===============================================

def get_system_info():
    """Get system information for debugging."""
    info = {
        'openrouter_configured': bool(OPENROUTER_API_KEY),
        'openrouter_model': OPENROUTER_MODEL,
        'face_recognition': 'Local (dlib)',
        'camera_resolution': f"{CAMERA_WIDTH}x{CAMERA_HEIGHT}",
        'image_max_width': IMAGE_MAX_WIDTH,
        'request_timeout': REQUEST_TIMEOUT,
        'tts_backend': TTS_BACKEND
    }
    return info


if __name__ == '__main__':
    # Print configuration when run directly
    print("=" * 50)
    print("Smart Vision Guide - Configuration")
    print("=" * 50)
    
    info = get_system_info()
    
    print(f"\n🔧 API Configuration:")
    print(f"  OpenRouter: {'✓ Configured' if info['openrouter_configured'] else '✗ Not configured'}")
    print(f"  Model:      {info['openrouter_model']}")
    print(f"  Face Recognition: {info['face_recognition']}")
    
    print(f"\n📷 Camera Settings:")
    print(f"  Resolution:   {info['camera_resolution']}")
    print(f"  Warmup:       {CAMERA_WARMUP_FRAMES} frames")
    
    print(f"\n🖼️  Image Processing:")
    print(f"  Max Width:    {IMAGE_MAX_WIDTH}px")
    print(f"  JPEG Quality: {IMAGE_JPEG_QUALITY}%")
    
    print(f"\n🌐 Network:")
    print(f"  Timeout:      {REQUEST_TIMEOUT}s")
    print(f"  Retries:      {RETRY_ATTEMPTS}")
    
    print(f"\n🔊 Audio:")
    print(f"  TTS Backend:  {TTS_BACKEND}")
    print(f"  Bluetooth:    {'Enabled' if USE_BLUETOOTH_AUDIO else 'Disabled'}")
    
    print(f"\n🎮 Button Configuration:")
    print(f"  Mode Toggle:  GPIO {BUTTON_MODE_PIN}")
    print(f"  Select:       GPIO {BUTTON_SELECT_PIN}")
    
    print(f"\n🎯 Enabled Modes:")
    print(f"  Describe:     {'✓' if ENABLE_DESCRIBE_MODE else '✗'}")
    print(f"  OCR:          {'✓' if ENABLE_OCR_MODE else '✗'}")
    print(f"  Face:         {'✓' if ENABLE_FACE_MODE else '✗'}")
    print(f"  Search:       {'✓' if ENABLE_SEARCH_MODE else '✗'}")
    
    print("\n" + "=" * 50)
