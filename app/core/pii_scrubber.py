"""PII Scrubber for Ethiopian Personal Identifiers.

Redacts phone numbers (+251 / 09 / 07), Bank Accounts, TINs, and Kebele IDs
to ensure zero customer personal data leaks into database storage or training exports.
"""
import re
from typing import Tuple

# Regex Patterns for Ethiopian Identifiers

# 1. Ethiopian Phone numbers:
# Covers +251 9... / +251 7... / 09... / 07... with optional spaces/dashes
ETH_PHONE_REGEX = re.compile(
    r'(?:\+251|00251|0)[\s\-]*(?:9|7)[0-9\s\-]{6,12}[0-9]',
    re.IGNORECASE
)

# 2. Ethiopian Tax Identification Number (TIN): 10 digits
# Often formatted as TIN: 1234567890 or 10-digit isolated sequence
TIN_REGEX = re.compile(
    r'(?:TIN[\s:#\-_]*|የግብር\s*መለያ\s*ቁጥር[\s:#\-_]*)(\d{10})|\b(100\d{7})\b',
    re.IGNORECASE
)

# 3. Kebele / National ID Card patterns
KEBELE_ID_REGEX = re.compile(
    r'(?:Kebele|KB|ID|ቀበሌ|መታወቂያ)[\s:#\-_]*[A-Za-z0-9\-/]{5,15}',
    re.IGNORECASE
)

# 4. Bank Account numbers: 8 to 16 continuous digits (often prefixed by Acc/Account/ሂሳብ)
BANK_ACCOUNT_REGEX = re.compile(
    r'(?:Account|Acc|A/C|ሂሳብ|የባንክ\s*ሂሳብ)[\s:#\-_]*(\d{8,16})|\b(1000\d{8,12})\b',
    re.IGNORECASE
)


def scrub_pii(text: str) -> str:
    """Scrub sensitive Ethiopian PII patterns from text.
    
    Args:
        text: Raw text containing potential personal identifiers.
        
    Returns:
        Redacted text with placeholders.
    """
    if not text:
        return ""

    scrubbed = text

    # Redact phone numbers
    scrubbed = ETH_PHONE_REGEX.sub('[REDACTED_PHONE]', scrubbed)

    # Redact Bank Accounts
    scrubbed = BANK_ACCOUNT_REGEX.sub('[REDACTED_ACCOUNT]', scrubbed)

    # Redact TINs
    scrubbed = TIN_REGEX.sub('[REDACTED_TIN]', scrubbed)

    # Redact Kebele / National IDs
    scrubbed = KEBELE_ID_REGEX.sub('[REDACTED_ID]', scrubbed)

    return scrubbed


def contains_pii(text: str) -> Tuple[bool, list[str]]:
    """Independent validator check used before training data export.
    
    Returns:
        (has_pii, list_of_detected_categories)
    """
    if not text:
        return False, []

    detected = []
    if ETH_PHONE_REGEX.search(text):
        detected.append("PHONE")
    if BANK_ACCOUNT_REGEX.search(text):
        detected.append("BANK_ACCOUNT")
    if TIN_REGEX.search(text):
        detected.append("TIN")
    if KEBELE_ID_REGEX.search(text):
        detected.append("KEBELE_ID")

    return (len(detected) > 0), detected
