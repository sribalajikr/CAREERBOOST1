"""PDF parsing — extract raw text from an uploaded resume."""
from io import BytesIO

from pypdf import PdfReader


def extract_text_from_pdf(data: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(data))
        pages = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            pages.append(page_text.strip())
        return "\n".join(p for p in pages if p).strip()
    except Exception:  # noqa: BLE001 - parser must never crash the API
        return ""
