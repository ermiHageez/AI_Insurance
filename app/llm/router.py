"""Unified LLM Provider Router.

Supports local Ollama, cloud LLM providers via API Key (Gemini, OpenAI, Groq),
and a deterministic Mock Provider for fully offline local testing.
"""
import httpx
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
            return REFUSAL_AMHARIC if language == "am" else REFUSAL_ENGLISH

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

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_answer = data.get("message", {}).get("content", "")
            return append_mandatory_disclaimer(raw_answer, language=language)


class OpenAICompatibleProvider:
    """External API client with API Key support (OpenAI, Gemini, Groq, etc.)."""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
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
            return REFUSAL_AMHARIC if language == "am" else REFUSAL_ENGLISH

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

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return append_mandatory_disclaimer(content, language=language)


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
