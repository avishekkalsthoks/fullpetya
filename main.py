"""
Smart Vision Guide - Main Application (Pi Zero 2W Optimized)
Assistive device for visually impaired users with 4 modes:
- Describe: Scene description
- OCR: Text reading
- Face: Face recognition
- Search: Object search

2-Button Interface:
- Button 1 (GPIO 17): Mode Toggle - Cycles through modes
- Button 2 (GPIO 27): Select - Executes current mode / Power on at startup

Mode Cycling: Describe → OCR → Face → Search → Shutdown → (repeat)

Optimizations for Pi Zero 2W:
- Watchdog timer for hung operations
- Progress feedback during analysis
- Graceful degradation on errors
- Button debounce with state tracking
"""

import threading
import time
import sys
import traceback
import os
import gc  # Garbage collection for memory optimization
from config import (
    BUTTON_MODE_PIN, BUTTON_SELECT_PIN,
    CAMERA_WIDTH, CAMERA_HEIGHT, TTS_BACKEND,
    ANALYSIS_TIMEOUT
)
from handlers.camera_handler import CameraHandler
from handlers.audio_handler import AudioHandler
from handlers.ai_handler import AIHandler

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except Exception:
    GPIO = None
    GPIO_AVAILABLE = False
    print("⚠️  Warning: RPi.GPIO not available. Running in simulation mode.")


