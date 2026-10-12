"""Known combos, from the Commander Spellbook export downloaded by scripts/fetch_data.py.

The export is loaded into its own SQLite index (data/combos.sqlite) the first time it
is needed, and again whenever the downloaded file changes. Combo data is Commander
Spellbook's (https://commanderspellbook.com); it lists combos people have submitted,
so a deck with no match has no known combo, which is not proof that it has none.
"""
from __future__ import annotations

import gzip
import json
import os
import re
import sqlite3
import sys
from contextlib import closing
from urllib.parse import quote

from .cards import DATA_DIR, CardDataError

COMBOS_FILE = DATA_DIR / "spellbook" / "variants.json.gz"
INDEX_FILE = DATA_DIR / "combos.sqlite"
COMBO_URL = "https://commanderspellbook.com/combo/{}/"
ONE_CARD_AWAY_SHOWN = 10

# Bump when the tables change, so existing indexes are rebuilt.
SCHEMA_VERSION = 1
SCHEMA = """
CREATE TABLE combos (
    n INTEGER PRIMARY KEY, id TEXT, identity TEXT, card_count INTEGER, kind TEXT,
    popularity INTEGER, prerequisites TEXT, requires TEXT
);
-- Numbered as Commander Spellbook numbers them; oracle_id joins to the card index.
CREATE TABLE cards (n INTEGER PRIMARY KEY, oracle_id TEXT UNIQUE, name TEXT);
CREATE TABLE combo_cards (
    card INTEGER, combo INTEGER, quantity INTEGER, must_be_commander INTEGER,
    PRIMARY KEY (card, combo)
) WITHOUT ROWID;
CREATE INDEX combo_cards_combo ON combo_cards (combo);
CREATE TABLE results (n INTEGER PRIMARY KEY, name TEXT, rank INTEGER);
CREATE TABLE combo_results (combo INTEGER, result INTEGER, PRIMARY KEY (combo, result)) WITHOUT ROWID;
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
"""
# A result that stands on its own ("Infinite mana") is listed before one that only
# helps another ("Infinite death triggers").
RESULT_RANK = {"S": 0, "C": 1, "H": 2}
BETWEEN_COMBOS = re.compile(r"[\s,]*")


def _source_stamp() -> str:
    """Identify the downloaded file, so the index is rebuilt when it changes."""
    if not COMBOS_FILE.exists():
        raise CardDataError(f"{COMBOS_FILE} is missing. Run: python3 scripts/fetch_data.py")
    stat = COMBOS_FILE.stat()
    return json.dumps([SCHEMA_VERSION, stat.st_size, stat.st_mtime_ns])


def _read_export():
    """Yield the export's header, then each combo.

    The export is a single 690 MB JSON object, {"timestamp": ..., "variants": [...], ...},
    so it is decoded one combo at a time rather than loaded whole.
    """
    decoder = json.JSONDecoder()
    marker = '"variants": ['
    with gzip.open(COMBOS_FILE, "rt", encoding="utf-8") as export:
        buffer = export.read(1 << 20)
        start = buffer.find(marker)
        if start < 0:
            raise CardDataError(f"{COMBOS_FILE} is not a Commander Spellbook export. "
                                "Run: python3 scripts/fetch_data.py --force --only combos")
        yield json.loads(buffer[:start].rstrip(", ") + "}")
        position = start + len(marker)
        while True:
            position = BETWEEN_COMBOS.match(buffer, position).end()
            if buffer.startswith("]", position):
                return
            try:
                combo, position = decoder.raw_decode(buffer, position)
            except json.JSONDecodeError:
                # The combo runs past what has been read so far.
                more = export.read(1 << 20)
                if not more:
                    raise CardDataError(f"{COMBOS_FILE} is cut short. "
                                        "Run: python3 scripts/fetch_data.py --force --only combos")
                buffer, position = buffer[position:] + more, 0
                continue
            yield combo


def _kind(results: list[str]) -> str:
    """'infinite', 'near-infinite' (a loop that runs out, such as one per card in a library),
    or 'finite' (an instant win or a lock, with no loop at all).

    The export has no field for this; the names of a combo's results are the only signal.
    """
    names = [name.lower() for name in results]
    if any("infinite" in name and "near-infinite" not in name for name in names):
        return "infinite"
    return "near-infinite" if any("near-infinite" in name for name in names) else "finite"


