# backend/core/processors/image.py
from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from typing import Optional, Tuple

from PIL import Image


@dataclass(frozen=True)
class ImageOptions:
    max_size: Tuple[int, int] = (1600, 1600)  # keep under model limits
    format: str = "PNG"
    jpeg_quality: int = 85


class ImageProcessor:
    def __init__(self, options: Optional[ImageOptions] = None):
        self.options = options or ImageOptions()

    def decode_base64_to_pil(self, b64_str: str) -> Image.Image:
        data = base64.b64decode(b64_str)
        return Image.open(io.BytesIO(data)).convert("RGB")

    def encode_pil_to_base64(
        self, img: Image.Image, *, format: Optional[str] = None
    ) -> str:
        buf = io.BytesIO()
        fmt = (format or self.options.format).upper()

        if fmt in ("JPG", "JPEG"):
            img.save(
                buf, format="JPEG", quality=self.options.jpeg_quality, optimize=True
            )
        else:
            img.save(buf, format="PNG", optimize=True)

        return base64.b64encode(buf.getvalue()).decode("utf-8")

    def resize_to_max(self, img: Image.Image) -> Image.Image:
        max_w, max_h = self.options.max_size
        img = img.copy()
        img.thumbnail((max_w, max_h))
        return img

    def normalize_base64(self, b64_str: str) -> str:
        """
        Decode -> resize -> re-encode.
        Ensures consistent size/format before sending to LLM.
        """
        img = self.decode_base64_to_pil(b64_str)
        img = self.resize_to_max(img)
        return self.encode_pil_to_base64(img, format=self.options.format)

    def to_data_url(self, b64_str: str, mime: str = "image/png") -> str:
        """Convert base64 to data URL form used by OpenRouter/OpenAI image_url."""
        return f"data:{mime};base64,{b64_str}"
