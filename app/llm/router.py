"""Unified LLM Provider Router.

Supports local Ollama, cloud LLM providers via API Key (Gemini, OpenAI, Groq),
and a deterministic Mock Provider for fully offline local testing and reliable fallback.
"""
import httpx
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional
from app.core.config import settings
from app.core.guardrails import (
    is_prompt_injection,
    append_mandatory_disclaimer,
    REFUSAL_AMHARIC,
    REFUSAL_ENGLISH,
    INJECTION_REFUSAL_AMHARIC,
    INJECTION_REFUSAL_ENGLISH,
    is_amharic_query,
)

logger = logging.getLogger("llm.router")


class MockLLMProvider:
    """Deterministic mock provider for rapid offline local verification."""

    async def generate(
        self,
        prompt: str,
        context_chunks: List[Dict[str, Any]],
        system_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        language: str = "am"
    ) -> str:
        # 1. Injection Defense
        if is_prompt_injection(prompt):
            return INJECTION_REFUSAL_AMHARIC if language == "am" else INJECTION_REFUSAL_ENGLISH

        # 2. No Context Refusal
        if not context_chunks:
            refusal = REFUSAL_AMHARIC if language == "am" else REFUSAL_ENGLISH
            return append_mandatory_disclaimer(refusal, language=language)

        # 3. Grounded response formulation citing document
        top_chunk = context_chunks[0]
        doc_id = top_chunk.get("document_id", "Policy-Document")
        section = top_chunk.get("section", "Section 1")
        content = top_chunk.get("content_text", "")

        # Extract first 2 relevant sentences from chunk
        sentences = [s.strip() for s in content.replace('\n', ' ').split('.') if s.strip()]
        snippet = ". ".join(sentences[:2]) if sentences else content[:200]

        if language == "am":
            body = (
                f"በተጠቀሰው የፖሊሲ ሰነድ [{doc_id}፣ {section}] መሰረት፡ {snippet}። "
                f"ተጨማሪ ማብራሪያ ከፈለጉ እባክዎን ይጠይቁ።"
            )
        else:
            body = (
                f"According to the policy document [{doc_id}, {section}]: {snippet}. "
                f"Please let me know if you need further clarification."
            )

        return append_mandatory_disclaimer(body, language=language)

    async def stream_tokens(
        self,
        full_text: str
    ) -> AsyncGenerator[str, None]:
        """Stream response word-by-word with punctuation markers."""
        words = full_text.split(" ")
        for i, word in enumerate(words):
            token = word + (" " if i < len(words) - 1 else "")
            yield token


class OllamaProvider:
    """Local Ollama client."""

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate(
        self,
        prompt: str,
        context_chunks: List[Dict[str, Any]],
        system_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        language: str = "am"
    ) -> str:
        if is_prompt_injection(prompt):
            return INJECTION_REFUSAL_AMHARIC if language == "am" else INJECTION_REFUSAL_ENGLISH

        if not context_chunks:
            refusal = REFUSAL_AMHARIC if language == "am" else REFUSAL_ENGLISH
            return append_mandatory_disclaimer(refusal, language=language)

        # Grounding context block
        context_text = "\n\n".join([
            f"[Source: {c.get('document_id', 'doc')} | Section: {c.get('section', '')}]\n{c.get('content_text', '')}"
            for c in context_chunks
        ])

        messages = [{"role": "system", "content": f"{system_prompt}\n\nDOCUMENT CONTEXT:\n{context_text}"}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": settings.LLM_TEMPERATURE}
        }

        try:
            # Check if base_url is full Ollama API (native /api/chat) or OpenAI-compatible (/v1)
            target_endpoint = (
                f"{self.base_url}/chat/completions"
                if "/v1" in self.base_url else
                f"{self.base_url}/api/chat"
            )

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(target_endpoint, json=payload)
                resp.raise_for_status()
                data = resp.json()
                
                # Check format (Ollama native vs OpenAI-compatible)
                if "message" in data:
                    raw_answer = data["message"].get("content", "")
                elif "choices" in data and len(data["choices"]) > 0:
                    raw_answer = data["choices"][0]["message"].get("content", "")
                else:
                    raw_answer = str(data)

                return append_mandatory_disclaimer(raw_answer, language=language)

        except Exception as e:
            logger.warning(f"Ollama inference error: {e}. Falling back to grounded mock.")
            fallback = MockLLMProvider()
            return await fallback.generate(prompt, context_chunks, system_prompt, history, language)


class OpenAICompatibleProvider:
    """External API client with API Key support (OpenAI, Gemini, Groq, etc.)."""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def _resolve_endpoint(self) -> str:
        """Resolve full chat completions URL."""
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    async def generate(
        self,
        prompt: str,
        context_chunks: List[Dict[str, Any]],
        system_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        language: str = "am"
    ) -> str:
        if is_prompt_injection(prompt):
            return INJECTION_REFUSAL_AMHARIC if language == "am" else INJECTION_REFUSAL_ENGLISH

        if not context_chunks:
            refusal = REFUSAL_AMHARIC if language == "am" else REFUSAL_ENGLISH
            return append_mandatory_disclaimer(refusal, language=language)

        context_text = "\n\n".join([
            f"[Source: {c.get('document_id', 'doc')} | Section: {c.get('section', '')}]\n{c.get('content_text', '')}"
            for c in context_chunks
        ])

        messages = [{"role": "system", "content": f"{system_prompt}\n\nDOCUMENT CONTEXT:\n{context_text}"}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": settings.LLM_TEMPERATURE
        }

        endpoint = self._resolve_endpoint()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(endpoint, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return append_mandatory_disclaimer(content, language=language)
        except Exception as e:
            logger.warning(f"OpenAI-compatible LLM error: {e}. Falling back to grounded mock.")
            fallback = MockLLMProvider()
            return await fallback.generate(prompt, context_chunks, system_prompt, history, language)


class LLMRouter:
    """Top-level LLM router delegating to configured provider."""

    def __init__(self):
        self._mock = MockLLMProvider()

    def get_provider(self):
        if settings.LLM_PROVIDER == "openai_compatible" and settings.LLM_API_KEY:
            return OpenAICompatibleProvider(
                base_url=settings.LLM_BASE_URL,
                api_key=settings.LLM_API_KEY,
                model=settings.LLM_MODEL
            )
        elif settings.LLM_PROVIDER == "ollama":
            return OllamaProvider(
                base_url=settings.LLM_BASE_URL,
                model=settings.LLM_MODEL
            )
        return self._mock

    async def generate_response(
        self,
        prompt: str,
        context_chunks: List[Dict[str, Any]],
        system_prompt: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        lang = "am" if is_amharic_query(prompt) else "en"
        provider = self.get_provider()
        return await provider.generate(
            prompt=prompt,
            context_chunks=context_chunks,
            system_prompt=system_prompt,
            history=history,
            language=lang
        )


llm_router = LLMRouter()
