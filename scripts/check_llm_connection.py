#!/usr/bin/env python3
"""LLM Connectivity & Grounding Diagnostic Tool.

Checks the active LLM provider configured in .env (Mock, Ollama, Gemini, OpenAI, Groq),
measures connection latency, and validates grounded Amharic generation.
"""
import sys
import os
import time
import asyncio

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.llm.router import llm_router
from app.core.guardrails import build_system_prompt

PASS = "\033[92m[PASSED]\033[0m"
FAIL = "\033[91m[FAILED]\033[0m"
INFO = "\033[94m[INFO]\033[0m"
WARN = "\033[93m[WARNING]\033[0m"


async def main():
    print("======================================================================")
    print("           InsurTech AI Assistant: LLM Connectivity Diagnostics       ")
    print("======================================================================")

    provider = settings.LLM_PROVIDER
    model = settings.LLM_MODEL
    base_url = settings.LLM_BASE_URL
    has_api_key = bool(settings.LLM_API_KEY)

    print(f"\nActive Configuration (.env):")
    print(f"  • LLM Provider : {provider}")
    print(f"  • Model Name   : {model}")
    print(f"  • Base URL     : {base_url}")
    print(f"  • API Key Set  : {'YES (' + settings.LLM_API_KEY[:6] + '...)' if has_api_key else 'NO'}")

    sample_context = [
        {
            "document_id": "MOTOR-TAR-2026",
            "section": "Section 4 - Third Party Liability",
            "content_text": (
                "የሞተር ተሽከርካሪ የሦስተኛ ወገን ኢንሹራንስ የካሳ ክፍያ ገደብ ለአካል ጉዳት 500,000 ብር ነው። "
                "የአደጋው ማስታወቂያ በ 48 ሰዓታት ውስጥ መቅረብ አለበት።"
            )
        }
    ]

    test_prompt = "የሦስተኛ ወገን ኢንሹራንስ የካሳ ገደብ ስንት ነው?"
    system_prompt = build_system_prompt(language="am")

    print(f"\n{INFO} Dispatching test query: '{test_prompt}'")
    t0 = time.perf_counter()

    try:
        reply = await llm_router.generate_response(
            prompt=test_prompt,
            context_chunks=sample_context,
            system_prompt=system_prompt
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000

        print(f"\n{PASS} Generation completed in {elapsed_ms:.2f}ms")
        print("\nGenerated Response:")
        print("-" * 50)
        print(reply)
        print("-" * 50)

        # Verification of mandatory disclaimer
        disclaimer = settings.AMHARIC_DISCLAIMER
        if disclaimer in reply:
            print(f"\n{PASS} Legal Disclaimer verified: Present and intact.")
        else:
            print(f"\n{WARN} Legal disclaimer was not detected in output.")

        # Citation verification
        if "MOTOR-TAR-2026" in reply or "500,000" in reply:
            print(f"{PASS} Factual Grounding verified: Policy citation/facts present.")

        print("\n" + "=" * 70)
        print(f"🎉 LLM Provider [{provider}] is operational and healthy!")
        print("======================================================================")

    except Exception as e:
        print(f"\n{FAIL} LLM Generation failed: {e}")
        print("\nTroubleshooting tips:")
        if provider in ["gemini", "openai", "groq", "openai_compatible"] and not has_api_key:
            print(f"  -> LLM_PROVIDER is set to '{provider}' but LLM_API_KEY is empty.")
            print("  -> Please add your API key in insuretech-ai/.env (e.g. LLM_API_KEY=AIzaSy...)")
        elif provider == "gemini":
            print("  -> Ensure your Gemini API Key is valid from Google AI Studio (https://aistudio.google.com/app/apikey).")
            print("  -> Ensure your network has outbound access to https://generativelanguage.googleapis.com")
        elif provider == "ollama":
            print(f"  -> Could not connect to Ollama at {base_url}.")
            print("  -> Ensure Ollama is running (`ollama serve`) or switch to `LLM_PROVIDER=mock`.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
