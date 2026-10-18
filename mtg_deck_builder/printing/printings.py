"""Candidate images for a card, from two sources, and the ranking that picks one.

Source A is the mpcfill.com index of community renders (print-ready, 800 to 1200 dpi,
bleed included). Source B is every Scryfall printing in the local index (real scans,
745x1040 px, no bleed). The weights come from docs/spec/print-suite.md, "Scoring".
"""
from __future__ import annotations

import re
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path

from .. import cards
from ..cards import DATA_DIR, CardDataError
from . import mpcfill

SCRYFALL_DPI = 300
FANCY_EFFECTS = {"showcase", "extendedart"}
BAD_BORDERS = {"gold", "silver", "white"}
USER_AGENT = "mtg-deck-builder/0.1 (+https://github.com/AshleyxAdamson/MTG-Deck-Builder)"
SCRYFALL_DIR = DATA_DIR / "art" / "scryfall"
# Weights per style: (render that looks fancy, other render, borderless, full_art, showcase/extended,
# inverted, universes beyond, plain 2015 frame, newest-per-year)
WEIGHTS = {
    "fullart":    {"fancy_render": 6, "render": 4, "borderless": 3, "full_art": 3, "showcase": 2, "inverted": 1, "ub": -2, "plain": 0, "year": 0},
    "borderless": {"fancy_render": 6, "render": 3, "borderless": 4, "full_art": 2, "showcase": 1, "inverted": 1, "ub": -2, "plain": 0, "year": 0},
    "classic":    {"fancy_render": 0, "render": 0, "borderless": -5, "full_art": -5, "showcase": -5, "inverted": -5, "ub": -5, "plain": 3, "year": 0},
    "newest":     {"fancy_render": 0, "render": 0, "borderless": 0, "full_art": 0, "showcase": 0, "inverted": 0, "ub": 0, "plain": 0, "year": 1},
}
LOW_DPI = 600
_last_scryfall_request = 0.0

# Style keys. A render's mpcfill tags (canonical names and their ancestors) map through TAG_STYLES;
# words in its name map through NAME_STYLES, because only about a fifth of renders are tagged.
TAG_STYLES = {
    "borderless": "borderless", "post-2023 borderless": "borderless", "extended-art": "extended",
    "showcase": "showcase", "retro": "retro", "modern": "modern", "m15": "m15", "full text": "full-text",
    "custom-made frame": "custom-frame", "minimalist": "minimalist", "futureshifted": "futureshifted",
    "planeshifted": "planeshifted", "fnm promo": "promo", "foil-etched": "etched",
    "universes beyond": "universes-beyond", "universe": "universes-beyond", "full-art": "full-art",
    "custom art": "custom-art", "ai art": "ai-art", "ai remaster": "ai-art", "altered art": "altered",
    "pixel art": "pixel", "pop-out art": "pop-out", "sketch art": "sketch", "upscaled scan": "upscaled-scan",
    "textless": "textless", "secret lair": "secret-lair", "zeta": "textless", "non-black border": "non-black-border",
    "alternate name": "alt-name", "nsfw": "nsfw", "eternal night card": "altered",
}
NAME_STYLES = {
    "borderless": "borderless", "extended": "extended", "ext": "extended", "showcase": "showcase",
    "min": "minimalist", "minimalist": "minimalist", "textless": "textless", "sketch": "sketch",
    "trixified": "custom-frame", "blackout": "custom-frame", "full art": "full-art", "fullart": "full-art",
    "retro": "retro", "ancient": "retro", "classic": "retro", "modern": "modern", "promo": "promo",
    "pop-out": "pop-out", "popout": "pop-out", "pixel": "pixel", "ai": "ai-art", "storybook": "showcase",
    "book": "showcase", "nsfw": "nsfw", "upscaled": "upscaled-scan", "secret lair": "secret-lair", "sld": "secret-lair",
}
# A render with any of these does not look like an ordinary Magic card: no cost or rules box.
NON_STANDARD = {"minimalist", "textless", "custom-frame", "altered", "sketch", "pop-out", "pixel"}
# What lands may be anyway: a land has no cost and its rules are simple.
LAND_OK = {"textless", "minimalist", "full-art"}
IMPLIED = {"minimalist": "custom-frame", "sketch": "altered", "pop-out": "altered", "pixel": "altered", "ai-art": "custom-art"}


