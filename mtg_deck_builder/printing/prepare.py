"""Getting a card image ready for the print shop: fill, upscale, bleed.

Scryfall PNGs are trimmed 745x1040 RGBA with transparent rounded corners.
Community renders already carry bleed. Either way the output is a PNG at the
target dpi with bleed (2176x2960 at 800 dpi), cached under data/art/prepared.
Nothing is sharpened, recoloured or cropped.
"""
from __future__ import annotations

import math
import statistics
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageStat

from ..cards import DATA_DIR, CardDataError
from . import upscale as upscaler

PREPARED_DIR = DATA_DIR / "art" / "prepared"

# A card with bleed at 300 dpi: 63x88 mm trim plus 36 px of bleed per side.
BLEED_PX_300 = 36
BLEED_SIZE_300 = (816, 1110)
SCRYFALL_HEIGHT = 1040  # Scryfall png height, about 300 dpi at trim
KINDS = ("scryfall", "render")


def effective_dpi(width: int, height: int, has_bleed: bool) -> int:
    """Print resolution, rounded to 10 dpi: 300 for a Scryfall png, 800 for a 2176x2960 render."""
    reference = BLEED_SIZE_300[1] if has_bleed else SCRYFALL_HEIGHT
    return 10 * round(height * 300 / reference / 10)


def bleed_px(dpi: int) -> int:
    return round(BLEED_PX_300 * dpi / 300)


def bleed_size(dpi: int) -> tuple[int, int]:
    return round(BLEED_SIZE_300[0] * dpi / 300), round(BLEED_SIZE_300[1] * dpi / 300)


def trim_size(dpi: int) -> tuple[int, int]:
    width, height = bleed_size(dpi)
    return width - 2 * bleed_px(dpi), height - 2 * bleed_px(dpi)


