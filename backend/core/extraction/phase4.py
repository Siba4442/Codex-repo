"""
Phase 4: Complete Item Extraction with Addons
Combines Phase 2 items with Phase 3 bases to extract full item details.
"""

import asyncio
import json
from typing import Any, Dict, List

from backend.config import get_settings
from backend.core.processors.pdf import PDFProcessor, get_pdf_processor
from backend.core.prompts.builder import get_prompt_builder
from backend.models.domain import CategoryBase, CategoryItemAddons, CategoryWithItems
from backend.services.llm_client import LLMClient, get_llm_client


class Phase4Extractor:
    """Handles Phase 4 extraction: complete item details with addons"""

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

    async def extract_category_addons(
        self,
        restaurant_name: str,
        page_number: int,
        page_image: str,
        category: Dict[str, Any],
        category_base: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract complete item details with addons for a category"""
        max_retries = 2
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Wrap data for prompt
                category_wrapper = {"category": category}
                base_wrapper = {"category_base": category_base}

                # Build prompt
                prompt = self.prompt_builder.phase4_prompt(
                    restaurant_name, page_number, category_wrapper, base_wrapper
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
                    response_format=self.llm.json_schema_format(CategoryItemAddons),
                )

                # Parse and validate
                raw = response.choices[0].message.content
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError as e:
                    error_msg = f"JSON decode error at position {e.pos}: {e.msg}"
                    print(f"Phase 4, Attempt {attempt + 1}/{max_retries} - Failed to parse LLM response: {error_msg}")
                    print(f"Raw response (first 500 chars): {raw[:500]}")
                    print(f"Raw response (around error): {raw[max(0, e.pos-100):e.pos+100]}")
                    
                    if attempt < max_retries - 1:
                        print(f"Retrying category '{category.get('name_raw', 'unknown')}'...")
                        await asyncio.sleep(1)
                        continue
                    
                    raise ValueError(f"LLM returned invalid JSON for category '{category.get('name_raw', 'unknown')}': {error_msg}")
                
                validated = CategoryItemAddons.model_validate(obj)
                return validated.model_dump()
                
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    print(f"Phase 4, Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
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
        page_bases: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Extract addons for all categories on a page"""
        # Create coroutines for each category
        coros = [
            self.extract_category_addons(
                restaurant_name, page_number, page_image, cat, base
            )
            for cat, base in zip(page_categories, page_bases)
        ]

        # Run with concurrency limit
        category_results = await self._bounded_gather(coros)

        return {"page_number": page_number, "categories": category_results}

    async def extract_all_pages(
        self,
        restaurant_name: str,
        items_payload: Dict[str, Any],
        bases_payload: Dict[str, Any],
        pdf_path: str,
    ) -> Dict[str, Any]:
        """Extract complete item details from all pages"""
        # Convert PDF to images
        images = await self.pdf_processor.convert_to_images(pdf_path)

        # Extract for each page
        all_pages = []
        for page_items, page_bases in zip(
            items_payload["pages"], bases_payload["pages"]
        ):
            page_number = page_items["page_number"]
            img_b64 = images[page_number - 1]

            # Validate structures
            page_categories = [
                CategoryWithItems.model_validate(cat).model_dump()
                for cat in page_items["categories"]
            ]
            page_bases_list = [
                CategoryBase.model_validate(base).model_dump()
                for base in page_bases["categories"]
            ]

            # Extract for this page
            page_result = await self.extract_page(
                restaurant_name, page_number, img_b64, page_categories, page_bases_list
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
async def run_phase4(
    restaurant_name: str,
    items_payload: Dict[str, Any],
    bases_payload: Dict[str, Any],
    pdf_path: str,
) -> Dict[str, Any]:
    """Run phase 4 extraction with default settings"""

    extractor = Phase4Extractor(
        llm_client=get_llm_client(), pdf_processor=get_pdf_processor()
    )

    return await extractor.extract_all_pages(
        restaurant_name, items_payload, bases_payload, pdf_path
    )
