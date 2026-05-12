from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


NAVY = "#0F2238"
NAVY_SOFT = "#173553"
SEA_GREEN = "#1C8F72"
OLIVE = "#83AD64"
PAPER = "#F5F7F1"
MUTED = "#B8C6D2"


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/SFNS.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size, index=0)
            except OSError:
                continue
    return ImageFont.load_default()


def draw_logo(size: int, background: tuple[int, int, int, int] = (0, 0, 0, 0)) -> Image.Image:
    image = Image.new("RGBA", (size, size), background)
    draw = ImageDraw.Draw(image)

    pad = size * 0.09
    scale = (size - pad * 2) / 144

    def pt(x: float, y: float) -> tuple[float, float]:
        return (pad + x * scale, pad + y * scale)

    outer_width = max(6, round(11 * scale))
    inner_width = max(3, round(5.7 * scale))
    spine_width = max(2, round(4.2 * scale))
    dot_radius = max(3, round(3.1 * scale))

    doc_box = (*pt(42, 31), *pt(101, 113))
    draw.rounded_rectangle(doc_box, radius=round(12 * scale), outline=NAVY, width=outer_width)

    # Cover a small part of the top-left edge so the outline keeps the lighter
    # folded-document feeling from the source brand mark instead of a plain box.
    fold_cover = [pt(42, 31), pt(65, 31), pt(65, 52), pt(42, 52)]
    draw.polygon(fold_cover, fill=background)
    draw.line([pt(42, 52), pt(42, 113)], fill=NAVY, width=outer_width)
    draw.line([pt(42, 52), pt(63, 31), pt(101, 31)], fill=NAVY, width=outer_width)
    draw.line([pt(101, 31), pt(101, 113), pt(42, 113)], fill=NAVY, width=outer_width)

    spine_points = [pt(98, 39), pt(89, 47), pt(84.5, 59.5), pt(84.5, 72), pt(84.5, 86.5), pt(89.5, 99.5), pt(98, 106)]
    draw.line(spine_points, fill=SEA_GREEN, width=spine_width, joint="curve")
    draw.line([pt(62, 58), pt(83, 58)], fill=PAPER, width=inner_width)
    draw.line([pt(62, 76), pt(78, 76)], fill=PAPER, width=inner_width)
    draw.line([pt(62, 94), pt(84, 94)], fill=PAPER, width=inner_width)

    cx, cy = pt(84.5, 76)
    draw.ellipse((cx - dot_radius, cy - dot_radius, cx + dot_radius, cy + dot_radius), fill=SEA_GREEN)
    return image


def create_background(width: int, height: int) -> Image.Image:
    image = Image.new("RGB", (width, height), NAVY)
    pixels = image.load()
    for y in range(height):
        blend = y / max(height - 1, 1)
        r0, g0, b0 = ImageColorCache.rgb(NAVY)
        r1, g1, b1 = ImageColorCache.rgb(NAVY_SOFT)
        r2, g2, b2 = ImageColorCache.rgb(SEA_GREEN)
        if blend < 0.72:
            mix = blend / 0.72
            r = int(r0 + (r1 - r0) * mix)
            g = int(g0 + (g1 - g0) * mix)
            b = int(b0 + (b1 - b0) * mix)
        else:
            mix = (blend - 0.72) / 0.28
            r = int(r1 + (r2 - r1) * mix)
            g = int(g1 + (g2 - g1) * mix)
            b = int(b1 + (b2 - b1) * mix)
        for x in range(width):
            pixels[x, y] = (r, g, b)
    return image


class ImageColorCache:
    _cache: dict[str, tuple[int, int, int]] = {}

    @classmethod
    def rgb(cls, color: str) -> tuple[int, int, int]:
        if color not in cls._cache:
            cls._cache[color] = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))
        return cls._cache[color]


def create_sidebar(background: Image.Image, logo: Image.Image) -> Image.Image:
    canvas = background.copy()
    draw = ImageDraw.Draw(canvas)

    panel = (48, 54, canvas.width - 48, canvas.height - 54)
    draw.rounded_rectangle(panel, radius=34, fill=(255, 255, 255))

    logo_resized = logo.resize((216, 216), Image.Resampling.LANCZOS)
    canvas.alpha_composite(logo_resized, (panel[0] + 54, panel[1] + 56))

    title_font = load_font(56, bold=True)
    subtitle_font = load_font(24)
    meta_font = load_font(22)

    text_x = panel[0] + 56
    title_y = panel[1] + 316
    draw.text((text_x, title_y), "极口腔", fill=NAVY, font=title_font)
    draw.text((text_x, title_y + 82), "照片整理助手", fill=NAVY, font=title_font)
    draw.text((text_x, title_y + 170), "JIKEYAN PHOTO SORTING", fill=SEA_GREEN, font=subtitle_font)
    draw.line((text_x, title_y + 228, panel[2] - 56, title_y + 228), fill=(220, 229, 234), width=2)
    draw.text((text_x, title_y + 260), "Windows x64", fill=NAVY_SOFT, font=meta_font)
    draw.text((text_x, title_y + 296), "Offline clinical desktop utility", fill=NAVY_SOFT, font=meta_font)
    draw.text((text_x, panel[3] - 88), "极口腔品牌交付资产", fill=MUTED, font=meta_font)
    draw.text((text_x, panel[3] - 52), "Professional installer package", fill=MUTED, font=meta_font)

    return canvas.convert("RGB")


def create_small_banner(background: Image.Image, logo: Image.Image) -> Image.Image:
    canvas = background.copy()
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((28, 18, canvas.width - 28, canvas.height - 18), radius=26, fill=(255, 255, 255))

    logo_resized = logo.resize((84, 84), Image.Resampling.LANCZOS)
    canvas.alpha_composite(logo_resized, (46, 28))

    title_font = load_font(34, bold=True)
    subtitle_font = load_font(18)
    draw.text((150, 30), "极口腔照片整理助手", fill=NAVY, font=title_font)
    draw.text((152, 74), "JIKEYAN PHOTO SORTING", fill=SEA_GREEN, font=subtitle_font)
    return canvas.convert("RGB")


def main() -> None:
    asset_dir = Path(__file__).resolve().parent / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)

    primary_logo = draw_logo(512)

    icon_png = primary_logo.resize((512, 512), Image.Resampling.LANCZOS)
    icon_png.save(asset_dir / "jikeyan_app_icon.png")
    icon_png.save(
        asset_dir / "jikeyan_app_icon.ico",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )

    sidebar = create_sidebar(create_background(620, 980).convert("RGBA"), primary_logo)
    sidebar.save(asset_dir / "jikeyan_wizard_sidebar.bmp")

    banner = create_small_banner(create_background(620, 140).convert("RGBA"), primary_logo)
    banner.save(asset_dir / "jikeyan_wizard_small.bmp")

    print(f"generated assets in {asset_dir}")


if __name__ == "__main__":
    main()