def build_index(stamp: str) -> None:
    # stderr, because the MCP server speaks its protocol on stdout.
    print(f"Building combo index at {INDEX_FILE} ...", file=sys.stderr)
    part = INDEX_FILE.with_name(f"{INDEX_FILE.name}.{os.getpid()}.part")
    part.unlink(missing_ok=True)
    db = sqlite3.connect(part)
    try:
        with db:
            db.executescript(SCHEMA)
            export = _read_export()
            db.executemany("INSERT INTO meta VALUES (?, ?)",
                           [("source_stamp", stamp), ("built_at", next(export)["timestamp"])])
            for number, combo in enumerate(export):
                # A combo needing a card banned in Commander cannot be in a legal deck.
                if combo["status"] != "OK" or not combo["legalities"]["commander"]:
                    continue
                results = [produced["feature"] for produced in combo["produces"]]
                requires = [required["template"]["name"] + (f" (x{required['quantity']})" if required["quantity"] > 1 else "")
                            for required in combo["requires"]]
                prerequisites = " ".join(filter(None, (combo["notablePrerequisites"], combo["easyPrerequisites"])))
                db.execute(
                    "INSERT INTO combos VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (number, combo["id"], combo["identity"], sum(use["quantity"] for use in combo["uses"]),
                     _kind([result["name"] for result in results]), combo["popularity"] or 0,
                     " ".join(prerequisites.split()), json.dumps(requires)),
                )
                db.executemany("INSERT OR IGNORE INTO cards VALUES (?, ?, ?)",
                               ((use["card"]["id"], use["card"]["oracleId"], use["card"]["name"])
                                for use in combo["uses"]))
                db.executemany("INSERT INTO combo_cards VALUES (?, ?, ?, ?)",
                               ((use["card"]["id"], number, use["quantity"], int(use["mustBeCommander"]))
                                for use in combo["uses"]))
                db.executemany("INSERT OR IGNORE INTO results VALUES (?, ?, ?)",
                               ((result["id"], result["name"], RESULT_RANK.get(result["status"], 2))
                                for result in results))
                db.executemany("INSERT OR IGNORE INTO combo_results VALUES (?, ?)",
                               ((number, result["id"]) for result in results))
    except BaseException:
        db.close()
        part.unlink(missing_ok=True)
        raise
    db.close()
    os.replace(part, INDEX_FILE)


def _connect() -> sqlite3.Connection:
    db = sqlite3.connect(f"file:{quote(INDEX_FILE.as_posix())}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def _index_stamp() -> str | None:
    if not INDEX_FILE.exists():
        return None
    db = _connect()
    try:
        row = db.execute("SELECT value FROM meta WHERE key = 'source_stamp'").fetchone()
        return row["value"] if row else None
    except sqlite3.DatabaseError:
        return None
    finally:
        db.close()


def open_index() -> sqlite3.Connection:
    """Open the combo index read-only, building it first if it is missing or stale."""
    stamp = _source_stamp()
    if _index_stamp() != stamp:
        build_index(stamp)
    return _connect()


def _describe(db: sqlite3.Connection, combo: sqlite3.Row, uses: list[sqlite3.Row]) -> dict:
    results = db.execute(
        """SELECT name FROM combo_results JOIN results ON results.n = result
           WHERE combo = ? ORDER BY rank, name""", [combo["n"]])
    return {
        "id": combo["id"],
        "cards": [use["name"] for use in uses],
        "results": [row["name"] for row in results],
        "infinite": combo["kind"] == "infinite",
        "kind": combo["kind"],
        "prerequisites": combo["prerequisites"],
        "popularity": combo["popularity"],
        "url": COMBO_URL.format(combo["id"]),
    }


def find_combos(deck: dict[str, int], commanders: set[str], identity: str) -> dict:
    """The known combos in a deck, and those it is one card short of.

    `deck` maps each card's Oracle ID to how many copies the deck holds, commanders
    included; `commanders` holds the commanders' Oracle IDs and `identity` their colors.
    """
    with closing(open_index()) as db:
        # Only combos sharing a card with the deck are looked at, through combo_cards' key.
        candidates = db.execute(
            """SELECT combos.*, card_count - sum(min(combo_cards.quantity, held.value)) AS missing
               FROM json_each(?) AS held
               JOIN cards ON cards.oracle_id = held.key
               JOIN combo_cards ON combo_cards.card = cards.n
               JOIN combos ON combos.n = combo_cards.combo
               GROUP BY combos.n HAVING missing <= 1
               ORDER BY popularity DESC, combos.id""",
            [json.dumps(deck)],
        ).fetchall()
        included, unverified, one_card_away = [], [], []
        for combo in candidates:
            uses = db.execute(
                """SELECT oracle_id, name, quantity, must_be_commander FROM combo_cards
                   JOIN cards ON cards.n = card WHERE combo = ? ORDER BY card""", [combo["n"]]).fetchall()
            # A combo built around a particular commander is not this deck's unless it leads it.
            if any(use["must_be_commander"] and use["oracle_id"] not in commanders for use in uses):
                continue
            requires = json.loads(combo["requires"])
            if combo["missing"] == 0 and requires:
                # "Persist Creature" and the like: any card of that kind completes the combo,
                # and telling whether the deck holds one needs Commander Spellbook's own search.
                unverified.append({**_describe(db, combo, uses), "requires": requires})
            elif combo["missing"] == 0:
                included.append(_describe(db, combo, uses))
            elif not requires and set(combo["identity"]) - {"C"} <= set(identity):
                one_card_away.append((combo, uses))
        nearest = []
        for combo, uses in one_card_away[:ONE_CARD_AWAY_SHOWN]:
            missing = next(use["name"] for use in uses if deck.get(use["oracle_id"], 0) < use["quantity"])
            nearest.append({**_describe(db, combo, uses), "missing": missing})
        as_of = db.execute("SELECT value FROM meta WHERE key = 'built_at'").fetchone()["value"][:10]
    return {
        "source": "Commander Spellbook, https://commanderspellbook.com",
        "as_of": as_of,
        "included": included,
        "unverified": unverified,
        "one_card_away": nearest,
        "one_card_away_total": len(one_card_away),
    }
