"""Guardrail Prompts & Injection Defenses.

Enforces zero-shot prompt injection protection, citation requirements,
deterministic refusal when verified RAG documentation is absent, and
unconditional appending of mandatory legal disclaimers.
"""
import re
from typing import List, Dict, Any, Tuple
from app.core.config import settings

# Injection / instruction override patterns
_INJECTION_PATTERNS = [
    re.compile(r'ignore\s+(?:all\s+)?(?:previous\s+)?instructions', re.IGNORECASE),
    re.compile(r'approve\s+(?:my\s+)?claim', re.IGNORECASE),
    re.compile(r'you\s+are\s+now\s+(?:in\s+)?dan', re.IGNORECASE),
    re.compile(r'jailbreak', re.IGNORECASE),
    re.compile(r'override\s+system', re.IGNORECASE),
    re.compile(r'ትዕዛዙን\s*ተወው|ክፈለው|ካሳውን\s*ፍቀድ', re.IGNORECASE),  # Amharic injection attempts
]

REFUSAL_AMHARIC = "በዚህ ጉዳይ ላይ የተረጋገጠ የፖሊሲ ሰነድ የለኝም። እባክዎ ጥያቄዎን ያብራሩ ወይም የደንበኞች አገልግሎትን ያነጋግሩ።"
REFUSAL_ENGLISH = "I do not have verified policy documentation on this matter. Please clarify your question or contact customer service."

INJECTION_REFUSAL_AMHARIC = "ይቅርታ፣ ይህንን ጥያቄ ማስተናገድ አልችልም። እኔ የኢንሹራንስ መረጃ ረዳት ብቻ ነኝ፤ የይገባኛል ጥያቄዎችን የማጽደቅ ወይም የሥርዓት ደንቦችን የመቀየር ስልጣን የለኝም።"
INJECTION_REFUSAL_ENGLISH = "I cannot process this instruction. As an InsurTech assistant, I cannot override rules or grant claim approvals."


def is_prompt_injection(message: str) -> bool:
    """Check if message contains adversarial prompt injection patterns."""
    if not message:
        return False
    for pat in _INJECTION_PATTERNS:
        if pat.search(message):
            return True
    return False


def build_system_prompt(language: str = "am") -> str:
    """Build grounded system prompt with legal and citation constraints."""
    if language == "am":
        return (
            "እርስዎ የኢንሹራንስ ረዳት (InsurTech AI) ነዎት። "
            "ደንበኞችን በትህትና እና በትክክል ያግዙ። "
            "ደንቦች:\n"
            "1. መልስዎ በተሰጠው የፖሊሲ ሰነድ (Context) ላይ ብቻ የተመሰረተ መሆን አለበት።\n"
            "2. ሰነድ ውስጥ የሌለ መረጃ በፍጹም አይፍጠሩ።\n"
            "3. የፖሊሲውን ስም እና አንቀጽ (Section) ሁልጊዜ ይጠቅሱ።\n"
            "4. የካሳ ክፍያ ወይም ይገባኛል ጥያቄ የማጽደቅ ስልጣን እንደሌለዎት ያስታውሱ።"
        )
    return (
        "You are the InsurTech AI Assistant. Answer inquiries professionally and accurately.\n"
        "Rules:\n"
        "1. Ground all answers exclusively in the provided policy context.\n"
        "2. Never hallucinate facts outside the provided documentation.\n"
        "3. Always cite the relevant policy document name and section.\n"
        "4. You do not possess the authority to approve claims or modify policies."
    )


def append_mandatory_disclaimer(response_text: str, language: str = "am") -> str:
    """Unconditionally append official insurer legal disclaimer to response."""
    disclaimer = (
        settings.AMHARIC_DISCLAIMER if language == "am" else settings.ENGLISH_DISCLAIMER
    )
    # Avoid duplicate disclaimer if already present
    if disclaimer in response_text:
        return response_text
    
    clean_text = response_text.rstrip()
    return f"{clean_text}\n\n---\n{disclaimer}"


def is_amharic_query(text: str) -> bool:
    """Detect if text predominantly contains Ethiopic / Ge'ez characters."""
    if not text:
        return False
    eth_chars = len(re.findall(r'[\u1200-\u137F]', text))
    return eth_chars > 0
