"""Semantic Chunker for Policy Documents.

Splits documents into ~512-token chunks with 10% overlap (~50 tokens),
preserving markdown headings, table rows, and deductible schedules.
"""
import re
from typing import List, Dict, Any


def estimate_tokens(text: str) -> int:
    """Rough estimation of token count (~4 characters per token on average)."""
    # For Amharic and English, whitespace word count * 1.3 is a strong heuristic
    words = len(text.split())
    return max(1, int(words * 1.3))


def chunk_document(
    text: str,
    target_tokens: int = 512,
    overlap_tokens: int = 50,
    metadata: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """Split text into semantic chunks with overlap.
    
    Args:
        text: Input document text.
        target_tokens: Maximum target tokens per chunk.
        overlap_tokens: Overlap tokens between consecutive chunks.
        metadata: Base metadata dictionary to attach to each chunk.
        
    Returns:
        List of chunk objects with text, token_count, and metadata.
    """
    if not text or not text.strip():
        return []

    metadata = metadata or {}
    
    # Split by major structural sections: double newlines or table boundaries
    paragraphs = re.split(r'\n{2,}', text)
    chunks: List[Dict[str, Any]] = []

    current_chunk_paras: List[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_clean = para.strip()
        if not para_clean:
            continue
            
        para_tokens = estimate_tokens(para_clean)
        
        # If single paragraph exceeds target, split by sentences
        if para_tokens > target_tokens:
            sentences = re.split(r'(?<=[.!?።\n])\s+', para_clean)
            for sentence in sentences:
                sent_tokens = estimate_tokens(sentence)
                if current_tokens + sent_tokens > target_tokens and current_chunk_paras:
                    chunk_text = "\n\n".join(current_chunk_paras)
                    chunks.append({
                        "content_text": chunk_text,
                        "token_count": current_tokens,
                        **metadata
                    })
                    # Keep overlap from the end
                    overlap_paras = []
                    overlap_acc = 0
                    for p in reversed(current_chunk_paras):
                        p_toks = estimate_tokens(p)
                        if overlap_acc + p_toks <= overlap_tokens:
                            overlap_paras.insert(0, p)
                            overlap_acc += p_toks
                        else:
                            break
                    current_chunk_paras = overlap_paras
                    current_tokens = overlap_acc
                
                current_chunk_paras.append(sentence)
                current_tokens += sent_tokens
            continue

        if current_tokens + para_tokens > target_tokens and current_chunk_paras:
            chunk_text = "\n\n".join(current_chunk_paras)
            chunks.append({
                "content_text": chunk_text,
                "token_count": current_tokens,
                **metadata
            })
            # Overlap handling
            overlap_paras = []
            overlap_acc = 0
            for p in reversed(current_chunk_paras):
                p_toks = estimate_tokens(p)
                if overlap_acc + p_toks <= overlap_tokens:
                    overlap_paras.insert(0, p)
                    overlap_acc += p_toks
                else:
                    break
            current_chunk_paras = overlap_paras
            current_tokens = overlap_acc

        current_chunk_paras.append(para_clean)
        current_tokens += para_tokens

    if current_chunk_paras:
        chunk_text = "\n\n".join(current_chunk_paras)
        chunks.append({
            "content_text": chunk_text,
            "token_count": current_tokens,
            **metadata
        })

    # Add chunk index to metadata
    for i, chunk in enumerate(chunks):
        chunk["chunk_index"] = i

    return chunks