def styles_of(label: str, tags: list[str], aliases: dict | None = None) -> set[str]:
    """Style keys for a render, from its tags and the words in its name."""
    styles: set[str] = set()
    aliases = aliases if aliases is not None else {}
    for tag in tags or []:
        canonical, ancestors = aliases.get(tag.lower(), (tag, []))
        for name in [canonical, *ancestors]:
            if name.lower() in TAG_STYLES:
                styles.add(TAG_STYLES[name.lower()])
    text = label.lower()
    inside = " ".join(re.findall(r"\(([^()]*)\)|\[([^\[\]]*)\]", text) and
                      [a or b for a, b in re.findall(r"\(([^()]*)\)|\[([^\[\]]*)\]", text)])
    for phrase in ("full art", "secret lair", "pop-out"):
        if phrase in text:
            styles.add(NAME_STYLES[phrase])
    for word in re.split(r"[\s,/_.-]+", inside):
        if word in NAME_STYLES and word not in ("ai",):
            styles.add(NAME_STYLES[word])
    if re.search(r"\(\s*min\b|\bmin-\s", text):
        styles.add("minimalist")
    if re.search(r"\bai\b", inside):
        styles.add("ai-art")
    for key, implied in IMPLIED.items():
        if key in styles:
            styles.add(implied)
    return styles


def is_standard(styles: set[str], land: bool = False) -> bool:
    bad = NON_STANDARD - (LAND_OK if land else set())
    return not (styles & bad)


def scryfall_candidates(db: sqlite3.Connection, oracle_id: str, allow_lowres: bool = False) -> list[dict]:
    """Printings worth printing: English paper cards with a real scan and a black or no border."""
    found = []
    for p in cards.printings_of(db, oracle_id):
        if not p["paper"] or p["digital"] or p["oversized"] or p["lang"] != "en" or not p["image_png"]:
            continue
        if p["border_color"] in BAD_BORDERS:
            continue
        lowres = p["image_status"] != "highres_scan"
        if lowres and not allow_lowres:
            continue
        effects = set(p["frame_effects"])
        flags = []
        if p["border_color"] == "borderless":
            flags.append("borderless")
        if p["full_art"] or "fullart" in effects:
            flags.append("full art")
        flags.extend(sorted(effects & FANCY_EFFECTS))
        if "inverted" in effects:
            flags.append("inverted")
        if p["textless"]:
            flags.append("textless")
        if lowres:
            flags.append("low res")
        label = f"{p['set_code'].upper()} {p['collector_number']}, {p['artist'] or 'unknown artist'}"
        if flags:
            label += f" ({', '.join(flags)})"
        styles = set()
        if p["border_color"] == "borderless":
            styles.add("borderless")
        if p["full_art"] or "fullart" in effects:
            styles.add("full-art")
        if effects & FANCY_EFFECTS:
            styles.add("showcase" if "showcase" in effects else "extended")
        if p["textless"]:
            styles.add("textless")
        if p["frame"] in ("1993", "1997"):
            styles.add("retro")
        elif p["frame"] == "2003":
            styles.add("modern")
        elif p["frame"] == "2015":
            styles.add("m15")
        if "universesbeyond" in p["promo_types"]:
            styles.add("universes-beyond")
        if p["set_type"] == "promo" or any(t in p["promo_types"] for t in ("fnm", "promopack", "setpromo")):
            styles.add("promo")
        found.append({
            "styles": sorted(styles),
            "source": "scryfall",
            "id": p["scryfall_id"],
            "name": p["name"],
            "label": label,
            "artist": p["artist"],
            "set": p["set_code"],
            "collector_number": p["collector_number"],
            "released_at": p["released_at"],
            "dpi": SCRYFALL_DPI if not lowres else 200,
            "fancy": bool(flags) and flags != ["inverted"] and "low res" not in flags,
            "borderless": p["border_color"] == "borderless",
            "full_art": bool(p["full_art"]) or "fullart" in effects,
            "showcase": bool(effects & FANCY_EFFECTS),
            "inverted": "inverted" in effects,
            "universes_beyond": "universesbeyond" in p["promo_types"],
            "plain": p["frame"] == "2015" and p["border_color"] == "black" and not effects and not p["full_art"],
            "lowres": lowres,
            "thumb": p["image_normal"],
            "large": p["image_large"] or p["image_png"],
            "png": p["image_png"],
            "back_png": p["back_png"],
            "layout": p["layout"],
        })
    return found


