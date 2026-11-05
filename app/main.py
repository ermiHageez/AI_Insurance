"""InsurTech AI Assistant Microservice Application Entrypoint."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
import structlog

from app.core.config import settings
from app.api.v1.health import router as health_router
from app.api.v1.kb import router as kb_router
from app.api.v1.chat import router as chat_router
from app.api.v1.admin_sources import router as admin_sources_router
from app.api.v1.admin_review import router as admin_review_router
from app.api.v1.voice_socket import router as voice_router
from app.api.v1.admin_web import router as admin_web_router

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "InsurTech AI microservice starting",
        port=settings.PORT,
        llm_provider=settings.LLM_PROVIDER,
        environment=settings.ENVIRONMENT
    )
    # Auto-seed sample Amharic policy if available and store is empty
    try:
        from pathlib import Path
        from app.rag.extractor import DocumentExtractor
        from app.rag.chunker import chunk_document
        from app.rag.store import knowledge_store

        sample_pdf = Path(__file__).resolve().parent.parent / "sample_amharic_policy.pdf"
        if sample_pdf.exists() and len(knowledge_store._chunks) == 0:
            doc_info = DocumentExtractor.extract(sample_pdf.read_bytes(), sample_pdf.name)
            chunks = chunk_document(
                doc_info["full_text"],
                metadata={
                    "section": "Standard Coverage",
                    "page_num": 1,
                    "filename": sample_pdf.name
                }
            )
            knowledge_store.upsert_chunks(
                chunks=chunks,
                document_id="sample_amharic_policy",
                category="POLICY",
                source_hash=doc_info["source_hash"]
            )
            logger.info("Auto-seeded sample Amharic policy into knowledge store", chunk_count=len(chunks))
    except Exception as exc:
        logger.warning("Failed to auto-seed sample policy", error=str(exc))
    yield


def create_application() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title="InsurTech AI Assistant Microservice",
        description="Grounded Amharic/English AI assistant for insurance policyholders and admins.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API Routers
    app.include_router(health_router)
    app.include_router(kb_router)
    app.include_router(chat_router)
    app.include_router(admin_sources_router)
    app.include_router(admin_review_router)
    app.include_router(voice_router)
    app.include_router(admin_web_router)

    # Mount Prometheus metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    return app


app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
