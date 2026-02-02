"""
Hardware Test Script - Pi Zero 2W Optimized
Tests camera, audio, button functionality, and system resources.
"""

import time
import sys
import os

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True  
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠️  Warning: RPi.GPIO not available. Button tests will be skipped.")

from handlers.camera_handler import CameraHandler
from handlers.audio_handler import AudioHandler
from config import (
    BUTTON_MODE_PIN, BUTTON_SELECT_PIN
)


def get_system_resources():
    """Get Pi Zero system resource information."""
    try:
        # Memory info
        with open('/proc/meminfo', 'r') as f:
            mem_info = {}
            for line in f:
                parts = line.split(':')
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip().split()[0]
                    mem_info[key] = int(value)
        
        mem_total_mb = mem_info.get('MemTotal', 0) // 1024
        mem_available_mb = mem_info.get('MemAvailable', 0) // 1024
        
        # Temperature
        try:
            temp_str = os.popen('vcgencmd measure_temp').read()
            temp = temp_str.replace("temp=", "").replace("'C\n", "")
        except:
            temp = "N/A"
        
        # CPU info
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'Model' in line:
                        model = line.split(':')[ 1].strip()
                        break
                else:
                    model = "Unknown"
        except:
            model = "Unknown"
        
        return {
            'model': model,
            'mem_total_mb': mem_total_mb,
            'mem_available_mb': mem_available_mb,
            'temperature': temp
        }
    except Exception as e:
        print(f"Error getting system info: {e}")
        return None


def test_system_resources():
    """Test system resources for Pi Zero 2W compatibility."""
    print("\n=== System Resources ===")
    
    info = get_system_resources()
    if not info:
        print("✗ Could not read system information")
        return False
    
    print(f"Model:          {info['model']}")
    print(f"Total RAM:      {info['mem_total_mb']} MB")
    print(f"Available RAM:  {info['mem_available_mb']} MB")
    print(f"Temperature:    {info['temperature']}°C")
    
    # Checks
    passed = True
    
    if info['mem_total_mb'] < 400:
        print("⚠️  Warning: Low total memory. Expected ~512MB for Pi Zero 2W")
        passed = False
    
    if info['mem_available_mb'] < 100:
        print("⚠️  Warning: Low available memory. Close other applications")
        passed = False
    
    try:
        temp_val = float(info['temperature'])
        if temp_val > 70:
            print(f"⚠️  Warning: High temperature ({temp_val}°C). Add cooling")
            passed = False
    except:
        pass
    
    if passed:
        print("✓ System resources OK")
    
    return passed


