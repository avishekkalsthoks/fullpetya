#!/usr/bin/env python3
"""
Test script for Ultrasonic Sensor + Buzzer

Run this script to test your HC-SR04 ultrasonic sensor and buzzer setup
before using it with the main Smart Vision Guide application.

Usage:
    python3 test_ultrasonic.py

Wiring:
    HC-SR04:
        VCC  -> Pi 5V
        GND  -> Pi GND
        TRIG -> GPIO 23 (default)
        ECHO -> GPIO 24 (default, use voltage divider!)
    
    Buzzer:
        Positive -> GPIO 25 (default)
        Negative -> Pi GND
"""

import sys
import time
import argparse

# Try to import RPi.GPIO
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO = None
    GPIO_AVAILABLE = False
    print("⚠️  RPi.GPIO not available. Running in simulation mode.")


def test_buzzer(buzzer_pin):
    """Test the buzzer with a few beeps."""
    print(f"\n🔊 Testing Buzzer on GPIO {buzzer_pin}...")
    
    if not GPIO_AVAILABLE:
        print("   [SIMULATION] Would beep 3 times")
        return True
    
    try:
        GPIO.setup(buzzer_pin, GPIO.OUT)
        
        for i in range(3):
            print(f"   Beep {i+1}/3")
            GPIO.output(buzzer_pin, GPIO.HIGH)
            time.sleep(0.2)
            GPIO.output(buzzer_pin, GPIO.LOW)
            time.sleep(0.2)
        
        print("   ✓ Buzzer test complete")
        return True
        
    except Exception as e:
        print(f"   ✗ Buzzer test failed: {e}")
        return False


def measure_distance(trigger_pin, echo_pin):
    """Measure distance using HC-SR04."""
    if not GPIO_AVAILABLE:
        return 42.0  # Simulation value
    
    try:
        # Send trigger pulse
        GPIO.output(trigger_pin, GPIO.HIGH)
        time.sleep(0.00001)  # 10 microseconds
        GPIO.output(trigger_pin, GPIO.LOW)
        
        # Wait for echo to go HIGH
        pulse_start = time.time()
        timeout_start = pulse_start
        while GPIO.input(echo_pin) == GPIO.LOW:
            pulse_start = time.time()
            if pulse_start - timeout_start > 0.1:
                return None  # Timeout
        
        # Wait for echo to go LOW
        pulse_end = time.time()
        timeout_start = pulse_end
        while GPIO.input(echo_pin) == GPIO.HIGH:
            pulse_end = time.time()
            if pulse_end - timeout_start > 0.1:
                return None  # Timeout
        
        # Calculate distance
        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150  # Speed of sound / 2
        
        if distance < 2 or distance > 400:
            return None  # Out of range
        
        return round(distance, 1)
        
    except Exception as e:
        print(f"   Error: {e}")
        return None


def test_ultrasonic(trigger_pin, echo_pin):
    """Test the ultrasonic sensor with continuous readings."""
    print(f"\n📏 Testing Ultrasonic Sensor...")
    print(f"   TRIG: GPIO {trigger_pin}")
    print(f"   ECHO: GPIO {echo_pin}")
    
    if not GPIO_AVAILABLE:
        print("   [SIMULATION] Would measure distance continuously")
        return True
    
    try:
        GPIO.setup(trigger_pin, GPIO.OUT)
        GPIO.setup(echo_pin, GPIO.IN)
        GPIO.output(trigger_pin, GPIO.LOW)
        
        # Give sensor time to settle
        time.sleep(0.5)
        
        print("\n   Taking 10 measurements (1 per second)...")
        print("   Move objects closer/further to see distance change.\n")
        
        for i in range(10):
            distance = measure_distance(trigger_pin, echo_pin)
            if distance is not None:
                # Visual bar
                bar_len = min(50, int(distance / 4))
                bar = "█" * bar_len
                print(f"   [{i+1:2d}] {distance:6.1f} cm  {bar}")
            else:
                print(f"   [{i+1:2d}] ------ (no reading)")
            time.sleep(1)
        
        print("\n   ✓ Ultrasonic sensor test complete")
        return True
        
    except Exception as e:
        print(f"   ✗ Ultrasonic test failed: {e}")
        return False


