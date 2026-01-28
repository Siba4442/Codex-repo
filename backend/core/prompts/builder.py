# backend/core/prompts/builder.py
"""
Prompt building utilities for menu extraction phases.
Centralizes all prompt logic and Jinja2 template rendering.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from backend.config import get_settings


class PromptBuilder:
    """Builds prompts from Jinja2 templates with validation"""

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize the prompt builder with template directory.

        Args:
            templates_dir: Path to Jinja2 templates. Defaults to config setting.
        """
        if templates_dir is None:
            settings = get_settings()
            templates_dir = settings.PROMPTS_DIR

        self.templates_dir = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            undefined=StrictUndefined,  # Fail if variable is missing
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, **variables) -> str:
        """
        Render a template with provided variables.

        Args:
            template_name: Name of the template file (e.g., "phase1.j2")
            **variables: Variables to pass to the template

        Returns:
            Rendered prompt string

        Raises:
            jinja2.TemplateNotFound: If template doesn't exist
            jinja2.UndefinedError: If required variable is missing
        """
        template = self.env.get_template(template_name)
        return template.render(**variables)

    def phase1_prompt(
        self,
        restaurant_name: str,
        page_number: int,
        additional_context: Optional[str] = None,
    ) -> str:
        """
        Build Phase 1 prompt for category extraction.

        Args:
            restaurant_name: Name of the restaurant
            page_number: PDF page number being processed
            additional_context: Optional context for better extraction

        Returns:
            Formatted prompt string
        """
        return self.render(
            "phase1.j2",
            restaurant_name=restaurant_name,
            page_number=page_number,
            additional_context=additional_context or "",
        )

    def phase2_prompt(
        self, restaurant_name: str, page_number: int, category: Dict[str, Any]
    ) -> str:
        """
        Build Phase 2 prompt for item extraction.

        Args:
            restaurant_name: Name of the restaurant
            page_number: PDF page number
            category: Category object with name and description

        Returns:
            Formatted prompt string
        """
        return self.render(
            "phase2.j2",
            restaurant_name=restaurant_name,
            page_number=page_number,
            category_name=category.get("name", ""),
            category_description=category.get("description", ""),
            categories=category,  # Pass full object for flexible template
        )

    def phase3_prompt(
        self, restaurant_name: str, page_number: int, category: Dict[str, Any]
    ) -> str:
        """
        Build Phase 3 prompt for base information extraction.

        Args:
            restaurant_name: Name of the restaurant
            page_number: PDF page number
            category: Category with items

        Returns:
            Formatted prompt string
        """
        return self.render(
            "phase3.j2",
            restaurant_name=restaurant_name,
            page_number=page_number,
            category=category,
            items_count=len(category.get("items", [])),
        )

    def phase4_prompt(
        self,
        restaurant_name: str,
        page_number: int,
        category: Dict[str, Any],
        category_base: Dict[str, Any],
    ) -> str:
        """
        Build Phase 4 prompt for complete item extraction with addons.

        Args:
            restaurant_name: Name of the restaurant
            page_number: PDF page number
            category: Category with items from phase 2
            category_base: Category base info from phase 3

        Returns:
            Formatted prompt string
        """
        return self.render(
            "phase4.j2",
            restaurant_name=restaurant_name,
            page_number=page_number,
            category=category,
            category_base=category_base,
            has_pricing=bool(category_base.get("base_price")),
        )

    def custom_prompt(self, template_name: str, **variables) -> str:
        """
        Build a custom prompt from any template.
        Useful for ad-hoc prompts or testing.

        Args:
            template_name: Name of template file
            **variables: Template variables

        Returns:
            Rendered prompt
        """
        return self.render(template_name, **variables)

    def list_templates(self) -> list[str]:
        """List all available template files"""
        return [t for t in self.env.list_templates() if t.endswith(".j2")]

    def validate_template(self, template_name: str) -> bool:
        """Check if a template exists and is valid"""
        try:
            self.env.get_template(template_name)
            return True
        except Exception:
            return False


# Singleton instance for easy import
_builder_instance = None


def get_prompt_builder() -> PromptBuilder:
    """Get cached prompt builder instance"""
    global _builder_instance
    if _builder_instance is None:
        _builder_instance = PromptBuilder()
    return _builder_instance


# Convenience functions for backward compatibility
def render_prompt(template_name: str, **variables) -> str:
    """Quick render without creating builder instance"""
    return get_prompt_builder().render(template_name, **variables)


def phase1_prompt(restaurant_name: str, page_number: int) -> str:
    """Convenience function for phase 1 prompt"""
    return get_prompt_builder().phase1_prompt(restaurant_name, page_number)


def phase2_prompt(
    restaurant_name: str, page_number: int, category: Dict[str, Any]
) -> str:
    """Convenience function for phase 2 prompt"""
    return get_prompt_builder().phase2_prompt(restaurant_name, page_number, category)


def phase3_prompt(
    restaurant_name: str, page_number: int, category: Dict[str, Any]
) -> str:
    """Convenience function for phase 3 prompt"""
    return get_prompt_builder().phase3_prompt(restaurant_name, page_number, category)


def phase4_prompt(
    restaurant_name: str,
    page_number: int,
    category: Dict[str, Any],
    category_base: Dict[str, Any],
) -> str:
    """Convenience function for phase 4 prompt"""
    return get_prompt_builder().phase4_prompt(
        restaurant_name, page_number, category, category_base
    )
