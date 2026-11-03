"""Ge'ez Homophone & Punctuation Normalizer.

Folds homophone character variations across Amharic orthography and standardizes
Ethiopic punctuation for reliable, deterministic retrieval and STT post-processing.
"""
import re
from typing import Dict

# Complete Unicode mapping dictionary for Ge'ez homophones
_HOMOPHONE_MAP: Dict[str, str] = {
    # ሐ / ኀ -> ሀ
    'ሐ': 'ሀ', 'ሑ': 'ሁ', 'ሒ': 'ሂ', 'ሓ': 'ሃ', 'ሔ': 'ሄ', 'ሕ': 'ህ', 'ሖ': 'ሆ', 'ሗ': 'ኋ',
    'ኀ': 'ሀ', 'ኁ': 'ሁ', 'ኂ': 'ሂ', 'ኃ': 'ሃ', 'ኄ': 'ሄ', 'ኅ': 'ህ', 'ኆ': 'ሆ',
    'ሇ': 'ሆ', 'ኇ': 'ሆ',
    # ሠ -> ሰ
    'ሠ': 'ሰ', 'ሡ': 'ሱ', 'ሢ': 'ሲ', 'ሣ': 'ሳ', 'ሤ': 'ሴ', 'ሥ': 'ስ', 'ሦ': 'ሶ', 'ሧ': 'ሷ',
    # ዐ -> አ
    'ዐ': 'አ', 'ዑ': 'ኡ', 'ዒ': 'ኢ', 'ዓ': 'ኣ', 'ዔ': 'ኤ', 'ዕ': 'እ', 'ዖ': 'ኦ',
    'ኧ': 'አ',
    # ፀ -> ጸ
    'ፀ': 'ጸ', 'ፁ': 'ጹ', 'ፂ': 'ጺ', 'ፃ': 'ጻ', 'ፄ': 'ጼ', 'ፅ': 'ጽ', 'ፆ': 'ጾ', 'ፇ': 'ጿ',
}

# Pre-compiled translation table for maximum speed (O(N) in C)
_TRANSLATION_TABLE = str.maketrans(_HOMOPHONE_MAP)

# Punctuation translation table
_PUNCTUATION_MAP = {
    '፡': ' ',   # Word space -> standard space
    '፣': ',',   # Ethiopic comma -> comma
    '።': '.',   # Ethiopic full stop -> period
    '፤': ';',   # Ethiopic semicolon
    '፥': ';',   # Ethiopic colon / semicolon
    '፦': ':',   # Ethiopic preface colon
    '፧': '?',   # Ethiopic question mark
    '፨': ' ',   # Ethiopic paragraph separator
}
_PUNCT_TABLE = str.maketrans(_PUNCTUATION_MAP)
_MULTISPACE_REGEX = re.compile(r'[ \t]+')
_MULTINEWLINE_REGEX = re.compile(r'\n{3,}')


def normalize_amharic(text: str) -> str:
    """Normalize Amharic text by folding homophones and standardizing punctuation.
    
    Args:
        text: Raw Amharic or mixed Amharic/English string.
        
    Returns:
        Canonicalized string with folded homophones and uniform punctuation.
    """
    if not text:
        return ""

    # Step 1: Character homophone translation via fast C-level table
    normalized = text.translate(_TRANSLATION_TABLE)

    # Step 2: Punctuation normalization
    normalized = normalized.translate(_PUNCT_TABLE)

    # Step 3: Collapse repeated spaces while preserving intentional newlines
    normalized = _MULTISPACE_REGEX.sub(' ', normalized)
    normalized = _MULTINEWLINE_REGEX.sub('\n\n', normalized)

    return normalized.strip()


def normalize(text: str) -> str:
    """Canonical alias for text normalization."""
    return normalize_amharic(text)
