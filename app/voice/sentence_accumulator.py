"""Sentence Accumulator for Real-Time Streaming Audio.

Buffers incoming token streams from the LLM and yields complete sentences
as early as possible on Ethiopic (።, ፣) and Latin (. , ! ?) punctuation marks,
enabling Time-to-First-Audio (TTFA) < 2.5s.
"""
import re
from typing import AsyncGenerator, List

# Sentence delimiter regex including Ge'ez punctuation:
# ። (Ethiopic full stop), ፣ (Ethiopic comma), ፤ (Ethiopic semicolon), ., !, ?, \n
_SENTENCE_BOUNDARY_REGEX = re.compile(r'([.!?።፤\n]+)')


class SentenceAccumulator:
    """Accumulates token chunks and yields complete sentences for pipelined TTS."""

    def __init__(self, min_words_per_sentence: int = 3):
        self.buffer = ""
        self.min_words = min_words_per_sentence

    def push_token(self, token: str) -> List[str]:
        """Push a token into the accumulator and return any completed sentences."""
        self.buffer += token
        sentences = []

        parts = _SENTENCE_BOUNDARY_REGEX.split(self.buffer)
        # parts will look like: [sentence1, delimiter1, sentence2, delimiter2, remainder]
        if len(parts) > 2:
            # We have at least one complete sentence + delimiter pair
            i = 0
            while i < len(parts) - 1:
                sentence_part = parts[i].strip()
                delimiter = parts[i + 1]
                complete = f"{sentence_part}{delimiter}".strip()
                
                # Check word count to avoid stuttering on isolated initials
                if len(complete.split()) >= self.min_words or any(p in complete for p in ['።', '.', '!']):
                    sentences.append(complete)
                else:
                    # Keep accumulating if too short
                    if sentences:
                        sentences[-1] += f" {complete}"
                    else:
                        parts[i+2] = f"{complete} {parts[i+2]}" if i + 2 < len(parts) else complete
                i += 2

            # Remaining uncompleted part
            self.buffer = parts[-1]

        return sentences

    def flush(self) -> List[str]:
        """Flush any remaining buffered text as the final sentence."""
        remaining = self.buffer.strip()
        self.buffer = ""
        if remaining:
            return [remaining]
        return []