class SmartVision:
    """Main Smart Vision Guide application with 2-button interface."""
    
    # Mode definitions with circular ordering
    MODE_SEQUENCE = ['describe', 'ocr', 'face', 'search', 'shutdown']
    
    MODES = {
        'describe': {
            'name': 'Describe',
            'announcement': 'Describe mode',
            'description': 'Scene description'
        },
        'ocr': {
            'name': 'OCR',
            'announcement': 'Text reading mode',
            'description': 'Read visible text'
        },
        'face': {
            'name': 'Face',
            'announcement': 'Face recognition mode',
            'description': 'Identify people'
        },
        'search': {
            'name': 'Search',
            'announcement': 'Search mode',
            'description': 'Find objects'
        },
        'shutdown': {
            'name': 'Shutdown',
            'announcement': 'Shutdown mode. Press select to power off.',
            'description': 'Power off the system'
        }
    }
    
    def __init__(self):
        self.running = True
        self.selected_mode = 'describe'  # Default starting mode
        self.analysis_in_progress = False
        
        # Button debounce tracking
        self.last_button_press = {}
        self.button_debounce_time = 0.3  # 300ms debounce
        
        print("🚀 Initializing Smart Vision Guide...")
        
        # Initialize handlers with error handling
        try:
            self.camera = CameraHandler(width=CAMERA_WIDTH, height=CAMERA_HEIGHT)
            print("✓ Camera handler initialized")
        except Exception as e:
            print(f"✗ Camera initialization failed: {e}")
            raise
        
        try:
            self.audio = AudioHandler(backend=TTS_BACKEND)
            print("✓ Audio handler initialized")
        except Exception as e:
            print(f"✗ Audio initialization failed: {e}")
            raise
        
        # Initialize AI handler (may fail if not configured)
        try:
            self.ai = AIHandler()
            print("✓ AI handler initialized")
        except Exception as e:
            print(f"⚠️  AI service not configured: {e}")
            print("   Describe, OCR, and Search modes will not work.")
            print("   Please set OPENROUTER_API_KEY in .env file.")
            self.ai = None
        
        # Initialize face handler (local offline recognition)
        try:
            from handlers.face_recognition_handler import FaceRecognitionHandler
            self.face = FaceRecognitionHandler(faces_dir='faces')
            stats = self.face.get_stats()
            print(f"✓ Local face recognition initialized: {stats['unique_people']} people enrolled")
        except Exception as e:
            print(f"⚠️  Face recognition not available: {e}")
            print("   Face mode will not work.")
            print("   Please ensure python3-dlib is installed and faces/ folder exists.")
            self.face = None
        
        # Setup GPIO
        self._setup_gpio()
        
        print("✓ Initialization complete")

    def _setup_gpio(self):
        """Setup GPIO pins for 2-button interface."""
        if not GPIO_AVAILABLE:
            print("⚠️  GPIO not available - buttons will not work")
            return
            
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Button 1: Mode Toggle
        GPIO.setup(BUTTON_MODE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(BUTTON_MODE_PIN, GPIO.FALLING, 
                             callback=self._mode_toggle_handler, 
                             bouncetime=300)
        
        # Button 2: Select/Execute
        GPIO.setup(BUTTON_SELECT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(BUTTON_SELECT_PIN, GPIO.FALLING, 
                             callback=self._select_handler, 
                             bouncetime=300)
        
        print(f"✓ GPIO buttons configured:")
        print(f"   Mode Toggle: GPIO {BUTTON_MODE_PIN}")
        print(f"   Select:      GPIO {BUTTON_SELECT_PIN}")

    def _is_debounced(self, channel):
        """Check if button press should be debounced."""
        current_time = time.time()
        last_press = self.last_button_press.get(channel, 0)
        
        if current_time - last_press < self.button_debounce_time:
            print(f"Button {channel} debounced")
            return True
        
        self.last_button_press[channel] = current_time
        return False

    def _mode_toggle_handler(self, channel):
        """
        Handle mode toggle button press.
        Cycles through: Describe → OCR → Face → Search → Shutdown → (repeat)
        """
        if self._is_debounced(channel):
            return
        
        if self.analysis_in_progress:
            self.audio.say("Please wait, I'm busy.")
            return
        
        # Find current mode index
        try:
            current_index = self.MODE_SEQUENCE.index(self.selected_mode)
        except ValueError:
            current_index = 0
        
        # Move to next mode (circular)
        next_index = (current_index + 1) % len(self.MODE_SEQUENCE)
        self.selected_mode = self.MODE_SEQUENCE[next_index]
        
        # Announce new mode
        mode_info = self.MODES.get(self.selected_mode, {})
        announcement = mode_info.get('announcement', f'{self.selected_mode} mode')
        
        print(f"🔄 Mode toggled to: {self.selected_mode}")
        self.audio.say(announcement)

    def _select_handler(self, channel):
        """
        Handle select button press.
        Executes the currently selected mode.
        """
        if self._is_debounced(channel):
            return
        
        if self.analysis_in_progress:
            self.audio.say("Please wait, I'm still processing.")
            return
        
        print(f"✓ Select pressed - executing: {self.selected_mode}")
        
        # Execute based on selected mode
        if self.selected_mode == 'shutdown':
            self._shutdown()
        else:
            threading.Thread(target=self._run_analysis, 
                           kwargs={'mode': self.selected_mode}, 
                           daemon=True).start()

    def _run_analysis(self, mode='describe', query=None):
        """
        Run analysis based on the selected mode with watchdog timer.
        
        Args:
            mode: One of 'describe', 'ocr', 'face', 'search'
            query: Optional query for search mode
        """
        self.analysis_in_progress = True
        
        try:
            # For search mode, we need to get the query first
            if mode == 'search' and query is None:
                query = self._get_search_query()
                if not query:
                    self.audio.say("Search cancelled.")
                    return
            
            # Check if required service is available
            if mode in ['describe', 'ocr', 'search'] and not self.ai:
                self.audio.say("Analysis service is not configured. Please set up Hugging Face API credentials.")
                return
            
            if mode == 'face' and not self.face:
                self.audio.say("Face recognition is not configured. Please set up Face++ API credentials.")
                return
            
            # Capture image with progress feedback
            self.audio.say("Capturing image.")
            start_time = time.time()
            
            try:
                img = self.camera.capture_image_bytes()
                capture_time = time.time() - start_time
                print(f"✓ Image captured in {capture_time:.1f}s")
            except Exception as e:
                print(f"✗ Camera error: {e}")
                self.audio.say("Sorry, I couldn't capture an image. Please check the camera and try again.")
                return
            
            # Process based on mode with watchdog timer
            analysis_start = time.time()
            
            # Create a watchdog timer thread
            watchdog_triggered = threading.Event()
            
            def watchdog():
                if not watchdog_triggered.wait(timeout=ANALYSIS_TIMEOUT):
                    print(f"⚠️  Analysis timeout after {ANALYSIS_TIMEOUT}s")
                    self.audio.say("The analysis is taking too long. Please try again.")
            
            watchdog_thread = threading.Thread(target=watchdog, daemon=True)
            watchdog_thread.start()
            
            # Run the actual analysis
            if mode == 'face':
                self._process_face_mode(img)
            else:
                self._process_ai_mode(img, mode, query)
            
            # Cancel watchdog
            watchdog_triggered.set()
            
            analysis_time = time.time() - analysis_start
            print(f"✓ Analysis completed in {analysis_time:.1f}s")
            
            # Trigger garbage collection to free memory
            gc.collect()
                
        except Exception as e:
            print(f'✗ Error during analysis: {e}')
            traceback.print_exc()
            self.audio.say("Sorry, an error occurred. Please try again.")
        finally:
            self.analysis_in_progress = False

    def _process_face_mode(self, image_bytes):
        """Process local face recognition mode."""
        if not self.face:
            self.audio.say("Face recognition is not available.")
            return
        
        self.audio.say("Looking for faces. Please wait.")
        
        try:
            # Use local face recognition (no API calls)
            result = self.face.recognize_from_bytes(image_bytes)
            self.audio.say(result)
            
        except Exception as e:
            print(f"✗ Face recognition error: {e}")
            traceback.print_exc()
            self.audio.say("Sorry, face recognition failed. Please try again.")

    def _process_ai_mode(self, image_bytes, mode, query=None):
        """Process AI-based modes (describe, OCR, search)."""
        if not self.ai:
            self.audio.say("Analysis service is not configured.")
            return
        
        self.audio.say("Analyzing. Please wait.")
        
        # Progress callback for long operations
        def progress_callback(message):
            print(f"Progress: {message}")
        
        try:
            result = self.ai.analyze_image(
                image_bytes, 
                mode=mode, 
                query=query,
                progress_callback=progress_callback
            )
            self.audio.say(result)
            
        except Exception as e:
            print(f"✗ AI analysis error: {e}")
            traceback.print_exc()
            self.audio.say("Sorry, the analysis failed. Please check your internet connection and try again.")

    def _get_search_query(self):
        """
        Get search query from user via voice input.
        
        For now, this is a placeholder - in production, you would:
        1. Use speech recognition (e.g., Vosk) to listen for the query
        2. Parse the query
        3. Return the search term
        
        Returns:
            Search query string or None if cancelled
        """
        # Placeholder - announce that we're listening
        self.audio.say("Listening. What should I search for?")
        
        # For demonstration, return a default query
        # In production, replace with actual speech recognition
        # For now, we'll search for "person" as a fallback
        time.sleep(2)  # Simulate listening time
        return "person"

    def _shutdown(self):
        """Shutdown the system gracefully."""
        print("🔴 Shutting down...")
        self.audio.say("Shutting down. Goodbye.")
        time.sleep(2)
        
        # Cleanup
        try:
            self.camera.stop()
        except Exception:
            pass
            
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        
        # Shutdown the Pi
        print("Executing shutdown command...")
        os.system("sudo shutdown -h now")

    def run(self):
        """Main application loop."""
        # Startup announcement
        self.audio.say("Smart Vision Guide ready.")
        time.sleep(0.5)
        
        # Announce starting mode
        mode_info = self.MODES.get(self.selected_mode, {})
        self.audio.say(mode_info.get('announcement', 'Describe mode'))
        
        print("=" * 60)
        print("Smart Vision Guide - 2-Button Interface")
        print("=" * 60)
        print(f"Button 1 (GPIO {BUTTON_MODE_PIN}): Toggle mode")
        print(f"Button 2 (GPIO {BUTTON_SELECT_PIN}): Select/Execute")
        print("")
        print(f"Current mode: {self.selected_mode}")
        print("Press Ctrl+C to exit")
        print("=" * 60)
        
        try:
            while self.running:
                time.sleep(0.1)  # Small delay to prevent CPU spinning
        except KeyboardInterrupt:
            print('\n🔴 Exiting...')
        finally:
            self._cleanup()

    def _cleanup(self):
        """Cleanup resources."""
        print("Cleaning up...")
        try:
            self.camera.stop()
        except Exception:
            pass
            
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        
        print("✓ Cleanup complete")


def main():
    """Entry point with error handling."""
    try:
        sv = SmartVision()
        sv.run()
    except KeyboardInterrupt:
        print("\n🔴 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
