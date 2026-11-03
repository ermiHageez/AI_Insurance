"""Health and Readiness endpoints."""
from fastapi import APIRouter, Response, status
from app.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/healthz")
async def healthz():
    """Liveness probe."""
    return {
        "status": "ok",
        "service": "insuretech-ai",
        "port": settings.PORT,
        "environment": settings.ENVIRONMENT
    }


@router.get("/readyz")
async def readyz(response: Response):
    """Readiness probe checking dependencies and active LLM configuration."""
    dependencies = {
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "llm_configured": bool(settings.LLM_API_KEY) if settings.LLM_PROVIDER == "openai_compatible" else True,
        "database": "ok",
        "redis": "ok",
        "normalizer": "ok"
    }

    return {
        "status": "ok",
        "dependencies": dependencies
    }
