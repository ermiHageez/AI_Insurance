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

        # Find the most relevant sentence or table entry matching prompt keywords
        import re
        prompt_words = [w.strip() for w in re.split(r'[\s\?፣።\.\,\:]+', prompt.lower()) if len(w.strip()) > 1]
        lines = [l.strip() for l in content.split('\n') if l.strip()]

        candidates = []
        for line in lines:
            if len(line) > 8:
                candidates.append(line)

        # Table row reconstruction: combine 2-4 consecutive short table cell lines
        for i in range(len(lines)):
            for window_size in (2, 3, 4):
                if i + window_size <= len(lines):
                    chunk_slice = lines[i:i+window_size]
                    if all(len(c) < 50 for c in chunk_slice):
                        candidates.append(" ".join(chunk_slice))

        best_candidate = ""
        best_score = -1
        for cand in candidates:
            cand_lower = cand.lower()
            score = sum(1 for w in prompt_words if w in cand_lower)
            # Give priority boost to candidates that answer with numbers / amounts
            if any(char.isdigit() for char in cand):
                score += 1.5
            if score > best_score:
                best_score = score
                best_candidate = cand

        # If a specific match was found, use it directly for a straightforward answer
        if best_candidate and best_score > 0:
            snippet = best_candidate
        else:
            snippet = lines[0] if lines else content[:150]

        if language == "am":
            body = (
                f"በተጠቀሰው የፖሊሲ ሰነድ [{doc_id}] መሰረት፡ {snippet}። "
                f"ተጨማሪ ማብራሪያ ከፈለጉ እባክዎን ይጠይቁ።"
            )
        else:
            body = (
                f"According to the policy document [{doc_id}]: {snippet}. "
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


class GeminiProvider:
    """Official Google Gemini client supporting AI Studio keys."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key.strip()
        self.model = model or "gemini-1.5-flash"

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

        # 1. Try Google AI Studio Native Endpoint: /models/{model}:generateContent?key=...
        url_native = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        native_body = (
            f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\n"
            f"DOCUMENT CONTEXT:\n{context_text}\n\n"
            f"USER QUERY: {prompt}"
        )
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url_native,
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": native_body}]}],
                        "generationConfig": {"temperature": settings.LLM_TEMPERATURE}
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "parts" in candidates[0].get("content", {}):
                        content = candidates[0]["content"]["parts"][0].get("text", "")
                        return append_mandatory_disclaimer(content, language=language)
        except Exception as e:
            logger.warning(f"Gemini native endpoint error: {e}")

        # 2. Try OpenAI-Compatible Endpoint: /openai/chat/completions
        url_openai = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        headers_openai = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        messages = [{"role": "system", "content": f"{system_prompt}\n\nDOCUMENT CONTEXT:\n{context_text}"}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url_openai,
                    headers=headers_openai,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": settings.LLM_TEMPERATURE
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return append_mandatory_disclaimer(content, language=language)
        except Exception as e:
            logger.warning(f"Gemini OpenAI-compatible endpoint error: {e}")

        # Fallback to deterministic mock if network/quota fails
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
        provider_name = settings.LLM_PROVIDER.lower()
        if provider_name == "gemini" and settings.LLM_API_KEY:
            model = (
                settings.LLM_MODEL
                if settings.LLM_MODEL and settings.LLM_MODEL != "qwen2.5:3b"
                else "gemini-1.5-flash"
            )
            return GeminiProvider(
                api_key=settings.LLM_API_KEY,
                model=model
            )
        elif provider_name == "openai" and settings.LLM_API_KEY:
            base_url = (
                settings.LLM_BASE_URL
                if settings.LLM_BASE_URL and "localhost" not in settings.LLM_BASE_URL
                else "https://api.openai.com/v1"
            )
            model = (
                settings.LLM_MODEL
                if settings.LLM_MODEL and settings.LLM_MODEL != "qwen2.5:3b"
                else "gpt-4o-mini"
            )
            return OpenAICompatibleProvider(
                base_url=base_url,
                api_key=settings.LLM_API_KEY,
                model=model
            )
        elif provider_name == "groq" and settings.LLM_API_KEY:
            base_url = (
                settings.LLM_BASE_URL
                if settings.LLM_BASE_URL and "localhost" not in settings.LLM_BASE_URL
                else "https://api.groq.com/openai/v1"
            )
            model = (
                settings.LLM_MODEL
                if settings.LLM_MODEL and settings.LLM_MODEL != "qwen2.5:3b"
                else "llama-3.3-70b-versatile"
            )
            return OpenAICompatibleProvider(
                base_url=base_url,
                api_key=settings.LLM_API_KEY,
                model=model
            )
        elif provider_name == "openai_compatible" and settings.LLM_API_KEY:
            return OpenAICompatibleProvider(
                base_url=settings.LLM_BASE_URL,
                api_key=settings.LLM_API_KEY,
                model=settings.LLM_MODEL
            )
        elif provider_name == "ollama":
            return OllamaProvider(
                base_url=settings.LLM_BASE_URL,
                model=settings.LLM_MODEL
            )
        return self._mock

    def get_provider_info(self) -> Dict[str, Any]:
        """Return metadata about the active provider and model."""
        provider_name = settings.LLM_PROVIDER.lower()
        if provider_name == "gemini" and settings.LLM_API_KEY:
            model = (
                settings.LLM_MODEL
                if settings.LLM_MODEL and settings.LLM_MODEL != "qwen2.5:3b"
                else "gemini-1.5-flash"
            )
            return {"provider": "gemini", "model": model, "is_mock": False}
        elif provider_name == "openai" and settings.LLM_API_KEY:
            model = (
                settings.LLM_MODEL
                if settings.LLM_MODEL and settings.LLM_MODEL != "qwen2.5:3b"
                else "gpt-4o-mini"
            )
            return {"provider": "openai", "model": model, "is_mock": False}
        elif provider_name == "groq" and settings.LLM_API_KEY:
            model = (
                settings.LLM_MODEL
                if settings.LLM_MODEL and settings.LLM_MODEL != "qwen2.5:3b"
                else "llama-3.3-70b-versatile"
            )
            return {"provider": "groq", "model": model, "is_mock": False}
        elif provider_name == "ollama":
            return {"provider": "ollama", "model": settings.LLM_MODEL, "is_mock": False}
        return {"provider": "mock", "model": "deterministic-mock", "is_mock": True}

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
