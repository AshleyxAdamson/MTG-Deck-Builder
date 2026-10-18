"""`mtg print`: the order for a deck, as MPC Autofill XML, containing only what is not yet printed.

Every `<id>` in the XML is a Google Drive file id: the shop fetches the images itself.
Community renders go in by their own id. Images we prepare (scans with bleed, upscales,
the plain back) are uploaded to the user's Drive first. See docs/spec/print-suite.md,
"Step 3" and "Printing only what changed".
"""
from __future__ import annotations

import sqlite3
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from ..cards import DATA_DIR, CardDataError
from . import art, drive, ledger, mpcfill, prepare, printfile, printings

BRACKETS = (18, 36, 55, 72, 90, 108, 126, 144, 162, 180, 198, 216, 234, 396, 504, 612)
STOCKS = ("(S27) Smooth", "(S30) Standard Smooth", "(S33) Superior Smooth", "(M31) Linen", "(P10) Plastic")
PREPARED_DIR = DATA_DIR / "art" / "prepared"


def bracket_for(quantity: int) -> int | None:
    return next((b for b in BRACKETS if b >= quantity), None)


def plan(db: sqlite3.Connection, decklist: Path, pf: dict, *, full: bool = False, allow_lowres: bool = False) -> dict:
    """Which copies of which entries go in this order, and everything wrong with that."""
    deck, _, _ = art.read_deck(decklist)
    rows, counts = art.resolve(db, deck)
    problems: list[str] = []
    entries = {c["name"]: c for c in pf["cards"]}
    stale = [n for n in counts if n not in entries]
    if stale:
        problems.append("The print file is older than the decklist; run mtg art --keep. Missing: " + "; ".join(stale))
    tokens = Counter({c["name"]: c["copies"] for c in pf["cards"] if c.get("kind") == "token" and not c.get("dropped")})
    wanted = counts + tokens
    printed_as = pf.get("printed_as")
    if full or not ledger.available(decklist):
        delta = {"to_print": wanted, "already": Counter(), "to_pull": Counter(), "printed_as": printed_as}
    else:
        delta = ledger.delta(decklist, wanted, printed_as)

    slots: list[dict] = []
    for name, copies in delta["to_print"].items():
        entry = entries.get(name)
        if entry is None or entry.get("dropped"):
            continue
        if entry.get("status") == "missing":
            problems.append(f"{name}: no printable image anywhere yet")
            continue
        if entry.get("status") == "lowres" and not allow_lowres:
            problems.append(f"{name}: only a low-resolution scan exists (pass --allow-lowres to print it anyway)")
            continue
        for ident, source, n in _allocate(entry, copies):
            for _ in range(n):
                slots.append({"name": name, "entry": entry, "source": source, "id": ident,
                              "back_id": entry.get("back_id"),
                              "back_source": entry.get("back_source", entry.get("source")), "slot": len(slots)})
    quantity = len(slots)
    bracket = bracket_for(quantity)
    if quantity and bracket is None:
        problems.append(f"{quantity} cards is more than one order holds (612); split the deck")
    if not quantity and not problems:
        problems.append("Nothing to print: every card is already in the ledger")
    return {
        "decklist": str(decklist), "slots": slots, "quantity": quantity, "bracket": bracket,
        "free_slots": (bracket - quantity) if bracket else 0, "problems": problems,
        "to_print": dict(delta["to_print"]), "already": dict(delta["already"]), "to_pull": dict(delta["to_pull"]),
        "printed_as": delta["printed_as"], "full": full,
    }


def _allocate(entry: dict, copies: int) -> list[tuple[str, str, int]]:
    """(id, source, copies) per art for an entry: basics may be spread over several arts."""
    spread = entry.get("slots")
    if not spread:
        return [(entry["id"], entry["source"], copies)]
    sources = entry.get("slot_sources") or {}
    total = sum(spread.values()) or 1
    out, given = [], 0
    ids = list(spread)
    for i, ident in enumerate(ids):
        n = round(copies * spread[ident] / total) if i < len(ids) - 1 else copies - given
        n = max(0, min(n, copies - given))
        given += n
        if n:
            out.append((ident, sources.get(ident, entry["source"]), n))
    return out


