"""`mtg art`: choose a printing for every card in a decklist and write the print file.

Printed cards come from the ledger and are locked. New cards get the best candidate
for the chosen style: a community render when one exists, else a Scryfall printing.
Tokens the deck makes are added. See docs/spec/print-suite.md, "Step 1".
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path

from .. import cards, decks
from ..cards import CardDataError
from . import ledger, mpcfill, printfile, printings, tokens

BASIC_LANDS = {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes",
               "Snow-Covered Plains", "Snow-Covered Island", "Snow-Covered Swamp",
               "Snow-Covered Mountain", "Snow-Covered Forest"}
SPREAD_OVER = 4
GALLERY_CANDIDATES = 40


def read_deck(decklist: Path) -> tuple[Counter, list[str], dict]:
    """The decklist as name -> copies with the commander included, the commanders, and the rules."""
    try:
        text = decklist.read_text(encoding="utf-8")
    except OSError as error:
        raise CardDataError(f"Cannot read {decklist}: {error.strerror}")
    rules_file = decklist.with_suffix(".rules.toml")
    rules = decks.load_rules(rules_file) if rules_file.exists() else {}
    commanders = rules.get("commander") or []
    commanders = [commanders] if isinstance(commanders, str) else list(commanders)
    deck: Counter = Counter()
    for quantity, name in decks.parse_decklist(text):
        deck[name] += quantity
    for commander in commanders:
        deck[commander] += 1
    return deck, commanders, rules


def resolve(db: sqlite3.Connection, deck: Counter) -> tuple[dict[str, sqlite3.Row], Counter]:
    """Card rows keyed by the decklist's own names (which the ledger also uses); unknown names raise."""
    rows, counts = {}, Counter()
    unknown = []
    for name, copies in deck.items():
        try:
            row = cards._find_card(db, name)
        except CardDataError:
            unknown.append(name)
            continue
        rows[name] = row
        counts[name] += copies
    if unknown:
        raise CardDataError("Not real card names: " + "; ".join(unknown) + ". Fix the decklist (mtg check names close matches).")
    return rows, counts


def candidates_for(db: sqlite3.Connection, name: str, row: sqlite3.Row | None, settings: dict,
                   renders: dict[str, list[dict]] | None = None, *, allow_lowres: bool = False) -> list[dict]:
    """Every image a card could be printed with, best first for the print file's style."""
    style = settings.get("style", "fullart")
    found: list[dict] = []
    if renders is not None:
        found.extend(renders.get(name, []))
    if row is not None:
        found.extend(printings.scryfall_candidates(db, row["oracle_id"], allow_lowres=allow_lowres))
    pins = settings.get("pins", {}).get(name, {}) if isinstance(settings.get("pins"), dict) else {}
    land = bool(row is not None and "Land" in (row["type_line"] or "").split(" // ")[0])
    styles_cfg = settings.get("styles") or {}
    return printings.rank(found, style, artist=pins.get("artist") or settings.get("artist"),
                          set_code=pins.get("set") or settings.get("set"),
                          hide_ub=settings.get("hide_universes_beyond", False),
                          exclude_styles=set(styles_cfg.get("exclude") or ()), land=land,
                          languages=set(styles_cfg.get("languages") or ()), hidden=set(settings.get("hidden") or ()))


def hide_render(decklist: Path, ident: str | None, source_name: str | None = None) -> dict:
    """Hide one render (by Drive id) or a whole drive (by source name) from this deck's choices.

    A hidden render that is currently chosen is re-chosen from what is left on the next `mtg art --keep`.
    """
    path = printfile.path_for(decklist)
    pf = printfile.load(path)
    hidden = list(pf.get("hidden") or [])
    for value in (ident, source_name):
        if value and value not in hidden:
            hidden.append(value)
    pf["hidden"] = hidden
    printfile.save(pf, path)
    return {"hidden": hidden}


def _entry_from(candidate: dict | None, name: str, copies: int, kind: str = "card") -> dict:
    entry = {"name": name, "copies": copies, "kind": kind, "printed": False, "upscale": "auto"}
    if candidate is None:
        entry["status"] = "missing"
        return entry
    entry.update({
        "source": candidate["source"], "id": candidate["id"], "label": candidate["label"],
        "dpi": candidate["dpi"], "chosen_by": "default",
    })
    if candidate.get("artist"):
        entry["artist"] = candidate["artist"]
    if candidate.get("back_png"):
        entry["back_id"] = candidate["id"]
    if candidate.get("lowres"):
        entry["status"] = "lowres"
    return entry


