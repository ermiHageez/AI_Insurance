"""Audio Cache for Pre-Synthesized Insurance Responses.

Caches synthesized audio bytes in Redis / in-memory by SHA-256 hash
of normalized text, returning repeated answers (disclaimers, greetings) in <100ms.
"""
import hashlib
import time
from typing import Optional, Dict, Tuple
from app.rag.normalizer import normalize

# In-memory fallback cache: hash -> (bytes, timestamp)
_MEMORY_AUDIO_CACHE: Dict[str, Tuple[bytes, float]] = {}


def generate_audio_cache_key(text: str, voice_config: str = "gheero-Leyu-24k") -> str:
    """Generate deterministic SHA-256 key from normalized text and voice parameters."""
    norm = normalize(text)
    combined = f"{norm}:{voice_config}"
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()


class AudioCache:
    """Cache client for synthesized voice chunks."""

    def __init__(self, ttl_seconds: int = 7 * 86400):
        self.ttl = ttl_seconds

    def get(self, text: str, voice_config: str = "gheero-Leyu-24k") -> Optional[bytes]:
        """Retrieve cached audio bytes if available and not expired."""
        key = generate_audio_cache_key(text, voice_config)
        if key in _MEMORY_AUDIO_CACHE:
            data, timestamp = _MEMORY_AUDIO_CACHE[key]
            if time.time() - timestamp < self.ttl:
                return data
            else:
                _MEMORY_AUDIO_CACHE.pop(key, None)
        return None

    def set(self, text: str, audio_bytes: bytes, voice_config: str = "gheero-Leyu-24k"):
        """Store synthesized audio bytes into cache."""
        key = generate_audio_cache_key(text, voice_config)
        _MEMORY_AUDIO_CACHE[key] = (audio_bytes, time.time())

    def clear(self):
        _MEMORY_AUDIO_CACHE.clear()


audio_cache = AudioCache()
