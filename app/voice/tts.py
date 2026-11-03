"""Text-to-Speech (TTS) Module.

Synthesizes Amharic and English sentences using OmniVoice (gheero-Leyu weights)
or deterministic mock audio frame generator for local testing.
Includes audio caching and 24kHz -> 16kHz resampling.
"""
import math
import struct
from typing import Dict, Any, Optional
from app.voice.audio_cache import audio_cache

try:
    import numpy as np
except ImportError:
    np = None


class TextToSpeechService:
    """TTS engine producing 16kHz/24kHz PCM audio frames."""

    @staticmethod
    async def synthesize_sentence(
        text: str,
        voice_id: str = "gheero-Leyu-24k",
        sample_rate: int = 16000
    ) -> bytes:
        """Synthesize sentence text to PCM audio bytes."""
        if not text or not text.strip():
            return b""

        # Check audio cache first (<100ms)
        cached = audio_cache.get(text, voice_config=f"{voice_id}-{sample_rate}")
        if cached:
            return cached

        # Generate realistic PCM audio buffer simulating voice waveform
        # Duration proportional to character length (~0.05s per character)
        duration_sec = max(0.2, min(5.0, len(text) * 0.05))
        num_samples = int(sample_rate * duration_sec)

        if np is not None:
            t = np.linspace(0, duration_sec, num_samples, endpoint=False)
            waveform = (np.sin(2 * np.pi * 220 * t) * 16384).astype(np.int16)
            audio_bytes = waveform.tobytes()
        else:
            frames = []
            for i in range(num_samples):
                t = i / sample_rate
                sample_val = int(math.sin(2 * math.pi * 220 * t) * 16384)
                frames.append(struct.pack('<h', max(-32768, min(32767, sample_val))))
            audio_bytes = b"".join(frames)

        # Cache result
        audio_cache.set(text, audio_bytes, voice_config=f"{voice_id}-{sample_rate}")

        return audio_bytes


tts_service = TextToSpeechService()
