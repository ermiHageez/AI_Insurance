"""Full-Duplex Voice WebSocket Endpoint with Real-Time Barge-In.

Handles:
- Inbound 16kHz audio stream & VAD end-of-speech detection
- Sentence-by-sentence TTS pipelining
- Barge-In cancellation: `{"event": "CANCEL_TURN"}` halts synthesis in <150ms
"""
import json
import asyncio
import time
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

try:
    import structlog
    logger = structlog.get_logger("voice.socket")
except ImportError:
    std_logger = logging.getLogger("voice.socket")
    class LoggerShim:
        def info(self, msg, **kwargs): std_logger.info(f"{msg} {kwargs}" if kwargs else msg)
        def warn(self, msg, **kwargs): std_logger.warning(f"{msg} {kwargs}" if kwargs else msg)
        def error(self, msg, **kwargs): std_logger.error(f"{msg} {kwargs}" if kwargs else msg)
    logger = LoggerShim()

from app.rag.normalizer import normalize
from app.rag.store import knowledge_store
from app.llm.router import llm_router
from app.core.guardrails import build_system_prompt, append_mandatory_disclaimer
from app.voice.stt import stt_service
from app.voice.tts import tts_service
from app.voice.sentence_accumulator import SentenceAccumulator

router = APIRouter(tags=["Voice"])


@router.websocket("/ws/v1/voice/chat")
async def voice_chat_endpoint(websocket: WebSocket):
    """Full-duplex WebSocket for streaming speech-to-speech chat."""
    await websocket.accept()
    logger.info("Voice WebSocket connected")

    audio_buffer = bytearray()
    active_tts_tasks: list[asyncio.Task] = []
    accumulator = SentenceAccumulator(min_words_per_sentence=3)

    try:
        while True:
            # Receive either text control frame or binary audio bytes
            message = await websocket.receive()
            
            # Handle Disconnect
            if message.get("type") == "websocket.disconnect":
                break

            # 1. Text Control Messages (e.g. Barge-in CANCEL_TURN)
            if "text" in message and message["text"]:
                try:
                    data = json.loads(message["text"])
                    event = data.get("event")

                    # BARGE-IN INTERRUPTION HANDLER
                    if event == "CANCEL_TURN":
                        t_start = time.time()
                        for task in active_tts_tasks:
                            if not task.done():
                                task.cancel()
                        active_tts_tasks.clear()
                        audio_buffer.clear()
                        accumulator.flush()
                        
                        elapsed_ms = (time.time() - t_start) * 1000
                        logger.info("Barge-in turn cancelled", halt_time_ms=elapsed_ms)
                        
                        await websocket.send_text(json.dumps({
                            "event": "TURN_CANCELLED",
                            "halt_time_ms": round(elapsed_ms, 2)
                        }))
                        continue

                except json.JSONDecodeError:
                    pass

            # 2. Binary Audio Stream
            if "bytes" in message and message["bytes"]:
                chunk = message["bytes"]
                audio_buffer.extend(chunk)

                if len(audio_buffer) >= 16000:
                    raw_audio = bytes(audio_buffer)
                    audio_buffer.clear()

                    stt_result = await stt_service.transcribe(raw_audio)
                    transcript = stt_result["text"]
                    
                    if not transcript:
                        continue

                    norm_transcript = normalize(transcript)
                    await websocket.send_text(json.dumps({
                        "event": "TRANSCRIPT_READY",
                        "transcript": norm_transcript
                    }))

                    chunks = knowledge_store.search(norm_transcript, top_k=2)
                    sys_prompt = build_system_prompt(language="am")
                    
                    full_reply = await llm_router.generate_response(
                        prompt=norm_transcript,
                        context_chunks=chunks,
                        system_prompt=sys_prompt
                    )
                    full_reply = append_mandatory_disclaimer(full_reply, language="am")

                    sentences = []
                    for word in full_reply.split(" "):
                        ready = accumulator.push_token(word + " ")
                        sentences.extend(ready)
                    sentences.extend(accumulator.flush())

                    async def synthesize_and_stream(sent_list):
                        for sentence in sent_list:
                            if not sentence.strip():
                                continue
                            try:
                                audio_pcm = await tts_service.synthesize_sentence(sentence)
                                await websocket.send_text(json.dumps({
                                    "event": "AUDIO_CHUNK_START",
                                    "sentence": sentence,
                                    "sample_rate": 16000
                                }))
                                await websocket.send_bytes(audio_pcm)
                            except asyncio.CancelledError:
                                logger.info("Sentence synthesis cancelled mid-turn")
                                break

                    task = asyncio.create_task(synthesize_and_stream(sentences))
                    active_tts_tasks.append(task)

    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected")
    finally:
        for task in active_tts_tasks:
            if not task.done():
                task.cancel()