def test_combined(trigger_pin, echo_pin, buzzer_pin, alert_distance, danger_distance):
    """Test ultrasonic + buzzer together."""
    print(f"\n🎯 Testing Combined Mode...")
    print(f"   Alert distance: {alert_distance} cm")
    print(f"   Danger distance: {danger_distance} cm")
    print(f"\n   Press Ctrl+C to stop.\n")
    
    if not GPIO_AVAILABLE:
        print("   [SIMULATION] Would run combined test")
        return True
    
    try:
        GPIO.setup(trigger_pin, GPIO.OUT)
        GPIO.setup(echo_pin, GPIO.IN)
        GPIO.setup(buzzer_pin, GPIO.OUT)
        GPIO.output(trigger_pin, GPIO.LOW)
        GPIO.output(buzzer_pin, GPIO.LOW)
        
        time.sleep(0.5)
        
        while True:
            distance = measure_distance(trigger_pin, echo_pin)
            
            if distance is not None:
                if distance <= danger_distance:
                    status = "🔴 DANGER"
                    GPIO.output(buzzer_pin, GPIO.HIGH)
                    time.sleep(0.05)
                    GPIO.output(buzzer_pin, GPIO.LOW)
                    time.sleep(0.05)
                elif distance <= alert_distance / 2:
                    status = "🟠 CLOSE"
                    GPIO.output(buzzer_pin, GPIO.HIGH)
                    time.sleep(0.1)
                    GPIO.output(buzzer_pin, GPIO.LOW)
                    time.sleep(0.1)
                elif distance <= alert_distance:
                    status = "🟡 ALERT"
                    GPIO.output(buzzer_pin, GPIO.HIGH)
                    time.sleep(0.1)
                    GPIO.output(buzzer_pin, GPIO.LOW)
                    time.sleep(0.3)
                else:
                    status = "🟢 SAFE"
                    GPIO.output(buzzer_pin, GPIO.LOW)
                    time.sleep(0.2)
                
                print(f"   {distance:6.1f} cm  {status}    ", end="\r")
            else:
                print(f"   ------ (no reading)      ", end="\r")
                time.sleep(0.2)
                
    except KeyboardInterrupt:
        GPIO.output(buzzer_pin, GPIO.LOW)
        print("\n\n   ✓ Combined test stopped")
        return True
        
    except Exception as e:
        print(f"\n   ✗ Combined test failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test Ultrasonic Sensor and Buzzer")
    parser.add_argument("--trig", type=int, default=23, help="TRIG GPIO pin (default: 23)")
    parser.add_argument("--echo", type=int, default=24, help="ECHO GPIO pin (default: 24)")
    parser.add_argument("--buzzer", type=int, default=25, help="Buzzer GPIO pin (default: 25)")
    parser.add_argument("--alert", type=float, default=50, help="Alert distance cm (default: 50)")
    parser.add_argument("--danger", type=float, default=20, help="Danger distance cm (default: 20)")
    parser.add_argument("--test", choices=["buzzer", "ultrasonic", "combined", "all"], 
                        default="all", help="Which test to run (default: all)")
    args = parser.parse_args()
    
    print("=" * 60)
    print("Ultrasonic Sensor + Buzzer Test")
    print("=" * 60)
    
    if GPIO_AVAILABLE:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
    
    try:
        if args.test in ["buzzer", "all"]:
            test_buzzer(args.buzzer)
        
        if args.test in ["ultrasonic", "all"]:
            test_ultrasonic(args.trig, args.echo)
        
        if args.test in ["combined", "all"]:
            test_combined(args.trig, args.echo, args.buzzer, args.alert, args.danger)
        
    finally:
        if GPIO_AVAILABLE:
            GPIO.cleanup()
            print("\n✓ GPIO cleanup complete")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