def mpcfill_candidates(names: list[str], source_names: list[str] | None, card_type: str = "CARD") -> dict[str, list[dict]]:
    """Community renders for many names at once: {name: [candidate, ...]} in mpcfill's ranking."""
    if not names:
        return {}
    results = mpcfill.search(names, source_names, card_type=card_type)
    ids = [i for hits in results.values() for i in hits]
    meta = mpcfill.cards(ids) if ids else {}
    try:
        aliases = mpcfill.tag_aliases()
    except CardDataError:
        aliases = {}
    found: dict[str, list[dict]] = {}
    for name in names:
        key = mpcfill_key(name)
        found[name] = []
        for drive_id in results.get(key, []):
            card = meta.get(drive_id)
            if not card:
                continue
            fancy = mpcfill.is_fancy(card)
            styles = styles_of(card["name"], card.get("tags") or [], aliases)
            found[name].append({
                "styles": sorted(styles),
                "universes_beyond_tag": "universes-beyond" in styles,
                "source": "mpcfill",
                "id": drive_id,
                "name": name,
                "label": card["name"],
                "artist": _artist_from_label(card["name"]),
                "dpi": int(card.get("dpi") or 0),
                "fancy": fancy,
                "universes_beyond": "universes-beyond" in styles,
                "plain": False,
                "lowres": int(card.get("dpi") or 0) < LOW_DPI,
                "thumb": mpcfill.thumbnail_url(drive_id, 400),
                "large": mpcfill.thumbnail_url(drive_id, 800),
                "extension": card.get("extension"),
                "size": card.get("size"),
                "render_source": card.get("sourceName"),
                "tags": card.get("tags") or [],
            })
    return found


def mpcfill_key(name: str) -> str:
    return name.split(" // ")[0].lower()


def _artist_from_label(label: str) -> str | None:
    """'Cultivate (Borderless Uichi Ukumo)' -> 'Uichi Ukumo', when the parentheses end in a name."""
    match = re.search(r"\(([^()]*)\)\s*$", label)
    if not match:
        return None
    words = match[1].replace("Borderless", "").replace("Full Art", "").replace("Extended", "").replace("Showcase", "").split()
    words = [w for w in words if not w.isdigit() and w not in ("-", "Art", "Textless")]
    return " ".join(words) if 1 < len(words) <= 4 else None


def score(candidate: dict, style: str) -> float:
    w = WEIGHTS[style]
    points = 0.0
    if candidate["source"] == "mpcfill":
        points += w["fancy_render"] if candidate["fancy"] else w["render"]
    else:
        if candidate.get("borderless"):
            points += w["borderless"]
        if candidate.get("full_art"):
            points += w["full_art"]
        if candidate.get("showcase"):
            points += w["showcase"]
        if candidate.get("inverted"):
            points += w["inverted"]
        if candidate.get("plain"):
            points += w["plain"]
        if w["year"] and candidate.get("released_at"):
            points += w["year"] * (int(candidate["released_at"][:4]) - 2000) / 10
    if candidate.get("universes_beyond"):
        points += w["ub"]
    if candidate.get("dpi", 0) < LOW_DPI:
        points -= 2
    if candidate.get("lowres"):
        points -= 10
    return points


def rank(candidates: list[dict], style: str, *, artist: str | None = None, set_code: str | None = None,
         hide_ub: bool = False, exclude_styles: set[str] | None = None, land: bool = False) -> list[dict]:
    """Best first. Pins (artist, set) go to the top; ties break on dpi, then newest.

    Candidates carrying an excluded style are dropped; a land keeps the styles in LAND_OK.
    """
    excluded = set(exclude_styles or ()) - (LAND_OK if land else set())

    def key(c: dict):
        pinned = (artist and (c.get("artist") or "").lower() == artist.lower()) or \
                 (set_code and (c.get("set") or "").lower() == set_code.lower())
        return (not pinned, -score(c, style), -c.get("dpi", 0), c.get("released_at") or "")
    kept = [c for c in candidates if not (hide_ub and c.get("universes_beyond"))
            and not (set(c.get("styles") or ()) & excluded)]
    ordered = sorted(kept, key=key)
    for position, c in enumerate(ordered):
        c["score"] = score(c, style)
        c["rank"] = position
        c["standard"] = is_standard(set(c.get("styles") or ()), land)
    return ordered


def download_scryfall(candidate: dict, back: bool = False) -> Path:
    """Fetch a printing's PNG from Scryfall's image host (no rate limit there) into data/art/scryfall."""
    global _last_scryfall_request
    url = candidate["back_png"] if back else candidate["png"]
    if not url:
        raise CardDataError(f"{candidate['name']} has no {'back' if back else 'front'} image on Scryfall.")
    SCRYFALL_DIR.mkdir(parents=True, exist_ok=True)
    dest = SCRYFALL_DIR / f"{candidate['id']}{'-back' if back else ''}.png"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    wait = 0.1 - (time.monotonic() - _last_scryfall_request)
    if wait > 0:
        time.sleep(wait)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "image/png,*/*"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
    except (urllib.error.URLError, OSError) as error:
        raise CardDataError(f"Could not download {url}: {error}")
    finally:
        _last_scryfall_request = time.monotonic()
    if not data.startswith(b"\x89PNG"):
        raise CardDataError(f"{url} did not return a PNG.")
    part = dest.with_suffix(".part")
    part.write_bytes(data)
    part.replace(dest)
    return dest
