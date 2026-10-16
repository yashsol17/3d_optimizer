"""Generate the application icon (desktop/icon.ico) — a copper wireframe globe on black."""
import math
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "icon.ico")

SIZE = 512
BG = (5, 5, 6, 255)
COPPER = (226, 130, 92, 255)


def draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), BG)
    d = ImageDraw.Draw(img)
    cx = cy = size / 2
    r = size * 0.34
    w = max(1, round(size / 170))

    # latitude rings, squashed to suggest a sphere
    for i in range(1, 5):
        f = i / 5
        ry = r * math.cos(f * math.pi / 2)
        off = r * math.sin(f * math.pi / 2) * 0.62
        for sign in (-1, 1):
            d.ellipse([cx - r * math.cos(f * math.pi / 2) * 0 - r, cy + sign * off - ry * 0.62,
                       cx + r, cy + sign * off + ry * 0.62], outline=COPPER, width=w)

    # equator + outline
    d.ellipse([cx - r, cy - r * 0.62, cx + r, cy + r * 0.62], outline=COPPER, width=w)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=COPPER, width=w + 1)

    # longitude arcs
    for f in (0.35, 0.7):
        rx = r * f
        d.ellipse([cx - rx, cy - r, cx + rx, cy + r], outline=COPPER, width=w)
    d.line([cx, cy - r, cx, cy + r], fill=COPPER, width=w)

    return img


def main() -> None:
    master = draw(SIZE)
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    master.save(OUT, format="ICO", sizes=sizes)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
