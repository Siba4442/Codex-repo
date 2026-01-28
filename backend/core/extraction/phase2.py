"""
Phase 2: Item Extraction
Extracts menu items under each category discovered in Phase 1.
"""

import asyncio
import json
from typing import Any, Dict, List

from backend.config import get_settings
from backend.core.processors.pdf import PDFProcessor, get_pdf_processor
from backend.core.prompts.builder import get_prompt_builder
from backend.models.domain import Categories, CategoryWithItems
from backend.services.llm_client import LLMClient, get_llm_client


class Phase2Extractor:
    """Handles Phase 2 extraction: item discovery per category"""

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

    async def extract_category(
        self,
        restaurant_name: str,
        page_number: int,
        page_image: str,
        category: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract items for a single category.

        Args:
            restaurant_name: Name of the restaurant
            page_number: Page number
            page_image: Base64 encoded image
            category: Category object from Phase 1

        Returns:
            CategoryWithItems with extracted items
        """
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Build prompt
                prompt = self.prompt_builder.phase2_prompt(
                    restaurant_name, page_number, category
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
                    response_format=self.llm.json_schema_format(CategoryWithItems),
                )

                # Parse and validate
                raw = response.choices[0].message.content
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError as e:
                    # Log the problematic JSON for debugging
                    category_name = category.get('name_raw', category.get('name', 'unknown'))
                    error_msg = f"JSON decode error at position {e.pos}: {e.msg}"
                    print(f"\n=== Phase 2 JSON Parse Error ===")
                    print(f"Category: {category_name}")
                    print(f"Page: {page_number}")
                    print(f"Attempt: {attempt + 1}/{max_retries}")
                    print(f"Error: {error_msg}")
                    print(f"Raw response (first 500 chars): {raw[:500]}")
                    print(f"Raw response (around error): {raw[max(0, e.pos-100):e.pos+100]}")
                    print(f"================================\n")
                    
                    if attempt < max_retries - 1:
                        print(f"Retrying category '{category_name}'...")
                        await asyncio.sleep(1)  # Brief delay before retry
                        continue
                    
                    raise ValueError(f"LLM returned invalid JSON for category '{category_name}' on page {page_number}: {error_msg}")
                
                validated = CategoryWithItems.model_validate(obj)
                return validated.model_dump()
                
            except Exception as e:
                last_error = e
                category_name = category.get('name_raw', category.get('name', 'unknown'))
                if attempt < max_retries - 1:
                    print(f"Phase 2 - Category '{category_name}' - Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                    await asyncio.sleep(1)
                    continue
                print(f"Phase 2 - Category '{category_name}' - All {max_retries} attempts failed")
                raise
        
        # If all retries failed
        raise last_error if last_error else ValueError("All retry attempts failed")

    async def extract_page(
        self,
        restaurant_name: str,
        page_number: int,
        page_image: str,
        page_categories: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Extract items for all categories on a page.

        Args:
            restaurant_name: Name of restaurant
            page_number: Page number
            page_image: Base64 encoded image
            page_categories: List of categories from Phase 1

        Returns:
            Page data with all category items
        """
        # Create coroutines for each category
        coros = [
            self.extract_category(restaurant_name, page_number, page_image, cat)
            for cat in page_categories
        ]

        # Run with concurrency limit
        category_results = await self._bounded_gather(coros)

        return {"page_number": page_number, "categories": category_results}

    async def extract_all_pages(
        self, restaurant_name: str, categories_payload: Dict[str, Any], pdf_path: str
    ) -> Dict[str, Any]:
        """
        Extract items from all pages based on Phase 1 categories.

        Args:
            restaurant_name: Name of restaurant
            categories_payload: Phase 1 output
            pdf_path: Path to PDF

        Returns:
            Complete Phase 2 output
        """
        # Convert PDF to images
        images = await self.pdf_processor.convert_to_images(pdf_path)

        # Extract for each page
        all_pages = []
        for page in categories_payload["pages"]:
            page_number = page["page_number"]
            img_b64 = images[page_number - 1]

            # Validate categories structure
            page_categories_obj = Categories.model_validate(page["data"])
            page_categories = [
                cat.model_dump() for cat in page_categories_obj.categories
            ]

            # Extract items for this page
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
async def run_phase2(
    restaurant_name: str, categories_payload: Dict[str, Any], pdf_path: str
) -> Dict[str, Any]:
    """Run phase 2 extraction with default settings"""

    extractor = Phase2Extractor(
        llm_client=get_llm_client(), pdf_processor=get_pdf_processor()
    )

    return await extractor.extract_all_pages(
        restaurant_name, categories_payload, pdf_path
    )
