"""
Image Analysis Skill — تحليل الصور
====================================
Computer vision for property images: room detection, condition assessment,
virtual staging analysis, and image enhancement.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger("skills.image_analysis")


class ImageAnalysisSkill:
    """Image analysis and computer vision skill."""

    async def analyze_property_image(self, image_path: str) -> dict:
        """Analyze a property image for features and condition."""
        path = Path(image_path)
        if not path.exists():
            return {"status": "error", "error": f"Image not found: {image_path}"}

        try:
            from PIL import Image, ImageStat

            img = Image.open(image_path)
            stat = ImageStat.Stat(img)

            # Basic image analysis
            width, height = img.size
            aspect_ratio = round(width / height, 2) if height > 0 else 0

            # Brightness analysis
            brightness = sum(stat.mean[:3]) / 3
            brightness_label = "dark" if brightness < 85 else "normal" if brightness < 170 else "bright"

            # Color analysis
            dominant_color = self._get_dominant_color(img)

            # Check if image needs enhancement
            needs_enhancement = brightness < 60 or brightness > 220

            return {
                "status": "success",
                "file": image_path,
                "dimensions": {"width": width, "height": height, "aspect_ratio": aspect_ratio},
                "brightness": {"value": round(brightness, 1), "label": brightness_label},
                "dominant_color": dominant_color,
                "needs_enhancement": needs_enhancement,
                "format": img.format or path.suffix[1:],
                "mode": img.mode,
                "megapixels": round((width * height) / 1_000_000, 2),
            }
        except ImportError:
            return {"status": "error", "error": "Pillow not installed. Run: pip install Pillow"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def batch_analyze_images(self, image_paths: list[str]) -> dict:
        """Analyze multiple property images."""
        results = []
        for path in image_paths:
            result = await self.analyze_property_image(path)
            results.append(result)

        successful = [r for r in results if r["status"] == "success"]
        return {
            "status": "success",
            "total": len(image_paths),
            "analyzed": len(successful),
            "results": results,
            "summary": {
                "avg_brightness": round(
                    sum(r["brightness"]["value"] for r in successful) / len(successful), 1
                ) if successful else 0,
                "needs_enhancement_count": sum(1 for r in successful if r.get("needs_enhancement")),
            },
        }

    async def enhance_image(self, image_path: str, output_path: str | None = None) -> dict:
        """Enhance a property image (brightness, contrast, sharpness)."""
        try:
            from PIL import Image, ImageEnhance

            img = Image.open(image_path)

            # Auto-enhance
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.1)

            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.2)

            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.3)

            # Save enhanced image
            if not output_path:
                path = Path(image_path)
                output_path = str(path.parent / f"{path.stem}_enhanced{path.suffix}")

            img.save(output_path, quality=95)

            return {
                "status": "success",
                "original": image_path,
                "enhanced": output_path,
                "improvements": ["brightness +10%", "contrast +20%", "sharpness +30%"],
            }
        except ImportError:
            return {"status": "error", "error": "Pillow not installed"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def detect_room_type(self, image_path: str) -> dict:
        """Detect the type of room in an image (basic heuristic)."""
        try:
            from PIL import Image, ImageStat

            img = Image.open(image_path)
            stat = ImageStat.Stat(img)

            # Basic heuristic based on color and brightness
            r, g, b = stat.mean[:3]
            brightness = (r + g + b) / 3

            # Simple room type heuristic
            room_type = "unknown"
            confidence = 0.3

            if brightness > 180:
                room_type = "living_room"
                confidence = 0.6
            elif r > g and r > b:
                room_type = "kitchen"
                confidence = 0.5
            elif b > r and b > g:
                room_type = "bathroom"
                confidence = 0.5
            elif 80 < brightness < 140:
                room_type = "bedroom"
                confidence = 0.5

            return {
                "status": "success",
                "file": image_path,
                "detected_type": room_type,
                "confidence": confidence,
                "note": "Heuristic-based detection. For accurate detection, use an AI vision API.",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def create_thumbnail(self, image_path: str, output_path: str | None = None, size: tuple = (300, 300)) -> dict:
        """Create a thumbnail of a property image."""
        try:
            from PIL import Image

            img = Image.open(image_path)
            img.thumbnail(size, Image.LANCZOS)

            if not output_path:
                path = Path(image_path)
                output_path = str(path.parent / f"{path.stem}_thumb{path.suffix}")

            img.save(output_path, quality=85)

            return {
                "status": "success",
                "original": image_path,
                "thumbnail": output_path,
                "size": size,
                "new_dimensions": img.size,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def extract_image_metadata(self, image_path: str) -> dict:
        """Extract EXIF metadata from an image."""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS

            img = Image.open(image_path)
            exif_data = {}

            if hasattr(img, "_getexif") and img._getexif():
                for tag_id, value in img._getexif().items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif_data[str(tag)] = str(value)[:200]

            return {
                "status": "success",
                "file": image_path,
                "format": img.format,
                "mode": img.mode,
                "size": img.size,
                "has_exif": bool(exif_data),
                "metadata": exif_data,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_dominant_color(self, img) -> dict:
        """Get the dominant color of an image."""
        try:

            small = img.copy()
            small.thumbnail((50, 50))
            small = small.convert("RGB")

            colors = small.getcolors(maxcolors=2500)
            if colors:
                colors.sort(key=lambda x: x[0], reverse=True)
                r, g, b = colors[0][1]
                return {"r": r, "g": g, "b": b, "hex": f"#{r:02x}{g:02x}{b:02x}"}
            return {"r": 128, "g": 128, "b": 128, "hex": "#808080"}
        except Exception:
            return {"r": 128, "g": 128, "b": 128, "hex": "#808080"}


def get_image_tools():
    """Return CrewAI-compatible tools for image analysis."""
    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field

    class AnalyzeImageInput(BaseModel):
        image_path: str = Field(description="Path to image file")

    class AnalyzeImageTool(BaseTool):
        name: str = "analyze_property_image"
        description: str = "Analyze a property image: brightness, dimensions, dominant color, enhancement needs."
        args_schema: type = AnalyzeImageInput

        def _run(self, image_path: str) -> str:
            import asyncio
            skill = ImageAnalysisSkill()
            result = asyncio.run(skill.analyze_property_image(image_path))
            return json.dumps(result, ensure_ascii=False)

    class EnhanceImageInput(BaseModel):
        image_path: str = Field(description="Path to image file")
        output_path: str | None = Field(default=None, description="Output path")

    class EnhanceImageTool(BaseTool):
        name: str = "enhance_property_image"
        description: str = "Enhance a property image (brightness, contrast, sharpness)."
        args_schema: type = EnhanceImageInput

        def _run(self, image_path: str, output_path: str | None = None) -> str:
            import asyncio
            skill = ImageAnalysisSkill()
            result = asyncio.run(skill.enhance_image(image_path, output_path))
            return json.dumps(result, ensure_ascii=False)

    class CreateThumbnailInput(BaseModel):
        image_path: str = Field(description="Path to image file")

    class CreateThumbnailTool(BaseTool):
        name: str = "create_thumbnail"
        description: str = "Create a thumbnail of a property image for listings."
        args_schema: type = CreateThumbnailInput

        def _run(self, image_path: str) -> str:
            import asyncio
            skill = ImageAnalysisSkill()
            result = asyncio.run(skill.create_thumbnail(image_path))
            return json.dumps(result, ensure_ascii=False)

    return [AnalyzeImageTool(), EnhanceImageTool(), CreateThumbnailTool()]
