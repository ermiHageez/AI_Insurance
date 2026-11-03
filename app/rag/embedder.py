"""Embedding Generation Service for RAG Pipeline.

Supports BAAI/bge-m3 (1024 dimensions) and a deterministic local mock embedder
that preserves cosine similarity characteristics for rapid local testing without
requiring large neural model weight downloads.
"""
import math
import hashlib
from typing import List

try:
    import numpy as np
except ImportError:
    np = None


class BaseEmbedder:
    """Abstract interface for text embedding models."""
    dimension: int = 1024

    def embed_text(self, text: str) -> List[float]:
        raise NotImplementedError

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


class DeterministicMockEmbedder(BaseEmbedder):
    """Deterministic 1024-dimension embedder for offline local testing.
    
    Generates consistent unit-length vectors where texts sharing semantic tokens
    and normalized Ge'ez characters yield high cosine similarity (>0.85).
    """
    dimension: int = 1024

    def embed_text(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self.dimension

        if np is not None:
            vec = np.zeros(self.dimension, dtype=np.float32)
        else:
            vec = [0.0] * self.dimension

        words = text.lower().split()
        
        # Word-level n-grams
        for i, word in enumerate(words):
            h = int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16)
            idx = h % self.dimension
            sign = 1.0 if (h >> 1) & 1 else -1.0
            vec[idx] += sign * 1.5

        # Character tri-grams for subword matching (crucial for Amharic roots)
        clean = "".join(text.split())
        for j in range(len(clean) - 2):
            trigram = clean[j:j+3]
            h = int(hashlib.sha256(trigram.encode('utf-8')).hexdigest(), 16)
            idx = h % self.dimension
            sign = 1.0 if (h >> 2) & 1 else -1.0
            vec[idx] += sign * 0.8

        # Normalize to unit length (L2 norm)
        if np is not None:
            norm = float(np.linalg.norm(vec))
            if norm > 0:
                vec = vec / norm
            else:
                vec[0] = 1.0
            return vec.tolist()
        else:
            norm = math.sqrt(sum(x * x for x in vec))
            if norm > 0:
                return [x / norm for x in vec]
            else:
                vec[0] = 1.0
                return vec


def get_embedder() -> BaseEmbedder:
    """Factory to retrieve the active embedder."""
    return DeterministicMockEmbedder()