def choose_art(db: sqlite3.Connection, decklist: Path, *, style: str = "fullart", basics: str | None = None,
               sources: list[str] | None = None, renders: bool = True, keep: bool = False,
               allow_lowres: bool = False, printed_as: str | None = None, with_tokens: bool = True,
               use_ledger: bool = True, artist: str | None = None, set_code: str | None = None) -> tuple[dict, dict]:
    """Write <deck>.print.toml and return (print file, report)."""
    if style not in printfile.STYLES:
        raise CardDataError(f"Unknown style {style!r}. Styles: {', '.join(printfile.STYLES)}")
    deck, commanders, rules = read_deck(decklist)
    rows, counts = resolve(db, deck)
    path = printfile.path_for(decklist)
    previous = printfile.load(path) if keep and path.exists() else None
    pf = printfile.new(decklist, style=style, sources=sources or mpcfill.DEFAULT_SOURCES,
                       basics=basics or (previous or {}).get("basics"), printed_as=printed_as)
    if artist:
        pf["artist"] = artist
    if set_code:
        pf["set"] = set_code
    pf["commanders"] = commanders

    # What the ledger already has, and the art it was printed with.
    use_ledger = use_ledger and ledger.available(decklist)
    printed = ledger.printed_counts(decklist, printed_as) if use_ledger else Counter()
    printed_art = ledger.printed_art(decklist, printed_as) if use_ledger else {}

    token_list = tokens.tokens_for_deck(db, rows) if with_tokens else []
    names_to_choose = [n for n in counts if not (previous and _kept(previous, n))]
    # A double-faced card needs a back image too; its back face is searched by its own name.
    back_faces = {name: _back_face(db, rows[name]) for name in names_to_choose}
    back_faces = {name: face for name, face in back_faces.items() if face}
    renders_by_name: dict[str, list[dict]] = {}
    token_renders: dict[str, list[dict]] = {}
    report = {"renders_online": None}
    if renders:
        try:
            renders_by_name = printings.mpcfill_candidates(
                names_to_choose + sorted(set(back_faces.values()) - set(names_to_choose)), pf["sources"])
            if token_list:
                token_renders = printings.mpcfill_candidates(
                    sorted({t["token"] for t in token_list}), pf["sources"], card_type="TOKEN")
            report["renders_online"] = True
        except CardDataError as error:
            report["renders_online"] = False
            report["renders_error"] = str(error)

    entries = []
    for name, copies in counts.items():
        if previous and _kept(previous, name):
            entries.append(printfile.card_entry(previous, name))
            continue
        row = rows[name]
        already = printed.get(name, 0)
        if already and name in printed_art and printed_art[name].get("drive_id"):
            art = printed_art[name]
            entry = {"name": name, "copies": copies, "kind": "card", "printed": True, "printed_copies": already,
                     "source": "mpcfill", "id": art["drive_id"], "label": art["art"], "chosen_by": "ledger", "upscale": "auto"}
            if art.get("back_drive_id"):
                entry["back_id"] = art["back_drive_id"]
            entries.append(entry)
            continue
        ranked = candidates_for(db, name, row, pf, renders_by_name, allow_lowres=allow_lowres)
        entry = _entry_from(ranked[0] if ranked else None, name, copies)
        if name in back_faces and entry.get("id"):
            _choose_back(entry, ranked, renders_by_name.get(back_faces[name], []), pf.get("style", "fullart"))
        if already:
            entry.update({"printed": True, "printed_copies": already, "chosen_by": "ledger"})
        if name in BASIC_LANDS and copies > 1 and pf.get("basics", "vary") == "vary" and ranked:
            top = ranked[:min(SPREAD_OVER, copies, len(ranked))]
            if len(top) > 1:
                entry["slots"] = _spread(copies, [c["id"] for c in top])
                entry["slot_sources"] = {c["id"]: c["source"] for c in top}
        entries.append(entry)

    for token in token_list:
        if previous and _kept(previous, token["name"]):
            entries.append(printfile.card_entry(previous, token["name"]))
            continue
        ranked = candidates_for(db, token["token"], None, pf, token_renders)
        ranked = ranked or printings.rank(printings.scryfall_candidates(db, token["oracle_id"], allow_lowres=allow_lowres), style)
        entry = _entry_from(ranked[0] if ranked else None, token["name"], token["copies"], kind="token")
        entry["token"] = token["token"]
        entry["made_by"] = token["made_by"]
        entry["oracle_id"] = token["oracle_id"]
        if printed.get(token["name"]):
            entry.update({"printed": True, "printed_copies": printed[token["name"]], "chosen_by": "ledger"})
        entries.append(entry)

    pf["cards"] = entries
    printfile.save(pf, path)
    report.update(summary(pf))
    report["path"] = str(path)
    return pf, report


