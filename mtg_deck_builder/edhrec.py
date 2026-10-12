"""Deck ideas from EDHREC: what other players run with a commander.

Unlike the rest of the package this needs the internet. EDHREC has no bulk download,
so a commander's page is fetched the first time it is asked for and cached under
data/edhrec/. The endpoint is unofficial and may change without notice.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
import unicodedata
import urllib.error
import urllib.request

from .cards import DATA_DIR, CardDataError, _find_card

PAGES = "https://json.edhrec.com/pages/commanders"
USER_AGENT = "mtg-deck-builder/0.1 (+https://github.com/AshleyxAdamson/MTG-Deck-Builder)"
CACHE_DIR = DATA_DIR / "edhrec"
CACHE_SECONDS = 7 * 24 * 3600
TIMEOUT = 30
AVERAGE_DECK = ("creature", "instant", "sorcery", "artifact", "enchantment", "planeswalker", "land")


def _slug(name: str) -> str:
    """EDHREC's page name for a card: 'Elenda, the Dusk Rose' -> 'elenda-the-dusk-rose'."""
    front = name.split(" // ")[0]
    plain = unicodedata.normalize("NFKD", front).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", plain.replace("'", "")).strip("-")


def _page(path: str) -> tuple[dict, float]:
    """A page and when it was fetched, from the cache when that is recent enough."""
    cached = CACHE_DIR / f"{path}.json"
    if cached.exists() and time.time() - cached.stat().st_mtime < CACHE_SECONDS:
        return json.loads(cached.read_text(encoding="utf-8")), cached.stat().st_mtime
    request = urllib.request.Request(
        f"{PAGES}/{path}.json", headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        # EDHREC answers 403, not 404, for a page that does not exist.
        raise CardDataError(f"EDHREC has no page for {path!r} (HTTP {error.code}).")
    except (urllib.error.URLError, TimeoutError) as error:
        # Offline: an old copy is better than nothing.
        if cached.exists():
            return json.loads(cached.read_text(encoding="utf-8")), cached.stat().st_mtime
        raise CardDataError(f"Could not reach EDHREC ({getattr(error, 'reason', error)}); this lookup needs the internet.")
    page = json.loads(body)
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(body)
    return page, time.time()


def commander_ideas(
    db: sqlite3.Connection,
    commander: str,
    theme: str | None = None,
    per_list: int = 12,
    price_max: float | None = None,
) -> dict:
    """The cards most played with a commander, optionally within one theme of its decks."""
    name = _find_card(db, commander)["name"]
    slug = _slug(name)
    main, fetched = _page(slug)
    themes = [{"theme": t["slug"], "name": t["value"], "decks": t["count"]} for t in main["panels"]["taglinks"]]
    page = main
    if theme:
        match = next((t for t in themes if _slug(theme) in (t["theme"], _slug(t["name"]))), None)
        if not match:
            raise CardDataError(
                f"EDHREC has no {theme!r} theme for {name}. Themes: {', '.join(t['theme'] for t in themes[:25])}")
        theme = match["theme"]
        page, fetched = _page(f"{slug}/{theme}")

    def idea(view: dict) -> dict | None:
        try:
            row = _find_card(db, view["name"])
        except CardDataError:
            return None
        if price_max is not None and (row["price_usd"] is None or row["price_usd"] > price_max):
            return None
        card = {
            "name": row["name"],
            # Share of this commander's decks that run the card.
            "in_decks_pct": round(100 * view["num_decks"] / view["potential_decks"]) if view.get("potential_decks") else None,
            # How much more often than in other decks of these colors; high means specific to this commander.
            "synergy_pct": round(100 * view["synergy"]) if view.get("synergy") is not None else None,
            "mana_cost": row["mana_cost"],
            "type_line": row["type_line"],
            "price_usd": row["price_usd"],
        }
        return {key: value for key, value in card.items() if value not in (None, "")}

    lists = {}
    for cardlist in page["container"]["json_dict"]["cardlists"]:
        ideas = []
        for view in cardlist["cardviews"]:
            if len(ideas) == per_list:
                break
            if card := idea(view):
                ideas.append(card)
        if ideas:
            lists[cardlist["header"]] = ideas
    return {
        "commander": name,
        "theme": theme,
        "decks": page["container"]["json_dict"]["card"].get("num_decks"),
        "themes": themes[:20],
        "average_deck": {kind: page[kind] for kind in AVERAGE_DECK if kind in page},
        "decks_by_bracket": main.get("bracket_counts"),
        "similar_commanders": main.get("similar"),
        # Combos EDHREC sees most with this commander; worth knowing when a brief forbids them.
        "known_combos": [combo["value"] for combo in main["panels"].get("combocounts", []) if " + " in combo["value"]],
        "lists": lists,
        "source": f"https://edhrec.com/commanders/{slug}" + (f"/{theme}" if theme else ""),
        "fetched": time.strftime("%Y-%m-%d", time.localtime(fetched)),
    }