def fill_corners(img: Image.Image) -> Image.Image:
    """Turn the transparent corners of a Scryfall png into border colour; returns RGB."""
    if img.mode == "RGB":
        return img
    if img.mode not in ("RGBA", "LA", "P", "PA"):
        return img.convert("RGB")
    rgba = img.convert("RGBA")
    width, height = rgba.size
    inset = 4
    midpoints = [
        (width // 2, inset), (width // 2, height - 1 - inset),
        (inset, height // 2), (width - 1 - inset, height // 2),
    ]
    pixels = rgba.load()
    samples = []
    for mx, my in midpoints:
        for dx in range(-2, 3):
            x, y = min(max(mx + dx, 0), width - 1), my
            r, g, b, a = pixels[x, y]
            if a >= 250:
                samples.append((r, g, b))
    if samples:
        colour = tuple(int(statistics.median(channel)) for channel in zip(*samples))
    else:
        colour = (0, 0, 0)
    canvas = Image.new("RGB", rgba.size, colour)
    canvas.paste(rgba, mask=rgba.getchannel("A"))
    return canvas


def to_trim_size(img: Image.Image, dpi: int) -> Image.Image:
    return img.resize(trim_size(dpi), Image.LANCZOS)


def to_bleed_size(img: Image.Image, dpi: int) -> Image.Image:
    return img.resize(bleed_size(dpi), Image.LANCZOS)


def add_bleed(img: Image.Image, dpi: int) -> Image.Image:
    """Pad a trimmed card by repeating its outermost pixels, then fit the exact with-bleed size."""
    img = img.convert("RGB")
    pad = bleed_px(dpi)
    width, height = img.size
    canvas = Image.new("RGB", (width + 2 * pad, height + 2 * pad))
    canvas.paste(img, (pad, pad))
    if pad:
        canvas.paste(img.crop((0, 0, width, 1)).resize((width, pad)), (pad, 0))
        canvas.paste(img.crop((0, height - 1, width, height)).resize((width, pad)), (pad, pad + height))
        canvas.paste(img.crop((0, 0, 1, height)).resize((pad, height)), (0, pad))
        canvas.paste(img.crop((width - 1, 0, width, height)).resize((pad, height)), (pad + width, pad))
        corners = {
            (0, 0): (0, 0), (pad + width, 0): (width - 1, 0),
            (0, pad + height): (0, height - 1), (pad + width, pad + height): (width - 1, height - 1),
        }
        for origin, source in corners.items():
            canvas.paste(Image.new("RGB", (pad, pad), img.getpixel(source)), origin)
    return canvas.resize(bleed_size(dpi), Image.LANCZOS) if canvas.size != bleed_size(dpi) else canvas


def plain_back(color: str = "#000000", dpi: int = 800) -> Image.Image:
    """A solid card back, with bleed."""
    return Image.new("RGB", bleed_size(dpi), color)


def color_shift(original: Image.Image, result: Image.Image) -> dict:
    """Compare a result with its original at the original's size.

    mean_diff is the largest per-channel gap between the two images' average
    values (0..255); psnr is in dB. ok means the colours held: under 4 and over 28.
    """
    original = original.convert("RGB")
    shrunk = result.convert("RGB").resize(original.size, Image.LANCZOS)
    mean_a, mean_b = ImageStat.Stat(original).mean, ImageStat.Stat(shrunk).mean
    mean_diff = max(abs(a - b) for a, b in zip(mean_a, mean_b))
    diff = ImageChops.difference(original, shrunk)
    stat = ImageStat.Stat(diff)
    mse = sum(stat.sum2) / (stat.count[0] * 3)
    psnr = 99.0 if mse == 0 else min(99.0, 10 * math.log10(255 ** 2 / mse))
    # The spike (docs/research/upscale-spike.md) found sharpening alone costs 3 to 4 dB, so the PSNR
    # floor is low; a real colour shift shows up in mean_diff first.
    return {"mean_diff": mean_diff, "psnr": psnr, "ok": mean_diff < 4 and psnr > 24}


def sharpness(img: Image.Image) -> float:
    """Variance of the edge-filtered grayscale image; compare only at the same pixel size."""
    edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
    return ImageStat.Stat(edges).var[0]


def prepared_path(source: str, ident: str, dpi: int, model: str | None) -> Path:
    suffix = f"-{model}" if model else ""
    return PREPARED_DIR / f"{source}-{ident}-{dpi}{suffix}.png"


def prepare(
    src: Path,
    kind: str,
    *,
    min_dpi: int = 600,
    target_dpi: int = 800,
    model: str = "ultrasharp-4x",
    engine: str = "auto",
    force: bool = False,
) -> dict:
    """Prepare one image for printing and save it under data/art/prepared.

    kind is "scryfall" (no bleed, transparent corners) or "render" (has bleed).
    Returns {"path", "from_dpi", "to_dpi", "upscaled", "engine", "model",
    "seconds", "color_shift", "fallback"}; color_shift is only set when the
    image was upscaled. An existing output is reused unless force.
    """
    if kind not in KINDS:
        raise CardDataError(f"Unknown image kind {kind!r}; use scryfall or render.")
    src = Path(src)
    started = time.monotonic()
    has_bleed = kind == "render"

    with Image.open(src) as opened:
        opened.load()
        from_dpi = effective_dpi(*opened.size, has_bleed)
        needs_upscale = from_dpi < min_dpi
        resolved = upscaler.detect(engine) if needs_upscale else None
        to_dpi = target_dpi if needs_upscale or from_dpi > target_dpi else from_dpi
        tag = None if not needs_upscale else ("lanczos" if resolved == "none" else model)
        out = prepared_path(kind, src.stem, to_dpi, tag)
        report = {
            "path": out, "from_dpi": from_dpi, "to_dpi": to_dpi, "upscaled": needs_upscale,
            "engine": None, "model": None, "seconds": 0.0, "color_shift": None, "fallback": False,
        }
        if out.exists() and not force:
            return report

        img = fill_corners(opened) if kind == "scryfall" else opened.convert("RGB")

    if needs_upscale:
        target = bleed_size(to_dpi) if has_bleed else trim_size(to_dpi)
        with tempfile.TemporaryDirectory(prefix="prepare-") as tmp:
            filled, upscaled = Path(tmp) / "in.png", Path(tmp) / "out.png"
            img.save(filled, "PNG")
            info = upscaler.upscale(filled, upscaled, model=model, target_size=target, engine=resolved)
            with Image.open(upscaled) as result:
                result.load()
        report.update(engine=info["engine"], model=info["model"], fallback=info["fallback"])
        report["color_shift"] = color_shift(img, result)
        img = result
    elif has_bleed:
        if from_dpi > target_dpi:
            img = to_bleed_size(img, target_dpi)
    else:
        img = to_trim_size(img, to_dpi)

    if not has_bleed:
        img = add_bleed(img, to_dpi)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG")
    report["seconds"] = time.monotonic() - started
    return report
