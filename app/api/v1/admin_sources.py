"""Admin Regulatory Sources & Approval Queue Endpoints."""
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl, Field

from app.mcp.registry import regulatory_registry, is_allowed_domain
from app.mcp.server import regulatory_fetcher, PENDING_APPROVAL_STORE

router = APIRouter(prefix="/api/v1/admin", tags=["Admin Regulatory"])


class SourceRegisterRequest(BaseModel):
    url: str = Field(..., description="Target regulatory domain URL")
    name: str = Field(..., description="Descriptive source label (e.g. 'NBE Motor Directive')")


class ApproveRequest(BaseModel):
    reviewer: str = Field(default="admin@insurtech.et")


class FetchTriggerRequest(BaseModel):
    source_id: str
    keyword: Optional[str] = None


@router.post("/sources")
async def register_regulatory_source(request: SourceRegisterRequest):
    """Register whitelisted Ethiopian regulatory portal."""
    if not is_allowed_domain(request.url):
        raise HTTPException(
            status_code=400,
            detail=f"URL domain '{request.url}' is not on the approved regulatory whitelist."
        )

    record = regulatory_registry.register_source(url=request.url, name=request.name)
    return record


@router.get("/sources")
async def list_regulatory_sources():
    """List all registered regulatory sources."""
    return regulatory_registry.list_sources()


@router.post("/regulatory/fetch")
async def trigger_fetch(request: FetchTriggerRequest):
    """Trigger on-demand fetch and change detection."""
    source = regulatory_registry.get_source(request.source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    result = await regulatory_fetcher.fetch_regulatory_update(
        target_url=source["url"],
        keyword=request.keyword,
        source_id=request.source_id
    )
    return result


@router.get("/regulatory/pending")
async def list_pending_regulatory_diffs():
    """Queue of regulatory diffs requiring human verification before indexing."""
    pending = [r for r in PENDING_APPROVAL_STORE.values() if r["status"] == "PENDING"]
    return pending


@router.post("/regulatory/pending/{pending_id}/approve")
async def approve_regulatory_diff(pending_id: str, request: ApproveRequest):
    """Approve verified regulatory update and trigger RAG vector indexing."""
    try:
        res = regulatory_fetcher.approve_and_index(pending_id=pending_id, reviewer=request.reviewer)
        return res
    except KeyError:
        raise HTTPException(status_code=404, detail="Pending record not found")