def _back_face(db: sqlite3.Connection, row: sqlite3.Row) -> str | None:
    """The back face's name for a transform or modal double-faced card, else None."""
    if not row["faces"]:
        return None
    newest = cards.printings_of(db, row["oracle_id"])
    if not newest or newest[0]["layout"] not in ("transform", "modal_dfc"):
        return None
    faces = json.loads(row["faces"])
    return faces[1]["name"] if len(faces) > 1 else None


def _choose_back(entry: dict, ranked: list[dict], back_renders: list[dict], style: str) -> None:
    """Pair a back image with the chosen front: a render of the back face when one exists, else the
    back of a Scryfall printing (the same printing when the front is a scan)."""
    if entry["source"] == "scryfall" and entry.get("back_id"):
        entry["back_source"] = "scryfall"
        return
    back = printings.rank(list(back_renders), style)
    if back:
        entry.update({"back_source": "mpcfill", "back_id": back[0]["id"], "back_label": back[0]["label"]})
        return
    scan = next((c for c in ranked if c["source"] == "scryfall" and c.get("back_png")), None)
    if scan:
        entry.update({"back_source": "scryfall", "back_id": scan["id"], "back_label": scan["label"] + " (back)"})


def _kept(previous: dict, name: str) -> bool:
    entry = printfile.card_entry(previous, name)
    return bool(entry and entry.get("chosen_by") in ("user", "ledger") and entry.get("status") != "missing")


def _spread(copies: int, ids: list[str]) -> dict[str, int]:
    base, extra = divmod(copies, len(ids))
    return {drive_id: base + (1 if i < extra else 0) for i, drive_id in enumerate(ids)}


def summary(pf: dict) -> dict:
    """Counts the agent reads back to the user."""
    cards_ = [c for c in pf["cards"] if c.get("kind", "card") == "card"]
    toks = [c for c in pf["cards"] if c.get("kind") == "token" and not c.get("dropped")]
    new = [c for c in pf["cards"] if not c.get("printed") and not c.get("dropped")]
    min_dpi = pf.get("upscale", {}).get("min_dpi", 600)
    return {
        "cards": sum(c["copies"] for c in cards_),
        "unique": len(cards_),
        "tokens": sum(c["copies"] for c in toks),
        "printed": sum(c["copies"] for c in pf["cards"] if c.get("printed")),
        "new": sum(c["copies"] for c in new),
        "renders": sum(c["copies"] for c in new if c.get("source") == "mpcfill"),
        "scans": sum(c["copies"] for c in new if c.get("source") == "scryfall"),
        "will_upscale": sorted(c["name"] for c in new if c.get("dpi") and c["dpi"] < min_dpi and c.get("upscale") != "never"),
        "missing": sorted(c["name"] for c in pf["cards"] if c.get("status") == "missing"),
        "lowres": sorted(c["name"] for c in pf["cards"] if c.get("status") == "lowres"),
    }