def resolve_images(db: sqlite3.Connection, pf: dict, order: dict, *, upload: bool = True) -> dict:
    """For every distinct image in the order, the Drive id the XML will carry, preparing and uploading as needed."""
    settings = pf.get("upscale", {})
    min_dpi, target_dpi = settings.get("min_dpi", 600), settings.get("target_dpi", 800)
    model, engine = settings.get("model", "ultrasharp-4x"), settings.get("engine", "auto")
    resolved: dict[tuple, dict] = {}
    needs_drive: list[str] = []
    upscaled: list[dict] = []
    drive_ok = upload and drive.available()

    def finish(key, path: Path, label: str, info: dict | None):
        item = {"path": path, "name": path.name, "label": label, "drive_id": None, "prepared": True}
        if info and info.get("upscaled"):
            upscaled.append({"name": label, "from_dpi": info["from_dpi"], "to_dpi": info["to_dpi"],
                             "model": info.get("model"), "fallback": info.get("fallback"), "color_shift": info.get("color_shift")})
        if drive_ok:
            item["drive_id"] = drive.upload(path)
        else:
            needs_drive.append(label)
        resolved[key] = item

    for slot in order["slots"]:
        entry = slot["entry"]
        for face in ("front", "back"):
            ident = slot["id"] if face == "front" else slot.get("back_id")
            if not ident:
                continue
            source = slot["source"] if face == "front" else slot["back_source"]
            key = (source, ident, face)
            if key in resolved:
                continue
            mode = entry.get("upscale", "auto")
            if source == "mpcfill":
                dpi = entry.get("dpi") or 0
                if face == "back":
                    dpi = int((mpcfill.cards([ident]).get(ident) or {}).get("dpi") or dpi)
                if mode != "always" and (dpi >= min_dpi or mode == "never"):
                    label = entry.get("back_label") if face == "back" else entry.get("label")
                    resolved[key] = {"drive_id": ident, "name": label or slot["name"], "label": slot["name"], "prepared": False}
                    continue
                src = mpcfill.download(ident)
                info = prepare.prepare(src, "render", min_dpi=min_dpi if mode != "always" else 10_000,
                                       target_dpi=target_dpi, model=model, engine=engine)
                finish(key, Path(info["path"]), slot["name"], info)
            else:
                candidate = {"id": ident, "name": slot["name"], "png": None, "back_png": None}
                row = db.execute("SELECT image_png, back_png FROM printings WHERE scryfall_id = ?", [ident]).fetchone()
                if row is None:
                    raise CardDataError(f"{slot['name']}: printing {ident} is not in the index any more; run mtg art --keep")
                candidate["png"], candidate["back_png"] = row["image_png"], row["back_png"]
                src = printings.download_scryfall(candidate, back=(face == "back"))
                info = prepare.prepare(src, "scryfall", min_dpi=min_dpi if mode != "never" else 0,
                                       target_dpi=target_dpi, model=model, engine=engine)
                label = slot["name"] + (" (back)" if face == "back" else "")
                finish(key, Path(info["path"]), label, info)

    back = pf.get("cardback") or {"kind": "plain", "color": "#000000"}
    if back.get("kind") == "plain":
        color = back.get("color", "#000000")
        path = PREPARED_DIR / f"back-{color.lstrip('#').lower()}.png"
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            prepare.plain_back(color, target_dpi).save(path)
        item = {"path": path, "name": path.name, "label": "card back", "drive_id": None, "prepared": True}
        if drive_ok:
            item["drive_id"] = drive.upload(path)
        else:
            needs_drive.append("card back")
        resolved[("back", color, "back")] = item
        cardback_id = item["drive_id"]
    else:
        cardback_id = back.get("id")
    return {"images": resolved, "cardback_id": cardback_id, "needs_drive": needs_drive, "upscaled": upscaled}


