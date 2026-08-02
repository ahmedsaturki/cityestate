"""Generate placeholder icons for CityEstate Bridge Extension."""
from PIL import Image, ImageDraw, ImageFont
import os

ICON_DIR = os.path.join(os.path.dirname(__file__), "icons")
os.makedirs(ICON_DIR, exist_ok=True)

SIZES = [16, 48, 128]

for size in SIZES:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Green circle background
    padding = max(1, size // 16)
    draw.ellipse([padding, padding, size - padding, size - padding], fill=(37, 211, 102, 255))

    # White "C" letter
    font_size = size // 2
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()

    text = "C"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - bbox[1]
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

    img.save(os.path.join(ICON_DIR, f"icon{size}.png"))
    print(f"Created icon{size}.png")

print("Done!")
