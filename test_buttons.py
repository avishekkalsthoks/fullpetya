import time
import sys

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("❌ Error: RPi.GPIO library not found.")
    print("If you are on a laptop, this script requires a Raspberry Pi.")
    print("If you are on a Pi, install it with: sudo apt-get install python3-rpi.gpio")
    sys.exit(1)

# Import pins from config if available, otherwise use defaults
try:
    from config import BUTTON_MODE_PIN, BUTTON_SELECT_PIN
except ImportError:
    print("⚠️  Warning: Could not import config.py. Using default pins (17, 27).")
    BUTTON_MODE_PIN = 17
    BUTTON_SELECT_PIN = 27

def test_buttons():
    """Test button inputs on the Raspberry Pi."""
    print("=" * 50)
    print("Smart Vision Guide - Button Connectivity Test")
    print("=" * 50)
    print(f"Configured Pins:")
    print(f"  - Mode Button:   GPIO {BUTTON_MODE_PIN}")
    print(f"  - Select Button: GPIO {BUTTON_SELECT_PIN}")
    print("-" * 50)

    # Use BCM GPIO numbering
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Setup pins as inputs with internal pull-up resistors
    # This assumes the buttons connect the pin to Ground when pressed
    GPIO.setup(BUTTON_MODE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(BUTTON_SELECT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    print("Initial States (Should be 'Released'):")
    print(f"  Mode Button:   {'PRESSED' if GPIO.input(BUTTON_MODE_PIN) == GPIO.LOW else 'Released'}")
    print(f"  Select Button: {'PRESSED' if GPIO.input(BUTTON_SELECT_PIN) == GPIO.LOW else 'Released'}")
    print("-" * 50)
    
    print("DIRECTIONS:")
    print("1. Press the 'Mode' button (GPIO 17)")
    print("2. Press the 'Select' button (GPIO 27)")
    print("3. Press Ctrl+C to exit the test")
    print("-" * 50)

    try:
        mode_pressed = False
        select_pressed = False
        
        while True:
            # Check Mode Button
            if GPIO.input(BUTTON_MODE_PIN) == GPIO.LOW:
                if not mode_pressed:
                    print("✅ [EVENT] Mode Button PRESSED")
                    mode_pressed = True
            else:
                if mode_pressed:
                    print("   [EVENT] Mode Button Released")
                    mode_pressed = False

            # Check Select Button
            if GPIO.input(BUTTON_SELECT_PIN) == GPIO.LOW:
                if not select_pressed:
                    print("✅ [EVENT] Select Button PRESSED")
                    select_pressed = True
            else:
                if select_pressed:
                    print("   [EVENT] Select Button Released")
                    select_pressed = False

            time.sleep(0.05)  # Small delay to reduce CPU usage

    except KeyboardInterrupt:
        print("\n\nTest stopped by user.")
    finally:
        GPIO.cleanup()
        print("GPIO Cleaned up. Exiting.")

if __name__ == "__main__":
    test_buttons()
