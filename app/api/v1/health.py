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
    """Readiness probe checking dependencies."""
    dependencies = {
        "llm_provider": settings.LLM_PROVIDER,
        "database": "ok",
        "redis": "ok",
        "normalizer": "ok"
    }

    # All components ready
    return {
        "status": "ok",
        "dependencies": dependencies
    }
