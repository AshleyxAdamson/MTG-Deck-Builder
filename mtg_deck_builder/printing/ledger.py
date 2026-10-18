"""What has already been printed, from the ledger kept in the decks repo.

The decks repo owns the ledger: `printed/ledger.csv`, the archived order XMLs in
`printed/orders/`, and `tools/printed.py` with `add` and `diff`. This module calls
that script's functions so there is one definition of "printed"; it does not copy
its format. See docs/spec/print-suite.md, "Printing only what changed".
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

from ..cards import CardDataError


def decks_dir(decklist: Path) -> Path:
    return decklist.resolve().parent


def deck_name(decklist: Path) -> str:
    return decklist.stem


def _tool(decklist: Path):
    """The decks repo's tools/printed.py, imported from next to the decklist."""
    script = decks_dir(decklist) / "tools" / "printed.py"
    if not script.exists():
        raise CardDataError(
            f"{script} is missing. The ledger lives in the decks repo (tools/printed.py, printed/ledger.csv); "
            "clone it into decks/ or pass --no-ledger to print the whole deck."
        )
    spec = importlib.util.spec_from_file_location("decks_printed", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def available(decklist: Path) -> bool:
    return (decks_dir(decklist) / "tools" / "printed.py").exists()


def rows(decklist: Path) -> list[dict]:
    return _tool(decklist).read_ledger()


def printed_counts(decklist: Path, printed_as: str | None = None) -> Counter:
    """Copies of each card already printed for this deck (or for the physical deck it upgrades)."""
    source = printed_as or deck_name(decklist)
    printed: Counter = Counter()
    for row in rows(decklist):
        if row["deck"] == source:
            printed[row["card"]] += int(row["qty"])
    return printed


def printed_art(decklist: Path, printed_as: str | None = None) -> dict[str, dict]:
    """The art each printed card was printed with: name -> {art, drive_id, back_art, back_drive_id, order}."""
    source = printed_as or deck_name(decklist)
    art = {}
    for row in rows(decklist):
        if row["deck"] == source and row["card"] not in art:
            art[row["card"]] = {k: row.get(k, "") for k in ("art", "drive_id", "back_art", "back_drive_id", "order", "date")}
    return art


def delta(decklist: Path, deck: Counter, printed_as: str | None = None) -> dict:
    """What a decklist (name -> copies, commander included) still needs printed, and what to pull."""
    printed = printed_counts(decklist, printed_as) if available(decklist) else Counter()
    return {
        "to_print": deck - printed,
        "already": deck & printed,
        "to_pull": printed - deck,
        "printed_as": printed_as or deck_name(decklist),
    }


def orders_dir(decklist: Path) -> Path:
    return decks_dir(decklist) / "printed" / "orders"


def next_order_path(decklist: Path, printed_as: str | None = None) -> Path:
    """printed/orders/<deck>-<n>.xml, n one past the highest that exists for the physical deck."""
    stem = printed_as or deck_name(decklist)
    highest = 0
    for existing in orders_dir(decklist).glob(f"{stem}-*.xml"):
        match = re.fullmatch(rf"{re.escape(stem)}-(\d+)\.xml", existing.name)
        if match:
            highest = max(highest, int(match[1]))
    return orders_dir(decklist) / f"{stem}-{highest + 1}.xml"


def record(decklist: Path, order_xml: Path, date: str | None, printed_as: str | None = None) -> str:
    """Append an order to the ledger with the decks repo's own `printed.py add`, and commit there."""
    folder = decks_dir(decklist)
    deck = printed_as or deck_name(decklist)
    command = [sys.executable, str(folder / "tools" / "printed.py"), "add", str(order_xml), "--deck", deck]
    if date:
        command += ["--date", date]
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True)
    if result.returncode != 0:
        raise CardDataError(f"Recording the order failed: {result.stderr.strip() or result.stdout.strip()}")
    message = result.stdout.strip()
    if (folder / ".git").exists():
        subprocess.run(["git", "add", "printed/ledger.csv", str(order_xml.relative_to(folder))],
                       cwd=folder, capture_output=True)
        committed = subprocess.run(
            ["git", "commit", "-q", "-m", f"Record print order {order_xml.stem}"], cwd=folder, capture_output=True, text=True)
        message += "\nCommitted in the decks repo." if committed.returncode == 0 else f"\nNot committed: {committed.stderr.strip()}"
    return message