def test_camera():
    """Test camera capture with memory monitoring."""
    print("\n=== Testing Camera ===")
    
    try:
        import resource
        mem_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        
        camera = CameraHandler()
        print("Capturing image...")
        
        start_time = time.time()
        img = camera.capture_image_bytes()
        capture_time = time.time() - start_time
        
        mem_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        mem_used_kb = mem_after - mem_before
        
        print(f"✓ Camera working!")
        print(f"  Image size:    {len(img)} bytes")
        print(f"  Capture time:  {capture_time:.2f}s")
        print(f"  Memory used:   ~{mem_used_kb} KB")
        
        if capture_time > 5:
            print(f"⚠️  Warning: Slow capture time ({capture_time:.1f}s)")
        
        # Save test image
        import tempfile
        path = camera.capture_image_file('/tmp/test_capture.jpg')
        print(f"✓ Test image saved to: {path}")
        
        camera.stop()
        return True
        
    except Exception as e:
        print(f"✗ Camera test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_audio():
    """Test text-to-speech."""
    print("\n=== Testing Audio ===")
    
    try:
        audio = AudioHandler()
        
        print("Testing espeak...")
        audio.say("Audio test successful. Smart Vision Guide is ready.")
        
        # Test Bluetooth detection
        bt_sinks = audio.get_bluetooth_sinks()
        if bt_sinks:
            print(f"✓ Found {len(bt_sinks)} Bluetooth audio sink(s):")
            for sink in bt_sinks:
                print(f"    - {sink}")
        else:
            print("  No Bluetooth audio sinks detected")
        
        print("✓ Audio test completed")
        return True
        
    except Exception as e:
        print(f"✗ Audio test failed: {e}")
        return False


def test_buttons():
    """Test button inputs."""
    print("\n=== Testing Buttons ===")
    
    if not GPIO_AVAILABLE:
        print("✗ GPIO not available. Skipping button tests")
        return False
    
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        buttons = {
            'Mode Toggle': BUTTON_MODE_PIN,
            'Select': BUTTON_SELECT_PIN
        }
        
        # Setup pins as inputs with pull-up
        for name, pin in buttons.items():
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            # Test initial state
            state = GPIO.input(pin)
            print(f"  {name} (GPIO {pin}): {'OK' if state == 1 else 'PRESSED'}")
        
        print("\n✓ Buttons configured")
        print("Press each button to test (Ctrl+C to skip):")
        
        button_pressed = {}
        
        def button_callback(channel):
            for name, pin in buttons.items():
                if pin == channel:
                    print(f"  → {name} button pressed!")
                    button_pressed[name] = True
                    break
        
        # Add event detection
        for pin in buttons.values():
            GPIO.add_event_detect(pin, GPIO.FALLING, 
                                callback=button_callback, 
                                bouncetime=200)
        
        # Wait for button presses
        try:
            timeout = 10
            start = time.time()
            while time.time() - start < timeout:
                time.sleep(0.1)
                if len(button_pressed) == len(buttons):
                    break
        except KeyboardInterrupt:
            pass
        
        GPIO.cleanup()
        
        if button_pressed:
            print(f"\n✓ Tested {len(button_pressed)}/{len(buttons)} buttons")
        
        return True
        
    except Exception as e:
        print(f"✗ Button test failed: {e}")
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        return False


def test_face_recognition():
    """Test local face recognition."""
    print("\n=== Testing Local Face Recognition ===")
    
    try:
        from handlers.face_recognition_handler import FaceRecognitionHandler
        face = FaceRecognitionHandler(faces_dir='faces')
        
        stats = face.get_stats()
        print(f"✓ Local face recognition initialized")
        print(f"  Enrolled people: {stats['unique_people']}")
        
        if stats['people']:
            for name in stats['people']:
                print(f"    - {name}")
        else:
            print("    (No enrolled faces yet)")
            print("    Use: python3 enroll_face.py <name>")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Face recognition not available: {e}")
        return False


def test_huggingface():
    """Test Hugging Face API connection."""
    print("\n=== Testing Hugging Face API ===")
    
    try:
        from handlers.ai_handler import AIHandler
        ai = AIHandler()
        
        print(f"✓ Hugging Face API configured")
        
        return True
        
    except RuntimeError as e:
        print(f"⚠️  Hugging Face API not configured: {e}")
        return False
    except Exception as e:
        print(f"✗ Hugging Face API test failed: {e}")
        return False


def test_dependencies():
    """Test that all dependencies are properly installed."""
    print("\n=== Testing Dependencies ===")
    
    deps = {
        'cv2': 'OpenCV',
        'numpy': 'NumPy',
        'PIL': 'Pillow',
        'requests': 'Requests',
        'dotenv': 'python-dotenv',
        'gtts': 'gTTS'
    }
    
    all_ok = True
    for module, name in deps.items():
        try:
            __import__(module)
            print(f"✓ {name}")
        except ImportError:
            print(f"✗ {name} - NOT INSTALLED")
            all_ok = False
    
    return all_ok


def main():
    """Run all hardware tests."""
    print("=" * 60)
    print("Smart Vision Guide - Hardware Test (Pi Zero 2W)")
    print("=" * 60)
    
    results = {}
    
    # System check first
    results['System Resources'] = test_system_resources()
    results['Dependencies'] = test_dependencies()
    results['Camera'] = test_camera()
    results['Audio'] = test_audio()
    results['Local Face Recognition'] = test_face_recognition()
    results['Hugging Face API'] = test_huggingface()
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:25s}: {status}")
    
    # Button test is interactive  
    print("\n" + "=" * 60)
    print("Would you like to test buttons? This is interactive. (y/n): ", end='')
    try:
        response = input().lower()
        if response == 'y':
            results['Buttons'] = test_buttons()
    except (EOFError, KeyboardInterrupt):
        pass
    
    print("\n" + "=" * 60)
    print("Testing complete!")
    
    # Overall status
    critical_tests = ['System Resources', 'Dependencies', 'Camera', 'Audio']
    critical_passed = all(results.get(t, False) for t in critical_tests)
    
    if critical_passed:
        print("✓ All critical tests passed - system ready!")
    else:
        print("⚠️  Some critical tests failed - please fix before running")
    
    print("=" * 60)


if __name__ == '__main__':
    main()
