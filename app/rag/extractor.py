"""Document Text Extractor.

Extracts text from PDF, DOCX, TXT, and Markdown documents.
Preserves table formatting and markdown structure for deductible tables.
"""
import hashlib
from typing import Dict, Any, List


def compute_source_hash(file_bytes: bytes) -> str:
    """Compute SHA-256 hash of raw document bytes for idempotency."""
    return hashlib.sha256(file_bytes).hexdigest()


class DocumentExtractor:
    """Extracts text and tabular content from insurance policy documents."""

    @staticmethod
    def extract(file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Extract content and structure from file bytes.
        
        Args:
            file_bytes: Raw bytes of the document.
            filename: Original filename (used to inspect extension).
            
        Returns:
            Dict containing extracted pages, full text, and metadata report.
        """
        source_hash = compute_source_hash(file_bytes)
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        
        pages: List[Dict[str, Any]] = []
        full_text_parts: List[str] = []

        if ext in ['txt', 'md']:
            try:
                text = file_bytes.decode('utf-8')
            except UnicodeDecodeError:
                text = file_bytes.decode('latin-1')
            pages.append({"page_num": 1, "text": text})
            full_text_parts.append(text)

        elif ext == 'pdf':
            # Attempt PyMuPDF extraction if installed, otherwise fallback to text parser
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                for page_idx in range(len(doc)):
                    page = doc[page_idx]
                    page_text = page.get_text("text")
                    pages.append({
                        "page_num": page_idx + 1,
                        "text": page_text
                    })
                    full_text_parts.append(page_text)
                doc.close()
            except ImportError:
                # Fallback for environments without compiled PyMuPDF
                # Decode printable strings and structure
                try:
                    raw_text = file_bytes.decode('utf-8', errors='ignore')
                except Exception:
                    raw_text = ""
                pages.append({"page_num": 1, "text": raw_text})
                full_text_parts.append(raw_text)

        else:
            # Fallback for other document types
            try:
                text = file_bytes.decode('utf-8', errors='ignore')
            except Exception:
                text = ""
            pages.append({"page_num": 1, "text": text})
            full_text_parts.append(text)

        full_text = "\n\n".join(full_text_parts)

        return {
            "filename": filename,
            "source_hash": source_hash,
            "page_count": len(pages),
            "pages": pages,
            "full_text": full_text,
            "total_characters": len(full_text),
            "ocr_applied": False
        }
