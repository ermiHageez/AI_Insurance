"""Knowledge Base & Document Ingestion Endpoints."""
import uuid
import time
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.rag.extractor import DocumentExtractor
from app.rag.chunker import chunk_document
from app.rag.store import knowledge_store
from app.rag.normalizer import normalize

router = APIRouter(prefix="/api/v1/kb", tags=["Knowledge Base"])

# In-memory jobs tracking
_INGESTION_JOBS: Dict[str, Dict[str, Any]] = {}


class SearchRequest(BaseModel):
    query: str = Field(..., description="User search query in Amharic or English")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    category: Optional[str] = Field(default=None, description="Optional category filter (POLICY, REGULATORY, GOLDEN_QA)")


class ChunkResponse(BaseModel):
    id: str
    document_id: str
    page_num: int
    category: str
    section: str
    content_text: str
    score: float


@router.post("/documents/upload", status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str = Form("POLICY")
):
    """Upload policy or tariff document (PDF, DOCX, TXT) <= 20MB."""
    # Validation: file size and extension
    filename = file.filename or "unknown"
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    if ext not in ["pdf", "docx", "txt", "md"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed: pdf, docx, txt, md"
        )

    file_bytes = await file.read()
    if len(file_bytes) > 20 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File size exceeds the 20MB limit."
        )

    job_id = str(uuid.uuid4())
    _INGESTION_JOBS[job_id] = {
        "job_id": job_id,
        "filename": filename,
        "status": "PROCESSING",
        "category": category,
        "started_at": time.time(),
        "chunks_indexed": 0,
        "report": None
    }

    # Execute extraction and indexing in background
    def process_job():
        try:
            extraction = DocumentExtractor.extract(file_bytes, filename)
            doc_id = filename.rsplit('.', 1)[0]
            chunks = chunk_document(
                extraction["full_text"],
                metadata={
                    "section": "Standard Coverage",
                    "page_num": 1,
                    "filename": filename
                }
            )
            indexed_count = knowledge_store.upsert_chunks(
                chunks=chunks,
                document_id=doc_id,
                category=category,
                source_hash=extraction["source_hash"]
            )
            _INGESTION_JOBS[job_id]["status"] = "COMPLETED"
            _INGESTION_JOBS[job_id]["chunks_indexed"] = indexed_count
            _INGESTION_JOBS[job_id]["report"] = {
                "source_hash": extraction["source_hash"],
                "total_chars": extraction["total_characters"],
                "pages": extraction["page_count"]
            }
        except Exception as e:
            _INGESTION_JOBS[job_id]["status"] = "FAILED"
            _INGESTION_JOBS[job_id]["error"] = str(e)

    background_tasks.add_task(process_job)

    return {
        "jobId": job_id,
        "filename": filename,
        "status": "PROCESSING",
        "message": "Document accepted for indexing."
    }


@router.get("/documents/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Retrieve async extraction & indexing job status."""
    if job_id not in _INGESTION_JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    return _INGESTION_JOBS[job_id]


@router.post("/search", response_model=List[ChunkResponse])
async def search_knowledge_base(request: SearchRequest):
    """Retrieve top-K policy and regulatory chunks with citations (<80ms)."""
    start_time = time.time()
    results = knowledge_store.search(
        query=request.query,
        top_k=request.top_k,
        category=request.category
    )
    elapsed_ms = (time.time() - start_time) * 1000
    return results
