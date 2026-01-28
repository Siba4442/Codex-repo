"""
Phase 3: Base Information Extraction
Extracts pricing, options, and base configurations for each category.
"""

import asyncio
import json
from typing import Any, Dict, List

from backend.config import get_settings
from backend.core.processors.pdf import PDFProcessor, get_pdf_processor
from backend.core.prompts.builder import get_prompt_builder
from backend.models.domain import CategoryBase, CategoryWithItems
from backend.services.llm_client import LLMClient, get_llm_client


class Phase3Extractor:
    """Handles Phase 3 extraction: category base information"""

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

    async def extract_category_base(
        self,
        restaurant_name: str,
        page_number: int,
        page_image: str,
        category: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract base information for a category"""
        max_retries = 2
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Wrap category for prompt
                category_wrapper = {"category": category}

                # Build prompt
                prompt = self.prompt_builder.phase3_prompt(
                    restaurant_name, page_number, category_wrapper
                )

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
                    response_format=self.llm.json_schema_format(CategoryBase),
                )

                # Parse and validate
                raw = response.choices[0].message.content
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError as e:
                    error_msg = f"JSON decode error at position {e.pos}: {e.msg}"
                    print(f"Phase 3, Attempt {attempt + 1}/{max_retries} - Failed to parse LLM response: {error_msg}")
                    print(f"Raw response (first 500 chars): {raw[:500]}")
                    print(f"Raw response (around error): {raw[max(0, e.pos-100):e.pos+100]}")
                    
                    if attempt < max_retries - 1:
                        print(f"Retrying category '{category.get('name_raw', 'unknown')}'...")
                        await asyncio.sleep(1)
                        continue
                    
                    raise ValueError(f"LLM returned invalid JSON for category '{category.get('name_raw', 'unknown')}': {error_msg}")
                
                validated = CategoryBase.model_validate(obj)
                return validated.model_dump()
                
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    print(f"Phase 3, Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                    await asyncio.sleep(1)
                    continue
                raise
        
        raise last_error if last_error else ValueError("All retry attempts failed")

    async def extract_page(
        self,
        restaurant_name: str,
        page_number: int,
        page_image: str,
        page_categories: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Extract base info for all categories on a page"""
        # Create coroutines
        coros = [
            self.extract_category_base(restaurant_name, page_number, page_image, cat)
            for cat in page_categories
        ]

        # Run with concurrency limit
        category_results = await self._bounded_gather(coros)

        return {"page_number": page_number, "categories": category_results}

    async def extract_all_pages(
        self, restaurant_name: str, items_payload: Dict[str, Any], pdf_path: str
    ) -> Dict[str, Any]:
        """Extract base information from all pages"""
        # Convert PDF to images
        images = await self.pdf_processor.convert_to_images(pdf_path)

        # Extract for each page
        all_pages = []
        for page in items_payload["pages"]:
            page_number = page["page_number"]
            img_b64 = images[page_number - 1]

            # Validate categories
            page_categories = [
                CategoryWithItems.model_validate(cat).model_dump()
                for cat in page["categories"]
            ]

            # Extract bases for this page
            page_result = await self.extract_page(
                restaurant_name, page_number, img_b64, page_categories
            )
            all_pages.append(page_result)

        return {"restaurant_name": restaurant_name, "pages": all_pages}

    async def _bounded_gather(self, coros: List) -> List:
        """Run coroutines with concurrency limit"""
        sem = asyncio.Semaphore(self.max_concurrency)

        async def _run(coro):
            async with sem:
                return await coro

        return await asyncio.gather(*(_run(c) for c in coros))


# Convenience function
async def run_phase3(
    restaurant_name: str, items_payload: Dict[str, Any], pdf_path: str
) -> Dict[str, Any]:
    """Run phase 3 extraction with default settings"""

    extractor = Phase3Extractor(
        llm_client=get_llm_client(), pdf_processor=get_pdf_processor()
    )

    return await extractor.extract_all_pages(restaurant_name, items_payload, pdf_path)
