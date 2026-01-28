"""
Phase 1: Category Discovery
Extracts category headers and descriptions from menu PDF pages.
"""

import asyncio
import json
from typing import Any, Dict, List

from backend.config import get_settings
from backend.core.processors.pdf import PDFProcessor, get_pdf_processor
from backend.core.prompts.builder import get_prompt_builder
from backend.models.domain import Categories
from backend.services.llm_client import LLMClient, get_llm_client


class Phase1Extractor:
    """Handles Phase 1 extraction: category discovery"""

    def __init__(
        self,
        llm_client: LLMClient,
        pdf_processor: PDFProcessor,
        max_concurrency: int = None,
    ):
        self.llm = llm_client
        self.pdf_processor = pdf_processor
        self.prompt_builder = get_prompt_builder()
        self.max_concurrency = max_concurrency or get_settings().MAX_CONCURRENCY

    async def extract_page(
        self, restaurant_name: str, page_number: int, page_image: str
    ) -> Dict[str, Any]:
        """
        Extract categories from a single page.

        Args:
            restaurant_name: Name of the restaurant
            page_number: Page number (1-indexed)
            page_image: Base64 encoded image

        Returns:
            Dict with page_number and extracted data
        """
        max_retries = 2
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Build prompt
                prompt = self.prompt_builder.phase1_prompt(restaurant_name, page_number)

                # Prepare message
                message_content = [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{page_image}"},
                    },
                ]

                # Call LLM
                response = await self.llm.generate(
                    messages=[{"role": "user", "content": message_content}],
                    response_format=self.llm.json_schema_format(Categories),
                )

                # Parse and validate
                raw = response.choices[0].message.content
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError as e:
                    error_msg = f"JSON decode error at position {e.pos}: {e.msg}"
                    print(f"Phase 1, Attempt {attempt + 1}/{max_retries} - Failed to parse LLM response: {error_msg}")
                    print(f"Raw response (first 500 chars): {raw[:500]}")
                    print(f"Raw response (around error): {raw[max(0, e.pos-100):e.pos+100]}")
                    
                    if attempt < max_retries - 1:
                        print(f"Retrying page {page_number}...")
                        await asyncio.sleep(1)
                        continue
                    
                    raise ValueError(f"LLM returned invalid JSON for page {page_number}: {error_msg}")
                
                validated = Categories.model_validate(data)
                return {"page_number": page_number, "data": validated.model_dump()}
                
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    print(f"Phase 1, Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                    await asyncio.sleep(1)
                    continue
                raise
        
        raise last_error if last_error else ValueError("All retry attempts failed")

    async def extract_all_pages(
        self, restaurant_name: str, pdf_path: str
    ) -> Dict[str, Any]:
        """
        Extract categories from all pages in the PDF.

        Args:
            restaurant_name: Name of the restaurant
            pdf_path: Path to PDF file

        Returns:
            Complete phase 1 output with all pages
        """
        # Convert PDF to images
        images = await self.pdf_processor.convert_to_images(pdf_path)

        # Create coroutines for all pages
        coros = [
            self.extract_page(restaurant_name, page_idx, img)
            for page_idx, img in enumerate(images, start=1)
        ]

        # Run with concurrency limit
        pages = await self._bounded_gather(coros)

        return {"restaurant_name": restaurant_name, "pages": pages}

    async def _bounded_gather(self, coros: List) -> List:
        """Run coroutines with concurrency limit"""
        sem = asyncio.Semaphore(self.max_concurrency)

        async def _run(coro):
            async with sem:
                return await coro

        return await asyncio.gather(*(_run(c) for c in coros))


# Convenience function for backward compatibility
async def run_phase1(restaurant_name: str, pdf_path: str) -> Dict[str, Any]:
    """
    Run phase 1 extraction with default settings.

    Args:
        restaurant_name: Name of the restaurant
        pdf_path: Path to PDF file

    Returns:
        Phase 1 output
    """

    extractor = Phase1Extractor(
        llm_client=get_llm_client(), pdf_processor=get_pdf_processor()
    )

    return await extractor.extract_all_pages(restaurant_name, pdf_path)
