"""Upscaling low-quality card images with a local engine.

The default engine is upscayl-bin, the command-line runner inside Upscayl. It
runs the model at its native 4x, then the result is shrunk with Lanczos to the
size the caller wants, which takes the edge off GAN texture. Without an engine
the image is just resampled, and the result says so (fallback=True).
"""
from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
import time
from pathlib import Path

from PIL import Image

from ..cards import DATA_DIR, CardDataError

# The app's own copy carries macOS's quarantine flag, and App Management keeps us from clearing
# it there, so a quarantined upscayl-bin hangs at launch waiting for a Gatekeeper dialog. A copy
# under data/ can be cleared and runs headless. `install()` makes that copy.
APP_BIN = Path("/Applications/Upscayl.app/Contents/Resources/bin/upscayl-bin")
APP_MODELS = Path("/Applications/Upscayl.app/Contents/Resources/models")
LOCAL_DIR = DATA_DIR / "upscayl"
UPSCAYL_BIN = LOCAL_DIR / "upscayl-bin"
UPSCAYL_MODELS = LOCAL_DIR / "models"
COMMAND_ENV = "MTG_UPSCALE_COMMAND"
ENGINES = ("upscayl", "command", "none")
TIMEOUT_SECONDS = 600
_probed: dict[str, bool] = {}


def install() -> bool:
    """Copy upscayl-bin and its models from the app into data/upscayl and clear the quarantine flag."""
    if UPSCAYL_BIN.exists() and UPSCAYL_MODELS.exists():
        return True
    if not APP_BIN.exists():
        return False
    import shutil
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(APP_BIN, UPSCAYL_BIN)
    if not UPSCAYL_MODELS.exists():
        shutil.copytree(APP_MODELS, UPSCAYL_MODELS)
    subprocess.run(["xattr", "-dr", "com.apple.quarantine", str(LOCAL_DIR)], capture_output=True)
    return True


def _runs() -> bool:
    """Whether upscayl-bin starts here (a quarantined copy hangs instead of printing its help)."""
    key = str(UPSCAYL_BIN)
    if key not in _probed:
        try:
            done = subprocess.run([key, "-h"], capture_output=True, text=True, timeout=20)
            _probed[key] = "Usage" in (done.stdout + done.stderr)
        except (subprocess.TimeoutExpired, OSError):
            _probed[key] = False
    return _probed[key]


def detect(engine: str = "auto") -> str:
    """Resolve an engine name to "upscayl", "command" or "none".

    "auto" picks "command" when MTG_UPSCALE_COMMAND is set (a template with
    {input} {output} {model}), else "upscayl" when the binary exists, else
    "none". An explicit name is honoured, or raises if it cannot run here.
    """
    if engine == "auto":
        if os.environ.get(COMMAND_ENV):
            return "command"
        return "upscayl" if install() and _runs() else "none"
    if engine not in ENGINES:
        raise CardDataError(f"Unknown upscale engine {engine!r}; use auto, {', '.join(ENGINES)}.")
    if engine == "upscayl" and not (install() and _runs()):
        raise CardDataError(
            f"upscayl-bin is not usable ({UPSCAYL_BIN}). Install it with `brew install --cask upscayl`; "
            "if it is installed but hangs, open Upscayl once from Finder to approve it. "
            "Or use engine \"none\" for plain Lanczos resampling."
        )
    if engine == "command" and not os.environ.get(COMMAND_ENV):
        raise CardDataError(
            f"Engine \"command\" needs {COMMAND_ENV} set to a command template "
            "with {input} {output} {model}."
        )
    return engine


def _run(cmd: list[str]) -> None:
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise CardDataError(f"Upscaling timed out after {TIMEOUT_SECONDS} s: {shlex.join(cmd)}") from None
    except OSError as err:
        raise CardDataError(f"Could not run {cmd[0]}: {err}") from None
    if done.returncode != 0:
        lines = done.stderr.strip().splitlines()
        first = lines[0] if lines else f"exit code {done.returncode}"
        raise CardDataError(f"Upscaling failed ({first}). Command: {shlex.join(cmd)}")


def upscale(
    src: Path,
    dst: Path,
    *,
    model: str = "ultrasharp-4x",
    target_size: tuple[int, int],
    engine: str = "auto",
    tile: int = 0,
) -> dict:
    """Upscale src to target_size and save a PNG at dst.

    Returns {"engine", "model", "seconds", "fallback", "native_size"}, where
    native_size is the engine's own output size before the Lanczos step (the
    source size when the Lanczos fallback ran).
    """
    src, dst = Path(src), Path(dst)
    chosen = detect(engine)
    started = time.monotonic()
    dst.parent.mkdir(parents=True, exist_ok=True)

    if chosen == "none":
        with Image.open(src) as img:
            native = img.size
            img.convert("RGB").resize(target_size, Image.LANCZOS).save(dst, "PNG")
        return {
            "engine": "none", "model": None, "seconds": time.monotonic() - started,
            "fallback": True, "native_size": native,
        }

    with tempfile.TemporaryDirectory(prefix="upscale-", dir=dst.parent) as tmp:
        out = Path(tmp) / "native.png"
        if chosen == "upscayl":
            cmd = [
                str(UPSCAYL_BIN), "-i", str(src), "-o", str(out),
                "-m", str(UPSCAYL_MODELS), "-n", model, "-f", "png", "-t", str(tile),
            ]
        else:
            template = os.environ[COMMAND_ENV]
            cmd = shlex.split(template.format(input=str(src), output=str(out), model=model))
        _run(cmd)
        if not out.exists():
            raise CardDataError(f"The upscaler produced no output. Command: {shlex.join(cmd)}")
        with Image.open(out) as native_img:
            native = native_img.size
            native_img.convert("RGB").resize(target_size, Image.LANCZOS).save(dst, "PNG")
    return {
        "engine": chosen, "model": model, "seconds": time.monotonic() - started,
        "fallback": False, "native_size": native,
    }
