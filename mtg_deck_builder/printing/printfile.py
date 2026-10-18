"""The deck's print file: `<deck>.print.toml`, one chosen printing per card.

It sits next to the decklist, so it lives in the user's decks repo and survives
sessions. `mtg art` writes it, the gallery edits it, `mtg print` reads it.
The file format is described in docs/spec/print-suite.md.
"""
from __future__ import annotations

import tomllib
from datetime import date
from pathlib import Path

from ..cards import CardDataError

STYLES = ("fullart", "borderless", "classic", "newest")
UPSCALE_MODES = ("auto", "never", "always")

DEFAULTS = {
    "style": "fullart",
    "stock": "(S33) Superior Smooth",
    "foil": False,
    "cardback": {"kind": "plain", "color": "#000000"},
    "basics": "vary",
    "upscale": {"engine": "auto", "model": "ultrasharp-4x", "min_dpi": 600, "target_dpi": 800},
    # Styles never chosen or shown. Lands keep textless, minimalist and full-art anyway (see printings.LAND_OK).
    # novelty-frame: unlabelled renders from the drives that make non-standard frames (pixel fonts, parchment,
    # stained glass). Minimalist, custom frames, altered art and odd borders are allowed.
    # prefer: official Japanese alternate art (English text) ranks first.
    "styles": {"exclude": ["novelty-frame", "sketch", "pixel", "textless", "nsfw"], "languages": ["EN"],
               "prefer": ["japanese"]},
    "hidden": [],   # render ids or source names the user hid in the gallery
}


def path_for(decklist: Path) -> Path:
    """decks/treefolk.txt -> decks/treefolk.print.toml"""
    return decklist.with_suffix(".print.toml")


def new(decklist: Path, **settings) -> dict:
    """An empty print file for a decklist, with the defaults filled in."""
    data = {
        "deck": decklist.name,
        "written": date.today().isoformat(),
        **{key: (dict(value) if isinstance(value, dict) else value) for key, value in DEFAULTS.items()},
        "sources": [],
        "cards": [],
    }
    data.update({key: value for key, value in settings.items() if value is not None})
    return data


def load(path: Path) -> dict:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise CardDataError(f"Cannot read {path}: {error.strerror}")
    except tomllib.TOMLDecodeError as error:
        raise CardDataError(f"{path} is not valid TOML: {error}")
    for key, value in DEFAULTS.items():
        data.setdefault(key, dict(value) if isinstance(value, dict) else value)
    data.setdefault("cards", [])
    return data


def save(data: dict, path: Path) -> None:
    path.write_text(dumps(data), encoding="utf-8")


def card_entry(data: dict, name: str) -> dict | None:
    return next((card for card in data["cards"] if card["name"] == name), None)


# --- A small TOML writer. The standard library reads TOML but does not write it. ---

def _scalar(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_scalar(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{_key(k)} = {_scalar(v)}" for k, v in value.items()) + " }"
    if value is None:
        raise ValueError("TOML has no null; leave the key out instead")
    raise TypeError(f"Cannot write {type(value).__name__} to TOML")


def _key(key: str) -> str:
    return key if key.replace("-", "").replace("_", "").isalnum() and key.isascii() else _scalar(key)


def dumps(data: dict) -> str:
    """Write a print file: scalars first, then tables, then the [[cards]] and other arrays of tables."""
    lines = [f"# Written by mtg art on {data.get('written', date.today().isoformat())}. "
             "Edited by the gallery; `mtg art --keep` fills gaps only. See docs/spec/print-suite.md."]
    tables, arrays = [], []
    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
            arrays.append((key, value))
        elif isinstance(value, dict) and any(isinstance(v, (dict, list)) for v in value.values()) and key != "cardback":
            tables.append((key, value))
        else:
            lines.append(f"{_key(key)} = {_scalar(value)}")
    for key, value in tables:
        lines.append(f"\n[{_key(key)}]")
        lines.extend(f"{_key(k)} = {_scalar(v)}" for k, v in value.items() if v is not None)
    for key, items in arrays:
        for item in items:
            lines.append(f"\n[[{_key(key)}]]")
            lines.extend(f"{_key(k)} = {_scalar(v)}" for k, v in item.items() if v is not None)
    return "\n".join(lines) + "\n"
