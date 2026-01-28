# backend/core/processors/pdf.py
from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from typing import List, Optional

import fitz  # PyMuPDF

from backend.core.processors.image import ImageProcessor


class PDFProcessor:
    def __init__(self, image_processor: Optional[ImageProcessor] = None):
        self.image_processor = image_processor or ImageProcessor()

    async def convert_to_base64(self, page: fitz.Page) -> str:
        """Convert a PDF page to a base64 PNG image."""
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Increase resolution
        img_data = pix.tobytes("png")
        base64_str = base64.b64encode(img_data).decode("utf-8")
        return base64_str

    async def convert_to_images(
        self,
        pdf_path: str | Path,
        *,
        dpi: int = 200,
        fmt: str = "png",
    ) -> List[str]:
        """
        Convert a PDF into a list of base64-encoded images (one per page).
        This wraps your existing utils.processing.convert_pdf_into_images().
        """

        if isinstance(pdf_path, str):
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF not found: {pdf_path}")  # file path
            doc = fitz.open(pdf_path)
        else:
            doc = fitz.open(stream=pdf_path, filetype="pdf")

        try:
            images_b64: List[str] = []
            tasks = [
                self.convert_to_base64(doc[page_num]) for page_num in range(len(doc))
            ]
            awaitable_results = await asyncio.gather(*tasks)
            images_b64.extend(awaitable_results)
            return images_b64

        finally:
            doc.close()

        # Optionally normalize images (resize/convert) in one place
        # (only needed if you want consistent sizes)
        # images_b64 = [self.image_processor.normalize_base64(img) for img in images_b64]

    async def page_count(self, pdf_path: str | Path) -> int:
        """
        Return number of pages (optional but useful).
        Implement via PyPDF or pdfplumber if you add it.
        """
        from pypdf import PdfReader  # if installed

        pdf_path = Path(pdf_path)
        reader = PdfReader(str(pdf_path))
        return len(reader.pages)


# convenient singleton
_pdf_processor: Optional[PDFProcessor] = None


def get_pdf_processor() -> PDFProcessor:
    global _pdf_processor
    if _pdf_processor is None:
        _pdf_processor = PDFProcessor()
    return _pdf_processor
