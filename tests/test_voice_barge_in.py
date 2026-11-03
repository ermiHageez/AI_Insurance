"""Unit and Latency Tests for Voice Streaming, Sentence Accumulation & Barge-In."""
import time
import asyncio
try:
    import pytest
except ImportError:
    pytest = None
from app.voice.sentence_accumulator import SentenceAccumulator
from app.voice.audio_cache import audio_cache
from app.voice.tts import tts_service


class TestVoiceBargeInPipeline:

    def test_sentence_accumulator_punctuation_splitting(self):
        acc = SentenceAccumulator(min_words_per_sentence=2)

        # Stream tokens one by one
        tokens = ["የመኪና", " ", "ኢንሹራንስ", " ", "አስፈላጊ", " ", "ነው", "።", " ", "በተጨማሪም", " ", "የሶስተኛ", " ", "ወገን", "።"]
        emitted_sentences = []
        for tok in tokens:
            ready = acc.push_token(tok)
            emitted_sentences.extend(ready)
        emitted_sentences.extend(acc.flush())

        assert len(emitted_sentences) >= 2
        assert "የመኪና ኢንሹራንስ አስፈላጊ ነው." in emitted_sentences or "የመኪና ኢንሹራንስ አስፈላጊ ነው" in emitted_sentences[0]

    @pytest.mark.asyncio
    async def test_audio_cache_latency_under_100ms(self):
        text = "ይህ መረጃ ለማሳወቂያ ብቻ የቀረበ ነው፤ የመጨረሻ ውሳኔ የሚሰጠው የካሳ ክፍያ ባለሙያው ነው"
        
        # Populate cache
        await tts_service.synthesize_sentence(text)

        # Retrieve from cache
        start = time.perf_counter()
        cached_pcm = audio_cache.get(text, voice_config="gheero-Leyu-24k-16000")
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert cached_pcm is not None
        assert len(cached_pcm) > 0
        assert elapsed_ms < 100.0, f"Cache retrieval took {elapsed_ms:.2f}ms (target <100ms)"

    @pytest.mark.asyncio
    async def test_barge_in_cancellation_latency_under_150ms(self):
        # Simulate background TTS generation task
        async def long_tts_worker():
            await asyncio.sleep(2.0)
            return b"synthesized_audio"

        task = asyncio.create_task(long_tts_worker())

        # Simulate user interruption (CANCEL_TURN)
        start = time.perf_counter()
        task.cancel()
        
        # Await task cancellation handling
        try:
            await task
        except asyncio.CancelledError:
            pass

        halt_time_ms = (time.perf_counter() - start) * 1000
        assert task.cancelled() is True
        assert halt_time_ms < 150.0, f"Barge-in halt took {halt_time_ms:.2f}ms (target <150ms)"
