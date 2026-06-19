"""Generate placeholder avatar PNGs for each participant."""
import os
from PIL import Image, ImageDraw, ImageFont

PARTICIPANTS = [
    "ivan", "raquel", "adrián", "soni", "ale", "arturo",
    "andrés", "nati", "ame", "mariana", "janet", "juan", "tony", "luis adrián",
]
DISPLAY = {"mariana": "Mari", "luis adrián": "Luis"}
PALETTE = [
    "#e41a1c", "#377eb8", "#4daf4a", "#984ea3",
    "#ff7f00", "#a65628", "#f781bf", "#008080",
    "#66c2a5", "#e6ab02", "#7570b3", "#d95f02",
    "#1b9e77", "#e7298a",
]
COLORS = {p: PALETTE[i] for i, p in enumerate(PARTICIPANTS)}

FONT_PATHS = [
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Geneva.ttf",
    "/Library/Fonts/Arial.ttf",
]


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def get_font(size):
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def display_name(p):
    return DISPLAY.get(p, p.title())


def create_avatar(participant, out_path, size=200):
    color_rgb = hex_to_rgb(COLORS[participant])
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Filled circle with a slightly lighter border
    r, g, b = color_rgb
    lighter = (min(r + 40, 255), min(g + 40, 255), min(b + 40, 255))
    draw.ellipse([0, 0, size - 1, size - 1], fill=lighter)
    draw.ellipse([6, 6, size - 7, size - 7], fill=color_rgb)

    # Initials
    name = display_name(participant)
    initials = "".join(w[0].upper() for w in name.split()[:2])
    font = get_font(int(size * 0.42))

    bbox = draw.textbbox((0, 0), initials, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (size - tw) // 2 - bbox[0]
    y = (size - th) // 2 - bbox[1]
    # Subtle shadow
    draw.text((x + 2, y + 2), initials, fill=(0, 0, 0, 80), font=font)
    draw.text((x, y), initials, fill=(255, 255, 255, 240), font=font)

    # Save as RGB PNG
    out = Image.new("RGB", (size, size), (245, 245, 245))
    out.paste(img, mask=img.split()[3])
    out.save(out_path)
    print(f"  ✓ {out_path}")


if __name__ == "__main__":
    os.makedirs("assets", exist_ok=True)
    print("Generating placeholder avatars...")
    for p in PARTICIPANTS:
        create_avatar(p, f"assets/{p}.png")
    print("Done.")