def gallery_payload(db: sqlite3.Connection, decklist: Path, pf: dict, order: dict | None = None,
                    *, allow_lowres: bool = False) -> tuple[dict, list[dict]]:
    """The gallery's input: deck counts and, per card, the chosen image and every alternative."""
    deck, _, _ = read_deck(decklist)
    rows, counts = resolve(db, deck)
    names = [c["name"] for c in pf["cards"] if c.get("kind", "card") == "card"]
    token_names = sorted({c["token"] for c in pf["cards"] if c.get("kind") == "token" and c.get("token")})
    renders, token_renders = {}, {}
    try:
        renders = printings.mpcfill_candidates(names, pf.get("sources"))
        if token_names:
            token_renders = printings.mpcfill_candidates(token_names, pf.get("sources"), card_type="TOKEN")
    except CardDataError:
        pass
    min_dpi = pf.get("upscale", {}).get("min_dpi", 600)
    # Cards printed from the ledger carry only a Drive id; ask mpcfill for their dpi and label when it can.
    ledger_meta: dict[str, dict] = {}
    ledger_ids = [c["id"] for c in pf["cards"] if c.get("chosen_by") == "ledger" and c.get("source") == "mpcfill" and c.get("id")]
    if ledger_ids:
        try:
            ledger_meta = mpcfill.cards(ledger_ids)
        except CardDataError:
            pass
    cards_out = []
    for entry in pf["cards"]:
        if entry.get("printed") or entry.get("dropped"):
            # Already in the box, or left out on purpose: nothing to choose.
            continue
        is_token = entry.get("kind") == "token"
        if is_token:
            ranked = candidates_for(db, entry.get("token", entry["name"]), None, pf, token_renders, allow_lowres=allow_lowres)
            ranked = ranked or printings.rank(
                printings.scryfall_candidates(db, entry["oracle_id"], allow_lowres=allow_lowres), pf.get("style", "fullart"))
        else:
            ranked = candidates_for(db, entry["name"], rows.get(entry["name"]), pf, renders, allow_lowres=allow_lowres)
        chosen = next((c for c in ranked if c["id"] == entry.get("id")), None)
        if chosen is None and entry.get("id"):
            meta = ledger_meta.get(entry["id"], {})
            chosen = {"source": entry.get("source"), "id": entry["id"],
                      "label": meta.get("name") or entry.get("label") or entry["name"],
                      "artist": entry.get("artist"), "dpi": entry.get("dpi") or meta.get("dpi"),
                      "fancy": bool(meta) and mpcfill.is_fancy(meta), "universes_beyond": False,
                      "thumb": mpcfill.thumbnail_url(entry["id"], 400) if entry.get("source") == "mpcfill" else None,
                      "large": mpcfill.thumbnail_url(entry["id"], 800) if entry.get("source") == "mpcfill" else None}
            ranked = [chosen] + ranked
        dpi = (chosen or {}).get("dpi") or entry.get("dpi") or 0
        cards_out.append({
            "name": entry["name"], "copies": entry["copies"], "kind": "token" if is_token else "card",
            "role": "Tokens" if is_token else ("Already printed" if entry.get("printed") else "To print"),
            "printed": bool(entry.get("printed")), "status": entry.get("status", "ok"),
            "upscale": entry.get("upscale", "auto"),
            "will_upscale": bool(dpi) and dpi < min_dpi and entry.get("upscale") != "never" and not entry.get("printed"),
            "upscaled_from": entry.get("upscaled_from"),
            "chosen": _public(chosen) if chosen else None,
            # Every source is searched, so a staple can have hundreds of renders; the page shows the best.
            "candidates": [_public(c) for c in ranked[:GALLERY_CANDIDATES]],
            **({"slots": entry["slots"]} if entry.get("slots") else {}),
        })
    # What needs a decision comes first: new cards, then tokens, then what is already in the box.
    group_order = {"To print": 0, "Tokens": 1, "Already printed": 2}
    cards_out.sort(key=lambda c: group_order.get(c["role"], 3))
    summary_ = summary(pf)
    quantity = (order or {}).get("quantity", summary_["new"])
    deck_info = {
        "name": decklist.stem, "to_print": quantity, "already_printed": summary_["printed"],
        "missing": len(summary_["missing"]), "bracket": (order or {}).get("bracket"), "free_slots": (order or {}).get("free_slots"),
    }
    return deck_info, cards_out


def _public(c: dict) -> dict:
    keys = ("source", "id", "label", "artist", "dpi", "fancy", "universes_beyond", "thumb", "large", "lowres",
            "render_source", "styles", "standard", "language")
    return {k: c.get(k) for k in keys if c.get(k) is not None}


def set_art(decklist: Path, name: str, source: str | None, ident: str | None, *, slots: dict | None = None,
            upscale: str | None = None, copies: int | None = None, drop: bool = False) -> dict:
    """One card by hand (the gallery and `mtg pick` call this). Returns the updated entry.

    `copies` changes how many go in the order (tokens only: a card's count comes from the decklist);
    `drop` removes a token entry altogether.
    """
    path = printfile.path_for(decklist)
    pf = printfile.load(path)
    entry = printfile.card_entry(pf, name)
    if entry is None:
        raise CardDataError(f"{name} is not in {path.name}. Run mtg art first.")
    if copies is not None or drop:
        if entry.get("kind") != "token":
            raise CardDataError(f"{name} is a card: its copies come from the decklist, not the print file.")
        if drop:
            # Kept in the file, flagged, so `mtg art --keep` does not bring it back.
            entry["dropped"] = True
            entry["chosen_by"] = "user"
            printfile.save(pf, path)
            return {"name": name, "dropped": True}
        entry["copies"] = max(1, int(copies))
        entry.pop("dropped", None)
        entry["chosen_by"] = "user"
    if source and ident:
        entry.update({"source": source, "id": ident, "chosen_by": "user"})
        for key in ("status", "slots", "slot_sources", "label", "dpi", "artist"):
            entry.pop(key, None)
        if source == "mpcfill":
            # Record the render's dpi and name, so the exporter uses the render as is.
            meta = {}
            try:
                meta = mpcfill.cards([ident]).get(ident, {})
            except CardDataError:
                pass
            if meta:
                entry["dpi"] = int(meta.get("dpi") or 0)
                entry["label"] = meta.get("name") or entry["name"]
        else:
            entry["dpi"] = printings.SCRYFALL_DPI
    if slots:
        entry["slots"] = {k: int(v) for k, v in slots.items()}
        entry["chosen_by"] = "user"
    if upscale:
        if upscale not in printfile.UPSCALE_MODES:
            raise CardDataError(f"upscale must be one of {', '.join(printfile.UPSCALE_MODES)}")
        entry["upscale"] = upscale
    printfile.save(pf, path)
    return entry
