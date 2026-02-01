"""
Audio Handler for Smart Vision Guide
Optimized for Raspberry Pi Zero 2W with Bluetooth audio support and minimal overhead.
"""

import subprocess
import shutil
import os
from gtts import gTTS


class AudioHandler:
    """Handler for text-to-speech output with Pi Zero 2W optimizations."""
    
    # Mode announcement phrases
    MODE_SOUNDS = {
        'describe': 'describe_mode.wav',
        'ocr': 'ocr_mode.wav',
        'face': 'face_mode.wav',
        'search': 'search_mode.wav'
    }
    
    def __init__(self, backend='espeak', use_bluetooth=True):
        """
        Initialize audio handler.
        
        Args:
            backend: TTS backend ('espeak' for offline, 'gtts' for online)
            use_bluetooth: Whether to route audio through Bluetooth (via PulseAudio)
        """
        self.backend = backend
        self.use_bluetooth = use_bluetooth
        self._test_audio_system()

    def _test_audio_system(self):
        """Test audio system availability."""
        # Check if espeak is available
        if not shutil.which('espeak'):
            print("⚠️  Warning: espeak not found. TTS may not work.")
        
        # Check PulseAudio for Bluetooth
        if self.use_bluetooth:
            result = subprocess.run(['pactl', 'info'], 
                                  capture_output=True, 
                                  timeout=2)
            if result.returncode != 0:
                print("⚠️  Warning: PulseAudio not running. Bluetooth audio may not work.")

    def say(self, text, lang='en'):
        """
        Speak the given text using the configured TTS backend.
        
        Args:
            text: Text to speak
            lang: Language code (default 'en')
        """
        if not text:
            return
            
        if self.backend == 'gtts':
            try:
                tts = gTTS(text=text, lang=lang, slow=False)
                tmp = '/tmp/speech.mp3'
                tts.save(tmp)
                
                # Try multiple playback methods
                played = False
                
                # Method 1: ffplay (most reliable)
                if shutil.which('ffplay'):
                    result = subprocess.run(
                        ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', tmp],
                        capture_output=True,
                        timeout=30
                    )
                    played = result.returncode == 0
                
                # Method 2: mpg123
                if not played and shutil.which('mpg123'):
                    result = subprocess.run(
                        ['mpg123', '-q', tmp],
                        capture_output=True,
                        timeout=30
                    )
                    played = result.returncode == 0
                
                # Method 3: aplay with sox conversion
                if not played and shutil.which('sox') and shutil.which('aplay'):
                    wav_tmp = '/tmp/speech.wav'
                    subprocess.run(['sox', tmp, wav_tmp], 
                                 capture_output=True, 
                                 timeout=10)
                    subprocess.run(['aplay', '-q', wav_tmp], 
                                 capture_output=True, 
                                 timeout=30)
                
                # Cleanup
                try:
                    os.remove(tmp)
                    if os.path.exists('/tmp/speech.wav'):
                        os.remove('/tmp/speech.wav')
                except:
                    pass
                    
                return
                
            except Exception as e:
                print(f"gTTS error: {e}, falling back to espeak")
                # Fall through to espeak

        # Default: offline espeak (fast, low overhead)
        try:
            # Reduced speed from 130 to 120 for better clarity on low-quality speakers
            # Added voice variant for better quality
            # capture_output=True prevents terminal clutter
            subprocess.run(
                ['espeak', '-s', '120', '-v', 'en-us+f3', text],
                capture_output=True,
                timeout=30,
                check=False
            )
        except subprocess.TimeoutExpired:
            print(f"espeak timeout for text: {text[:50]}...")
        except FileNotFoundError:
            # Last-resort: print to console
            print(f'🔊 TTS: {text}')
        except Exception as e:
            print(f"Audio error: {e}")
    
    def announce_mode(self, mode: str):
        """
        Announce the current mode to the user.
        
        Args:
            mode: One of 'describe', 'ocr', 'face', 'search', or system message
        """
        announcements = {
            'describe': 'Describe mode activated.',
            'ocr': 'Text reading mode.',
            'face': 'Face recognition mode.',
            'search': 'Search mode.',
            'enroll': 'Face enrollment mode.',
            'shutdown': 'Shutting down. Goodbye.',
            'startup': 'Smart Vision Guide ready. Press a button to begin.',
            'listening': 'Listening. What should I search for?',
            'analyzing': 'Analyzing. Please wait.',
            'error': 'Sorry, an error occurred. Please try again.',
            'no_faces': 'No faces detected.',
            'enrolled': 'Face enrolled successfully.',
            'power_on': 'Starting Smart Vision Guide.',
            'power_off': 'Powering off.'
        }
        
        message = announcements.get(mode, f'{mode} mode.')
        self.say(message)
    
    def play_beep(self, beep_type='start'):
        """
        Play a simple beep sound for feedback.
        
        Args:
            beep_type: Type of beep ('start', 'success', 'error', 'click')
        """
        # Simple beep using speaker-test or paplay
        frequencies = {
            'start': 800,
            'success': 1000,
            'error': 400,
            'click': 600
        }
        
        freq = frequencies.get(beep_type, 800)
        
        try:
            # Try beep command if available
            if shutil.which('beep'):
                subprocess.run(
                    ['beep', '-f', str(freq), '-l', '100'],
                    capture_output=True,
                    timeout=2,
                    check=False
                )
            # Fallback: use speaker-test
            elif shutil.which('speaker-test'):
                subprocess.run(
                    ['speaker-test', '-t', 'sine', '-f', str(freq), '-l', '1'],
                    capture_output=True,
                    timeout=2,
                    check=False
                )
        except Exception:
            pass  # Silently fail if beep not available
    
    def get_bluetooth_sinks(self):
        """Get available PulseAudio Bluetooth sinks."""
        try:
            result = subprocess.run(
                ['pactl', 'list', 'short', 'sinks'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                sinks = []
                for line in result.stdout.split('\n'):
                    if 'bluez' in line.lower():
                        parts = line.split()
                        if parts:
                            sinks.append(parts[1])  # Sink name
                return sinks
            
        except Exception as e:
            print(f"Error getting Bluetooth sinks: {e}")
        
        return []
    
    def set_default_sink(self, sink_name):
        """Set default PulseAudio sink for Bluetooth routing."""
        try:
            subprocess.run(
                ['pactl', 'set-default-sink', sink_name],
                capture_output=True,
                timeout=5,
                check=True
            )
            print(f"✓ Set default audio sink to: {sink_name}")
            return True
        except Exception as e:
            print(f"Error setting default sink: {e}")
            return False
