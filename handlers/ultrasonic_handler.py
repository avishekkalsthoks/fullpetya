"""
Ultrasonic Sensor Handler for Smart Vision Guide
Detects nearby obstacles using HC-SR04 sensor and alerts via buzzer.
Optimized for Raspberry Pi Zero 2W.
"""

import time
import threading

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except Exception:
    GPIO = None
    GPIO_AVAILABLE = False
    print("⚠️  Warning: RPi.GPIO not available for ultrasonic sensor.")


class UltrasonicHandler:
    """
    Handles HC-SR04 ultrasonic sensor for obstacle detection.
    Uses a buzzer to alert user of nearby obstacles.
    
    Wiring:
    - VCC -> 5V
    - GND -> GND
    - TRIG -> GPIO 23 (configurable)
    - ECHO -> GPIO 24 (configurable, use voltage divider for 3.3V!)
    
    Buzzer:
    - Positive -> GPIO 25 (configurable)
    - Negative -> GND
    """
    
    def __init__(self, trigger_pin, echo_pin, buzzer_pin,
                 alert_distance=50, danger_distance=20,
                 check_interval=0.2, buzzer_frequency=2000):
        """
        Initialize ultrasonic handler.
        
        Args:
            trigger_pin: GPIO pin for ultrasonic TRIG
            echo_pin: GPIO pin for ultrasonic ECHO
            buzzer_pin: GPIO pin for buzzer
            alert_distance: Distance (cm) to start warning
            danger_distance: Distance (cm) for danger zone (continuous beep)
            check_interval: Time between distance checks (seconds)
            buzzer_frequency: Buzzer frequency in Hz (for PWM)
        """
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self.buzzer_pin = buzzer_pin
        self.alert_distance = alert_distance
        self.danger_distance = danger_distance
        self.check_interval = check_interval
        self.buzzer_frequency = buzzer_frequency
        
        self.running = False
        self.monitoring_thread = None
        self.last_distance = None
        self.buzzer_pwm = None
        
        self._setup_gpio()
    
    def _setup_gpio(self):
        """Setup GPIO pins for ultrasonic sensor and buzzer."""
        if not GPIO_AVAILABLE:
            print("⚠️  GPIO not available - ultrasonic sensor disabled")
            return False
        
        try:
            # Set GPIO mode if not already set
            if GPIO.getmode() is None:
                GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Setup ultrasonic pins
            GPIO.setup(self.trigger_pin, GPIO.OUT)
            GPIO.setup(self.echo_pin, GPIO.IN)
            GPIO.output(self.trigger_pin, GPIO.LOW)
            
            # Setup buzzer pin
            GPIO.setup(self.buzzer_pin, GPIO.OUT)
            GPIO.output(self.buzzer_pin, GPIO.LOW)
            
            # Try to setup PWM for buzzer (for variable beep patterns)
            try:
                self.buzzer_pwm = GPIO.PWM(self.buzzer_pin, self.buzzer_frequency)
            except Exception:
                self.buzzer_pwm = None
            
            print(f"✓ Ultrasonic sensor configured:")
            print(f"   TRIG: GPIO {self.trigger_pin}")
            print(f"   ECHO: GPIO {self.echo_pin}")
            print(f"   Buzzer: GPIO {self.buzzer_pin}")
            print(f"   Alert distance: {self.alert_distance}cm")
            print(f"   Danger distance: {self.danger_distance}cm")
            return True
            
        except Exception as e:
            print(f"✗ Failed to setup ultrasonic GPIO: {e}")
            return False
    
    def measure_distance(self):
        """
        Measure distance using HC-SR04 ultrasonic sensor.
        
        Returns:
            Distance in centimeters, or None if measurement failed
        """
        if not GPIO_AVAILABLE:
            return None
        
        try:
            # Send 10us pulse to trigger
            GPIO.output(self.trigger_pin, GPIO.HIGH)
            time.sleep(0.00001)  # 10 microseconds
            GPIO.output(self.trigger_pin, GPIO.LOW)
            
            # Wait for echo to go HIGH (with timeout)
            pulse_start = time.time()
            timeout_start = pulse_start
            while GPIO.input(self.echo_pin) == GPIO.LOW:
                pulse_start = time.time()
                if pulse_start - timeout_start > 0.1:  # 100ms timeout
                    return None
            
            # Wait for echo to go LOW (with timeout)
            pulse_end = time.time()
            timeout_start = pulse_end
            while GPIO.input(self.echo_pin) == GPIO.HIGH:
                pulse_end = time.time()
                if pulse_end - timeout_start > 0.1:  # 100ms timeout
                    return None
            
            # Calculate distance
            pulse_duration = pulse_end - pulse_start
            # Speed of sound = 34300 cm/s, divide by 2 for round trip
            distance = pulse_duration * 17150
            
            # Sanity check (HC-SR04 range: 2cm - 400cm)
            if distance < 2 or distance > 400:
                return None
            
            self.last_distance = distance
            return round(distance, 1)
            
        except Exception as e:
            print(f"⚠️  Distance measurement error: {e}")
            return None
    
    def buzzer_on(self, duty_cycle=50):
        """Turn on buzzer."""
        if not GPIO_AVAILABLE:
            return
        
        try:
            if self.buzzer_pwm:
                self.buzzer_pwm.start(duty_cycle)
            else:
                GPIO.output(self.buzzer_pin, GPIO.HIGH)
        except Exception:
            pass
    
    def buzzer_off(self):
        """Turn off buzzer."""
        if not GPIO_AVAILABLE:
            return
        
        try:
            if self.buzzer_pwm:
                self.buzzer_pwm.stop()
            else:
                GPIO.output(self.buzzer_pin, GPIO.LOW)
        except Exception:
            pass
    
    def beep(self, duration=0.1, duty_cycle=50):
        """
        Short beep sound.
        
        Args:
            duration: Beep duration in seconds
            duty_cycle: PWM duty cycle (0-100)
        """
        self.buzzer_on(duty_cycle)
        time.sleep(duration)
        self.buzzer_off()
    
    def _get_beep_pattern(self, distance):
        """
        Get beep pattern based on distance.
        
        Returns:
            Tuple of (beep_duration, pause_duration) or None for no beep
        """
        if distance is None:
            return None
        
        if distance <= self.danger_distance:
            # Danger zone: continuous rapid beeping
            return (0.05, 0.05)
        elif distance <= self.alert_distance / 2:
            # Very close: fast beeping
            return (0.1, 0.1)
        elif distance <= self.alert_distance:
            # Alert zone: medium beeping
            return (0.1, 0.3)
        else:
            # Safe zone: no beep
            return None
    
    def _monitoring_loop(self):
        """Main loop for continuous obstacle monitoring."""
        while self.running:
            try:
                distance = self.measure_distance()
                pattern = self._get_beep_pattern(distance)
                
                if pattern:
                    beep_duration, pause_duration = pattern
                    self.beep(beep_duration)
                    time.sleep(pause_duration)
                else:
                    time.sleep(self.check_interval)
                    
            except Exception as e:
                print(f"⚠️  Ultrasonic monitoring error: {e}")
                time.sleep(self.check_interval)
    
    def start_monitoring(self):
        """Start continuous obstacle monitoring in background thread."""
        if not GPIO_AVAILABLE:
            print("⚠️  Cannot start monitoring - GPIO not available")
            return False
        
        if self.running:
            return True
        
        self.running = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()
        print("✓ Ultrasonic obstacle monitoring started")
        return True
    
    def stop_monitoring(self):
        """Stop obstacle monitoring."""
        self.running = False
        self.buzzer_off()
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=1.0)
            self.monitoring_thread = None
        
        print("✓ Ultrasonic obstacle monitoring stopped")
    
    def get_status(self):
        """Get current sensor status."""
        distance = self.measure_distance()
        return {
            "enabled": GPIO_AVAILABLE,
            "monitoring": self.running,
            "last_distance_cm": distance,
            "alert_distance_cm": self.alert_distance,
            "danger_distance_cm": self.danger_distance,
            "in_alert_zone": distance is not None and distance <= self.alert_distance,
            "in_danger_zone": distance is not None and distance <= self.danger_distance
        }
    
    def cleanup(self):
        """Cleanup GPIO resources."""
        self.stop_monitoring()
        
        if GPIO_AVAILABLE:
            try:
                if self.buzzer_pwm:
                    self.buzzer_pwm.stop()
                GPIO.output(self.buzzer_pin, GPIO.LOW)
            except Exception:
                pass
