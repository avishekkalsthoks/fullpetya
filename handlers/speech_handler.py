"""
Speech Handler for Smart Vision Guide
Captures short audio and performs offline speech-to-text (Vosk).
Designed to be lightweight for Pi Zero 2W.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import wave
from typing import Optional

from config import (
    STT_BACKEND,
    VOSK_MODEL_PATH,
    VOICE_INPUT_SECONDS,
    VOICE_INPUT_SAMPLE_RATE
)


class SpeechHandler:
    def __init__(self, audio_handler=None):
        self.audio_handler = audio_handler
        self.backend = STT_BACKEND.lower()
        self.vosk_model = None
        self._init_vosk()

    def _init_vosk(self) -> None:
        if self.backend not in ("vosk", "auto"):
            return
        try:
            import vosk  # type: ignore
        except Exception as e:
            print(f"WARN: Vosk not available: {e}")
            return

        if not os.path.isdir(VOSK_MODEL_PATH):
            print(f"WARN: Vosk model not found: {VOSK_MODEL_PATH}")
            return

        try:
            self.vosk_model = vosk.Model(VOSK_MODEL_PATH)
            self.vosk_module = vosk
            print("OK: Vosk STT initialized")
        except Exception as e:
            print(f"WARN: Failed to load Vosk model: {e}")
            self.vosk_model = None

    def _record_wav(self, seconds: float, sample_rate: int) -> Optional[str]:
        """Record audio to a temp WAV file using arecord."""
        if not shutil.which("arecord"):
            print("WARN: arecord not available for microphone capture")
            return None

        # Use temp WAV file
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)

        # Try to set Bluetooth mic as default if available
        if self.audio_handler:
            try:
                sources = self.audio_handler.get_audio_status().get("sources", [])
                bt_sources = [s["name"] for s in sources if s.get("bluetooth")]
                if bt_sources:
                    self.audio_handler.set_default_source(bt_sources[0])
            except Exception:
                pass

        cmd = [
            "arecord",
            "-q",
            "-d", str(int(seconds)),
            "-f", "S16_LE",
            "-r", str(int(sample_rate)),
            "-c", "1",
            path
        ]

        try:
            subprocess.run(cmd, check=True, timeout=seconds + 2)
            return path
        except Exception as e:
            print(f"WARN: Audio record failed: {e}")
            try:
                os.remove(path)
            except Exception:
                pass
            return None

    def _transcribe_vosk(self, wav_path: str) -> Optional[str]:
        """Transcribe WAV with Vosk."""
        if self.vosk_model is None:
            return None

        wf = wave.open(wav_path, "rb")
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
            # Vosk expects mono 16-bit PCM
            wf.close()
            return None

        rec = self.vosk_module.KaldiRecognizer(self.vosk_model, wf.getframerate())
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            rec.AcceptWaveform(data)

        wf.close()
        result = json.loads(rec.FinalResult())
        text = result.get("text", "").strip()
        return text or None

    def listen(self) -> Optional[str]:
        """Record audio and return transcribed text."""
        if self.backend not in ("vosk", "auto"):
            return None

        wav_path = self._record_wav(VOICE_INPUT_SECONDS, VOICE_INPUT_SAMPLE_RATE)
        if not wav_path:
            return None

        try:
            text = self._transcribe_vosk(wav_path)
            return text
        finally:
            try:
                os.remove(wav_path)
            except Exception:
                pass
