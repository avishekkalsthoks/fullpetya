"""
Audio Handler for Smart Vision Guide
Optimized for Raspberry Pi Zero 2W with Bluetooth audio support and minimal overhead.
"""

import subprocess
import shutil
import os


class AudioHandler:
    """Handler for text-to-speech output with Pi Zero 2W optimizations."""
    
    # Mode announcement phrases
    MODE_SOUNDS = {
        'describe': 'describe_mode.wav',
        'ocr': 'ocr_mode.wav',
        'face': 'face_mode.wav',
        'search': 'search_mode.wav'
    }
    
    def __init__(self, backend='auto', use_bluetooth=True, rate=120, voice='en-us+f3'):
        """
        Initialize audio handler.
        
        Args:
            backend: TTS backend ('pico2wave', 'espeak-ng', 'espeak', 'gtts', or 'auto')
            use_bluetooth: Whether to route audio through Bluetooth (via PulseAudio)
            rate: TTS speaking rate
            voice: TTS voice (espeak/espeak-ng)
        """
        self.backend = backend
        self.use_bluetooth = use_bluetooth
        self.rate = rate
        self.voice = voice
        self.backend = self._resolve_backend(self.backend)
        self._test_audio_system()

    def _resolve_backend(self, backend: str) -> str:
        """Resolve 'auto' backend to best available local option."""
        if backend and backend != 'auto':
            return backend

        if shutil.which('pico2wave') and shutil.which('aplay'):
            return 'pico2wave'
        if shutil.which('espeak-ng'):
            return 'espeak-ng'
        if shutil.which('espeak'):
            return 'espeak'
        return 'gtts'

    def _test_audio_system(self):
        """Test audio system availability."""
        # Check if any offline TTS is available
        if not shutil.which('pico2wave') and not shutil.which('espeak-ng') and not shutil.which('espeak'):
            print("⚠️  Warning: No offline TTS engine found.")
        
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
                # Import gTTS lazily to avoid failing when gTTS isn't installed
                from gtts import gTTS
            except Exception as e:
                print(f"gTTS import error: {e}, falling back to espeak")
            else:
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

        # Offline TTS options
        if self.backend == 'pico2wave':
            if shutil.which('pico2wave') and shutil.which('aplay'):
                try:
                    tmp = '/tmp/speech_pico.wav'
                    subprocess.run(['pico2wave', '-w', tmp, '-l', 'en-US', text],
                                   capture_output=True, timeout=30, check=False)
                    subprocess.run(['aplay', '-q', tmp], capture_output=True, timeout=30, check=False)
                    try:
                        os.remove(tmp)
                    except Exception:
                        pass
                    return
                except Exception as e:
                    print(f"pico2wave error: {e}, falling back to espeak")

        # Default: offline espeak / espeak-ng
        engine = 'espeak-ng' if shutil.which('espeak-ng') else 'espeak'
        try:
            subprocess.run(
                [engine, '-s', str(self.rate), '-v', self.voice, text],
                capture_output=True,
                timeout=30,
                check=False
            )
        except subprocess.TimeoutExpired:
            print(f"{engine} timeout for text: {text[:50]}...")
        except FileNotFoundError:
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
    
    def switch_bluetooth_profile(self, mode='music'):
        """
        Switch Bluetooth profile to optimize for music (A2DP) or chat/mic (HSP/HFP).
        Dynamically detects available profiles to avoid errors.
        """
        try:
            # 1. Get full details of the Bluetooth card
            result = subprocess.run(['pactl', 'list', 'cards'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return False
            
            # 2. Find the Bluetooth card and its profiles
            cards_content = result.stdout.split('Card #')
            bt_card_content = None
            for card in cards_content:
                if 'bluez_card' in card:
                    bt_card_content = card
                    break
            
            if not bt_card_content:
                print("No Bluetooth card found to switch profile.")
                return False

            # Extract card name (e.g., bluez_card.XX_XX_XX_XX_XX_XX)
            import re
            name_match = re.search(r'Name: (bluez_card\.[^\n\s]+)', bt_card_content)
            if not name_match:
                return False
            card_full_name = name_match.group(1)

            # 3. List all available profiles
            profiles = []
            profile_section = False
            for line in bt_card_content.split('\n'):
                line = line.strip()
                if line.startswith('Profiles:'):
                    profile_section = True
                    continue
                if profile_section:
                    if line.startswith('Active Profile:'):
                        break
                    
                    # Profile line looks like: "a2dp_sink: High Fidelity Playback (A2DP Sink) (sinks: 1, sources: 0, priority: 40, available: yes)"
                    # We ONLY want profiles that are "available: yes" or "available: unknown"
                    match = re.match(r'^([^:]+):.*available: (yes|unknown)', line)
                    if match:
                        profiles.append(match.group(1))

            # 4. Pick best match for target mode
            target_profile = None
            if mode == 'music':
                # Prefer A2DP
                for p in profiles:
                    if 'a2dp' in p.lower():
                        target_profile = p
                        break
            else:
                # Prefer HSP/HFP (Handsfree/Headset)
                for p in profiles:
                    if any(x in p.lower() for x in ['hfp', 'hsp', 'headset', 'handsfree']):
                        target_profile = p
                        break
            
            if not target_profile:
                if mode == 'chat':
                    print("⚠️ Note: Headset does not seem to support a microphone profile (HSP/HFP).")
                else:
                    print(f"⚠️ No suitable profile found for {mode} mode.")
                return False

            # 5. Execute switch if not already active
            if f"Active Profile: {target_profile}" in bt_card_content:
                return True

            print(f"🔄 Switching Bluetooth profile to: {target_profile}")
            result = subprocess.run(['pactl', 'set-card-profile', card_full_name, target_profile], 
                                  capture_output=True, timeout=5)
            
            if result.returncode != 0:
                print(f"⚠️ Failed to switch to {target_profile}. Your headset might be in a mode that doesn't allow profile switching.")
                return False
                
            return True
            
        except Exception as e:
            print(f"Error switching Bluetooth profile: {e}")
            return False

    def get_audio_status(self):
        """
        Get detailed status of audio devices (Sinks and Sources).
        Useful for diagnosing Bluetooth input/output issues.
        """
        status = {
            'sinks': [],   # Outputs (Speakers/Headphones)
            'sources': []  # Inputs (Microphones)
        }
        
        try:
            # Check Sinks (Outputs)
            result = subprocess.run(['pactl', 'list', 'short', 'sinks'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line:
                        parts = line.split()
                        if len(parts) >= 2:
                            name = parts[1]
                            is_bt = 'bluez' in name.lower()
                            status['sinks'].append({'name': name, 'bluetooth': is_bt})
            
            # Check Sources (Inputs)
            result = subprocess.run(['pactl', 'list', 'short', 'sources'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line:
                        parts = line.split()
                        if len(parts) >= 2:
                            name = parts[1]
                            # Filter out monitor sources (they are just loopbacks of sinks)
                            if '.monitor' not in name.lower():
                                is_bt = 'bluez' in name.lower()
                                status['sources'].append({'name': name, 'bluetooth': is_bt})
                                
        except Exception as e:
            print(f"Error getting audio status: {e}")
            
        return status

    def set_default_sink(self, sink_name):
        """Set default PulseAudio sink for Bluetooth routing."""
        try:
            subprocess.run(
                ['pactl', 'set-default-sink', sink_name],
                capture_output=True,
                timeout=5,
                check=True
            )
            
            # Apply latency offset to improve stability for Bluetooth
            if 'bluez' in sink_name.lower():
                # 50ms offset often helps with stuttering
                subprocess.run(
                    ['pactl', 'set-port-latency-offset', sink_name, 'headset-output', '50000'],
                    capture_output=True,
                    timeout=2
                )
                
            print(f"✓ Set default audio sink to: {sink_name}")
            return True
        except Exception as e:
            print(f"Error setting default sink: {e}")
            return False

    def set_default_source(self, source_name):
        """Set default PulseAudio source for microphone routing."""
        try:
            subprocess.run(
                ['pactl', 'set-default-source', source_name],
                capture_output=True,
                timeout=5,
                check=True
            )
            print(f"✓ Set default audio source to: {source_name}")
            return True
        except Exception as e:
            print(f"Error setting default source: {e}")
            return False