def write_xml(order: dict, images: dict, path: Path, *, stock: str, foil: bool) -> Path:
    if stock not in STOCKS:
        raise CardDataError(f"Unknown stock {stock!r}. Stocks: {', '.join(STOCKS)}")
    if foil and stock == "(P10) Plastic":
        raise CardDataError("Plastic stock cannot be foil.")
    root = ET.Element("order")
    details = ET.SubElement(root, "details")
    ET.SubElement(details, "quantity").text = str(order["quantity"])
    ET.SubElement(details, "stock").text = stock
    ET.SubElement(details, "foil").text = "true" if foil else "false"
    fronts, backs = ET.SubElement(root, "fronts"), ET.SubElement(root, "backs")
    # One <card> per deck entry and image, never merged across entries that share an image: the ledger
    # records each <card> under its <query>, and the query is the entry's name so the ledger matches it.
    by_entry: dict[tuple, list[int]] = {}
    for slot in order["slots"]:
        by_entry.setdefault((slot["name"], slot["source"], slot["id"], "front"), []).append(slot["slot"])
        if slot.get("back_id"):
            by_entry.setdefault((slot["name"], slot["back_source"], slot["back_id"], "back"), []).append(slot["slot"])
    for (name, source, ident, face), slot_numbers in by_entry.items():
        image = images["images"][(source, ident, face)]
        if not image["drive_id"]:
            continue
        card = ET.SubElement(fronts if face == "front" else backs, "card")
        ET.SubElement(card, "id").text = image["drive_id"]
        ET.SubElement(card, "slots").text = ",".join(str(n) for n in slot_numbers)
        ET.SubElement(card, "name").text = image["name"]
        # A card name is matched by the ledger after normalising; a token name is stored as written.
        ET.SubElement(card, "query").text = name if name.endswith("token") or " token (" in name else printings.mpcfill_key(name)
    ET.SubElement(root, "cardback").text = images["cardback_id"] or ""
    ET.indent(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ET.tostring(root, encoding="unicode") + "\n", encoding="utf-8")
    return path


def export(db: sqlite3.Connection, decklist: Path, *, full: bool = False, allow_lowres: bool = False,
           upload: bool = True, stock: str | None = None, foil: bool | None = None, out: Path | None = None) -> dict:
    """Plan, prepare, upload, write the XML. Returns the preflight report; `ok` says whether the XML is complete."""
    pf = printfile.load(printfile.path_for(decklist))
    order = plan(db, decklist, pf, full=full, allow_lowres=allow_lowres)
    report = {k: v for k, v in order.items() if k != "slots"}
    report["decklist"] = str(decklist)
    if order["problems"] and not order["slots"]:
        report.update({"ok": False, "xml": None, "needs_drive": [], "upscaled": []})
        return report
    images = resolve_images(db, pf, order, upload=upload)
    report["needs_drive"] = images["needs_drive"]
    report["upscaled"] = images["upscaled"]
    if images["needs_drive"]:
        report["problems"].append(
            f"{len(images['needs_drive'])} prepared image(s) are not on Google Drive yet, so they are left out of the XML. "
            "Run `rclone config` once (a Google Drive remote named gdrive), then re-run.")
    for shift in [u for u in images["upscaled"] if u.get("color_shift") and not u["color_shift"].get("ok")]:
        report["problems"].append(f"{shift['name']}: the upscale shifted its colours (mean diff {shift['color_shift'].get('mean_diff')}); check it in the gallery or set upscale = \"never\"")
    path = out or ledger.next_order_path(decklist, pf.get("printed_as")) if ledger.available(decklist) else decklist.with_suffix(".xml")
    if out:
        path = out
    write_xml(order, images, path, stock=stock or pf.get("stock", "(S33) Superior Smooth"),
              foil=pf.get("foil", False) if foil is None else foil)
    report["xml"] = str(path)
    report["ok"] = not report["problems"]
    return report
