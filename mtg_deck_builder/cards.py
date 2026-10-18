"""Card search over the Scryfall data downloaded by scripts/fetch_data.py.

The bulk files are loaded into a SQLite index (data/cards.sqlite) the first
time they are needed, and again whenever the downloaded files change.
"""
from __future__ import annotations

import difflib
import gzip
import json
import os
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote

DATA_DIR = Path(os.environ.get("MTG_DATA_DIR") or Path(__file__).resolve().parent.parent / "data")
CARDS_FILE = DATA_DIR / "scryfall" / "oracle-cards.jsonl.gz"
RULINGS_FILE = DATA_DIR / "scryfall" / "rulings.jsonl.gz"
TAGS_FILE = DATA_DIR / "scryfall" / "oracle-tags.jsonl.gz"
PRINTINGS_FILE = DATA_DIR / "scryfall" / "default-cards.jsonl.gz"
SOURCE_FILES = (CARDS_FILE, RULINGS_FILE, TAGS_FILE, PRINTINGS_FILE)
INDEX_FILE = DATA_DIR / "cards.sqlite"

COLORS = "WUBRG"
# Things Scryfall lists that never go in a deck.
EXTRA_LAYOUTS = (
    "token", "double_faced_token", "emblem", "art_series",
    "planar", "scheme", "vanguard", "front_card",
)
# Dungeons, role tokens, hero cards and the like, which use ordinary layouts.
EXTRA_SET_TYPES = ("token", "memorabilia")
SORTS = {
    "popularity": "edhrec_rank IS NULL, edhrec_rank, name",
    "name": "name",
    "mana_value": "cmc, name",
    "price": "price_usd IS NULL, price_usd, name",
    "priciest": "price_usd IS NULL, price_usd DESC, name",
    "newest": "released_at DESC, name",
}
MAX_LIMIT = 100

# Bump when the tables change, so existing indexes are rebuilt.
SCHEMA_VERSION = 4
SCHEMA = """
CREATE TABLE cards (
    oracle_id TEXT, name TEXT COLLATE NOCASE, is_extra INTEGER, mana_cost TEXT, cmc REAL,
    type_line TEXT, oracle_text TEXT, power TEXT, toughness TEXT, loyalty TEXT,
    power_num REAL, toughness_num REAL, colors TEXT, color_identity TEXT,
    keywords TEXT, legalities TEXT, faces TEXT, price_usd REAL, price_printing TEXT,
    game_changer INTEGER, rarity TEXT, set_code TEXT, set_name TEXT, released_at TEXT,
    edhrec_rank INTEGER, scryfall_uri TEXT, produced_mana TEXT
);
CREATE INDEX cards_name ON cards (name);
CREATE INDEX cards_oracle_id ON cards (oracle_id);
CREATE TABLE rulings (oracle_id TEXT, published_at TEXT, source TEXT, comment TEXT);
CREATE INDEX rulings_oracle_id ON rulings (oracle_id);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
-- Scryfall's community tags. A tag also covers everything tagged with its children.
CREATE TABLE tags (slug TEXT PRIMARY KEY, label TEXT, description TEXT);
CREATE TABLE tag_children (parent TEXT, child TEXT);
CREATE INDEX tag_children_parent ON tag_children (parent);
CREATE TABLE tag_names (key TEXT PRIMARY KEY, slug TEXT);
CREATE TABLE card_tags (oracle_id TEXT, tag TEXT);
CREATE INDEX card_tags_tag ON card_tags (tag, oracle_id);
CREATE INDEX card_tags_oracle_id ON card_tags (oracle_id);
-- Every printing of every card, for choosing art to print. Images of double-faced
-- cards live on the faces in Scryfall's data; here the front is image_* and the back back_*.
CREATE TABLE printings (
    oracle_id TEXT, scryfall_id TEXT, name TEXT COLLATE NOCASE, set_code TEXT, set_name TEXT,
    collector_number TEXT, released_at TEXT, lang TEXT, paper INTEGER, digital INTEGER,
    oversized INTEGER, image_status TEXT, highres INTEGER, full_art INTEGER, textless INTEGER,
    border_color TEXT, frame TEXT, frame_effects TEXT, promo_types TEXT, finishes TEXT,
    set_type TEXT, security_stamp TEXT, artist TEXT, layout TEXT,
    image_png TEXT, image_normal TEXT, image_large TEXT, back_png TEXT, back_normal TEXT,
    tokens TEXT
);
CREATE INDEX printings_oracle_id ON printings (oracle_id);
CREATE INDEX printings_name ON printings (name);
CREATE INDEX printings_scryfall_id ON printings (scryfall_id);
"""
FACE_FIELDS = ("name", "mana_cost", "type_line", "oracle_text", "power", "toughness", "loyalty")


class CardDataError(Exception):
    """The request cannot be answered; the message says what to do instead."""


def _source_stamp() -> str:
    """Identify the downloaded files, so the index is rebuilt when they change."""
    for path in SOURCE_FILES:
        if not path.exists():
            raise CardDataError(f"{path} is missing. Run: python3 scripts/fetch_data.py")
    stats = [path.stat() for path in SOURCE_FILES]
    return json.dumps([SCHEMA_VERSION, *([s.st_size, s.st_mtime_ns] for s in stats)])


def _color_string(colors) -> str:
    return "".join(c for c in COLORS if c in colors)


def _to_number(value):
    """Power and toughness can be '*' or '1+*'; only plain numbers are comparable."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _note_price(printing: dict, oracle_id: str, cheapest: dict[str, tuple[bool, float, str]]) -> None:
    """Keep the lowest US dollar price of each card across its printings, and which printing that is.

    The Oracle file prices only the newest printing, which is often an unreleased or
    digital one with no price at all. Printings that are not real, playable paper cards
    (oversized, gold-bordered, collector's editions) only count when nothing else is priced.
    """
    prices = [float(printing["prices"][key]) for key in ("usd", "usd_foil", "usd_etched")
              if printing["prices"].get(key)]
    if not prices or "paper" not in printing["games"]:
        return
    novelty = (printing["oversized"] or printing["border_color"] == "gold"
               or printing["set_type"] == "memorabilia")
    offer = (novelty, min(prices), printing["set_name"])
    if oracle_id not in cheapest or offer < cheapest[oracle_id]:
        cheapest[oracle_id] = offer


def _printing_row(printing: dict, oracle_id: str) -> dict:
    """One printing, with its images, for choosing art to print."""
    faces = printing.get("card_faces") or []
    front = printing.get("image_uris") or (faces[0].get("image_uris") if faces else None) or {}
    # Only a double-faced card keeps images on its faces; split and adventure cards have one image.
    back = faces[1].get("image_uris") if printing.get("image_uris") is None and len(faces) > 1 else None
    back = back or {}
    return {
        "oracle_id": oracle_id,
        "scryfall_id": printing["id"],
        "name": printing["name"],
        "set_code": printing.get("set"),
        "set_name": printing.get("set_name"),
        "collector_number": printing.get("collector_number"),
        "released_at": printing.get("released_at"),
        "lang": printing.get("lang"),
        "paper": int("paper" in printing.get("games", [])),
        "digital": int(bool(printing.get("digital"))),
        "oversized": int(bool(printing.get("oversized"))),
        "image_status": printing.get("image_status"),
        "highres": int(bool(printing.get("highres_image"))),
        "full_art": int(bool(printing.get("full_art"))),
        "textless": int(bool(printing.get("textless"))),
        "border_color": printing.get("border_color"),
        "frame": printing.get("frame"),
        "frame_effects": json.dumps(printing.get("frame_effects") or []),
        "promo_types": json.dumps(printing.get("promo_types") or []),
        "finishes": json.dumps(printing.get("finishes") or []),
        "set_type": printing.get("set_type"),
        "security_stamp": printing.get("security_stamp"),
        "artist": printing.get("artist"),
        "layout": printing.get("layout"),
        "image_png": front.get("png"),
        "image_normal": front.get("normal"),
        "image_large": front.get("large"),
        "back_png": back.get("png"),
        "back_normal": back.get("normal"),
        "tokens": json.dumps([p["id"] for p in printing.get("all_parts") or [] if p.get("component") == "token"]),
    }


def _printing_rows(cheapest: dict[str, tuple[bool, float, str]]):
    """Every printing as a row, noting each card's cheapest price along the way (one pass over 80 MB)."""
    for printing in _read_jsonl(PRINTINGS_FILE):
        oracle_id = printing.get("oracle_id") or (printing.get("card_faces") or [{}])[0].get("oracle_id")
        if not oracle_id:
            continue
        _note_price(printing, oracle_id, cheapest)
        yield _printing_row(printing, oracle_id)


def _card_row(card: dict, cheapest: dict[str, tuple[float, str]]) -> dict:
    """Flatten a Scryfall card, pulling from its faces what the card itself lacks.

    Split, adventure and double-faced cards keep rules text, and sometimes mana
    cost and colors, on their faces only.
    """
    faces = card.get("card_faces") or []

    def joined(field: str, separator: str):
        if card.get(field) is not None:
            return card[field]
        return separator.join(f[field] for f in faces if f.get(field)) or None

    def front(field: str):
        if card.get(field) is not None:
            return card[field]
        return next((f[field] for f in faces if f.get(field) is not None), None)

    colors = card.get("colors")
    if colors is None:
        colors = {c for f in faces for c in f.get("colors") or []}
    price, price_printing = cheapest.get(card["oracle_id"], (None, None))
    power, toughness = front("power"), front("toughness")
    return {
        "oracle_id": card["oracle_id"],
        "name": card["name"],
        "is_extra": int(card["layout"] in EXTRA_LAYOUTS or card.get("set_type") in EXTRA_SET_TYPES),
        "mana_cost": joined("mana_cost", " // "),
        "cmc": card.get("cmc"),
        "type_line": card.get("type_line"),
        "oracle_text": joined("oracle_text", "\n//\n"),
        "power": power,
        "toughness": toughness,
        "loyalty": front("loyalty"),
        "power_num": _to_number(power),
        "toughness_num": _to_number(toughness),
        "colors": _color_string(colors),
        "color_identity": _color_string(card.get("color_identity") or []),
        "keywords": json.dumps(card.get("keywords") or []),
        "legalities": json.dumps(card.get("legalities") or {}),
        "faces": json.dumps([{k: f[k] for k in FACE_FIELDS if f.get(k)} for f in faces]) if faces else None,
        "price_usd": price,
        "price_printing": price_printing,
        "game_changer": int(bool(card.get("game_changer"))),
        "rarity": card.get("rarity"),
        "set_code": card.get("set"),
        "set_name": card.get("set_name"),
        "released_at": card.get("released_at"),
        "edhrec_rank": card.get("edhrec_rank"),
        "scryfall_uri": card.get("scryfall_uri"),
        "produced_mana": _color_string(card.get("produced_mana") or []),
    }


def _tag_key(name: str) -> str:
    """Fold a tag's spelling, so 'Board Wipe', 'board-wipe' and 'boardwipe' are one name."""
    return "".join(c for c in name.lower() if c.isalnum())


def _load_tags(db: sqlite3.Connection) -> None:
    tags = list(_read_jsonl(TAGS_FILE))
    slugs = {tag["id"]: tag["slug"] for tag in tags}
    db.executemany("INSERT INTO tags VALUES (?, ?, ?)",
                   ((t["slug"], t["label"], t.get("description")) for t in tags))
    db.executemany("INSERT INTO tag_children VALUES (?, ?)",
                   ((t["slug"], slugs[child]) for t in tags for child in t["child_ids"] if child in slugs))
    db.executemany("INSERT INTO card_tags VALUES (?, ?)",
                   ((tagging["oracle_id"], t["slug"]) for t in tags for tagging in t["taggings"]))
    # A tag's own name wins over another tag's alias of the same spelling.
    for names in (lambda t: [t["slug"]], lambda t: [t["label"]], lambda t: t["aliases"]):
        db.executemany("INSERT OR IGNORE INTO tag_names VALUES (?, ?)",
                       ((_tag_key(name), t["slug"]) for t in tags for name in names(t)))


def _read_jsonl(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as lines:
        for line in lines:
            yield json.loads(line)


def build_index(stamp: str) -> None:
    # stderr, because the MCP server speaks its protocol on stdout.
    print(f"Building card index at {INDEX_FILE} ...", file=sys.stderr)
    part = INDEX_FILE.with_name(f"{INDEX_FILE.name}.{os.getpid()}.part")
    part.unlink(missing_ok=True)
    db = sqlite3.connect(part)
    try:
        formats: set[str] = set()
        offers: dict[str, tuple[bool, float, str]] = {}

        def card_rows():
            for card in _read_jsonl(CARDS_FILE):
                formats.update(card.get("legalities") or {})
                yield _card_row(card, cheapest)

        with db:
            db.executescript(SCHEMA)
            printing_columns = [row[1] for row in db.execute("PRAGMA table_info(printings)")]
            db.executemany(
                f"INSERT INTO printings ({', '.join(printing_columns)}) "
                f"VALUES ({', '.join(':' + c for c in printing_columns)})",
                _printing_rows(offers),
            )
            cheapest = {oracle_id: (price, set_name) for oracle_id, (_, price, set_name) in offers.items()}
            columns = [row[1] for row in db.execute("PRAGMA table_info(cards)")]
            db.executemany(
                f"INSERT INTO cards ({', '.join(columns)}) VALUES ({', '.join(':' + c for c in columns)})",
                card_rows(),
            )
            db.executemany(
                "INSERT INTO rulings VALUES (?, ?, ?, ?)",
                ((r["oracle_id"], r["published_at"], r["source"], r["comment"])
                 for r in _read_jsonl(RULINGS_FILE)),
            )
            _load_tags(db)
            db.executemany("INSERT INTO meta VALUES (?, ?)",
                           [("source_stamp", stamp), ("formats", json.dumps(sorted(formats)))])
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
    """Open the card index read-only, building it first if it is missing or stale."""
    stamp = _source_stamp()
    if _index_stamp() != stamp:
        build_index(stamp)
    return _connect()


def _escape(value: str) -> str:
    """Escape LIKE wildcards so user text only ever matches literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _like(value: str) -> str:
    return f"%{_escape(value)}%"


def _parse_colors(value: str, option: str) -> str:
    letters = value.upper().replace("C", "")
    if set(letters) - set(COLORS):
        raise CardDataError(f"{option} takes color letters from WUBRG (or C for colorless), got {value!r}")
    return letters


def _number(value):
    return int(value) if isinstance(value, float) and value.is_integer() else value


def _summary(row: sqlite3.Row) -> dict:
    card = {
        "name": row["name"],
        "mana_cost": row["mana_cost"],
        "mana_value": _number(row["cmc"]),
        "type_line": row["type_line"],
        "oracle_text": row["oracle_text"],
        "power": row["power"],
        "toughness": row["toughness"],
        "loyalty": row["loyalty"],
        "color_identity": row["color_identity"] or "C",
        "price_usd": row["price_usd"],
        "game_changer": True if row["game_changer"] else None,
    }
    return {key: value for key, value in card.items() if value not in (None, "")}


def tag_family(db: sqlite3.Connection, name: str) -> list[str]:
    """The tag called `name`, by slug, label or alias, followed by all tags beneath it."""
    row = db.execute("SELECT slug FROM tag_names WHERE key = ?", [_tag_key(name)]).fetchone()
    if not row:
        close = [tag["tag"] for tag in find_tags(db, name, limit=8)]
        hint = f" Did you mean: {', '.join(close)}" if close else " Search for one with find_tags / `mtg tags`."
        raise CardDataError(f"No tag named {name!r}.{hint}")
    family = db.execute(
        """WITH RECURSIVE family (slug) AS (
               SELECT ? UNION SELECT child FROM tag_children JOIN family ON parent = family.slug)
           SELECT slug FROM family""",
        [row["slug"]],
    )
    return [member["slug"] for member in family]


def tagged_ids(db: sqlite3.Connection, name: str) -> set[str]:
    """Oracle IDs of every card carrying the tag or one beneath it."""
    family = tag_family(db, name)
    marks = ",".join("?" * len(family))
    return {row[0] for row in db.execute(f"SELECT oracle_id FROM card_tags WHERE tag IN ({marks})", family)}


def find_tags(db: sqlite3.Connection, query: str, limit: int = 30) -> list[dict]:
    """Tags whose name or description mentions the query, biggest first."""
    words = [_like(word) for word in query.split()]
    condition = " AND ".join(["(slug LIKE ? ESCAPE '\\' OR label LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\'"
                              " OR slug IN (SELECT slug FROM tag_names WHERE key LIKE ? ESCAPE '\\'))"] * len(words))
    params = [value for word in words for value in (word, word, word, f"%{_escape(_tag_key(word[1:-1]))}%")]
    found = []
    for row in db.execute(f"SELECT slug, description FROM tags WHERE {condition or '1'}", params):
        found.append({"tag": row["slug"], "cards": len(tagged_ids(db, row["slug"])), "description": row["description"]})
    found.sort(key=lambda tag: -tag["cards"])
    return [{key: value for key, value in tag.items() if value} for tag in found[:limit]]


def search_cards(
    db: sqlite3.Connection,
    *,
    name: str | None = None,
    text: list[str] | None = None,
    types: list[str] | None = None,
    color_identity: str | None = None,
    colors: str | None = None,
    mana_value_min: float | None = None,
    mana_value_max: float | None = None,
    power_min: float | None = None,
    power_max: float | None = None,
    toughness_min: float | None = None,
    toughness_max: float | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    keywords: list[str] | None = None,
    tags: list[str] | None = None,
    produces: str | None = None,
    legal_in: str | None = None,
    include_extras: bool = False,
    sort: str = "popularity",
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Find cards matching every filter given. See server.py for what each one means."""
    where, params = [], []

    def add(clause: str, *values) -> None:
        where.append(clause)
        params.extend(values)

    if name:
        add("name LIKE ? ESCAPE '\\'", _like(name))
    for phrase in text or []:
        add("oracle_text LIKE ? ESCAPE '\\'", _like(phrase))
    for word in types or []:
        add("type_line LIKE ? ESCAPE '\\'", _like(word))
    if color_identity is not None:
        allowed = _parse_colors(color_identity, "color_identity")
        for color in COLORS:
            if color not in allowed:
                add("color_identity NOT LIKE ?", f"%{color}%")
    if colors is not None:
        required = _parse_colors(colors, "colors")
        if not required:
            add("colors = ''")
        for color in required:
            add("colors LIKE ?", f"%{color}%")
    for column, low, high in (
        ("cmc", mana_value_min, mana_value_max),
        ("power_num", power_min, power_max),
        ("toughness_num", toughness_min, toughness_max),
        ("price_usd", price_min, price_max),
    ):
        if low is not None:
            add(f"{column} >= ?", low)
        if high is not None:
            add(f"{column} <= ?", high)
    for keyword in keywords or []:
        add("EXISTS (SELECT 1 FROM json_each(cards.keywords) WHERE value = ? COLLATE NOCASE)", keyword)
    for tag in tags or []:
        family = tag_family(db, tag)
        add(f"EXISTS (SELECT 1 FROM card_tags WHERE oracle_id = cards.oracle_id"
            f" AND tag IN ({','.join('?' * len(family))}))", *family)
    for color in _parse_colors(produces, "produces") if produces else "":
        add("produced_mana LIKE ?", f"%{color}%")
    if legal_in:
        formats = json.loads(db.execute("SELECT value FROM meta WHERE key = 'formats'").fetchone()[0])
        if legal_in.lower() not in formats:
            raise CardDataError(f"Unknown format {legal_in!r}. Formats: {', '.join(formats)}")
        # Tokens and other extras have no legality, so the format never rules them out.
        legal = "json_extract(legalities, ?) IN ('legal', 'restricted')"
        add(f"(is_extra = 1 OR {legal})" if include_extras else legal, f"$.{legal_in.lower()}")
    if not include_extras:
        add("is_extra = 0")
    if sort not in SORTS:
        raise CardDataError(f"Unknown sort {sort!r}. Sorts: {', '.join(SORTS)}")

    condition = " AND ".join(where) or "1"
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    total = db.execute(f"SELECT count(*) FROM cards WHERE {condition}", params).fetchone()[0]
    rows = db.execute(
        f"SELECT * FROM cards WHERE {condition} ORDER BY {SORTS[sort]} LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()
    return {"total": total, "offset": offset, "cards": [_summary(row) for row in rows]}


def suggest_names(db: sqlite3.Connection, name: str) -> list[str]:
    """Cards containing what was typed, then near misses such as typos."""
    close = [c["name"] for c in search_cards(db, name=name, limit=5)["cards"]]
    # Each face of a double-faced card is a name someone might type.
    faces = {}
    for (full,) in db.execute("SELECT name FROM cards WHERE is_extra = 0"):
        for face in {full, *full.split(" // ")}:
            faces.setdefault(face, full)
    for face in difflib.get_close_matches(name, list(faces), n=5, cutoff=0.7):
        if faces[face] not in close:
            close.append(faces[face])
    return close


def _find_card(db: sqlite3.Connection, name: str) -> sqlite3.Row:
    """Resolve a card by exact name, or by the name of one of its faces."""
    # A real card wins over a token that shares its name.
    row = db.execute(
        """SELECT * FROM cards
           WHERE name = ? OR name LIKE ? ESCAPE '\\' OR name LIKE ? ESCAPE '\\'
           ORDER BY is_extra, name != ?, edhrec_rank IS NULL, edhrec_rank LIMIT 1""",
        [name, f"{_escape(name)} // %", f"% // {_escape(name)}", name],
    ).fetchone()
    if row:
        return row
    close = suggest_names(db, name)
    hint = f" Did you mean: {'; '.join(close)}" if close else ""
    raise CardDataError(f"No card named {name!r}.{hint}")


def get_card(db: sqlite3.Connection, name: str) -> dict:
    """Everything deck-relevant about one card, looked up by exact name."""
    row = _find_card(db, name)
    legalities = json.loads(row["legalities"])
    card = _summary(row)
    card.update({
        "colors": row["colors"] or "C",
        "keywords": json.loads(row["keywords"]),
        "legal_in": sorted(f for f, status in legalities.items() if status in ("legal", "restricted")),
        "banned_in": sorted(f for f, status in legalities.items() if status == "banned"),
        "price_printing": row["price_printing"],
        "rarity": row["rarity"],
        "set": row["set_name"],
        "released_at": row["released_at"],
        "edhrec_rank": row["edhrec_rank"],
        "rulings": db.execute("SELECT count(*) FROM rulings WHERE oracle_id = ?", [row["oracle_id"]]).fetchone()[0],
        "scryfall_uri": row["scryfall_uri"],
        "tags": [r[0] for r in db.execute(
            "SELECT DISTINCT tag FROM card_tags WHERE oracle_id = ? ORDER BY tag", [row["oracle_id"]])],
    })
    card["game_changer"] = bool(row["game_changer"])
    if row["faces"]:
        card["faces"] = json.loads(row["faces"])
    return {key: value for key, value in card.items() if value is not None}


def printings_of(db: sqlite3.Connection, oracle_id: str) -> list[dict]:
    """Every printing of a card, newest first, with the JSON columns decoded."""
    rows = db.execute(
        "SELECT * FROM printings WHERE oracle_id = ? ORDER BY released_at DESC, collector_number", [oracle_id]
    ).fetchall()
    printings = []
    for row in rows:
        printing = dict(row)
        for key in ("frame_effects", "promo_types", "finishes", "tokens"):
            printing[key] = json.loads(printing[key] or "[]")
        printings.append(printing)
    return printings


def token_oracle_ids(db: sqlite3.Connection, oracle_id: str) -> set[str]:
    """The tokens a card makes, as the tokens' own Oracle IDs, from Scryfall's related parts."""
    token_ids: set[str] = set()
    for row in db.execute("SELECT tokens FROM printings WHERE oracle_id = ?", [oracle_id]):
        token_ids.update(json.loads(row["tokens"] or "[]"))
    if not token_ids:
        return set()
    marks = ", ".join("?" for _ in token_ids)
    return {row["oracle_id"] for row in db.execute(
        f"SELECT DISTINCT oracle_id FROM printings WHERE scryfall_id IN ({marks})", list(token_ids))}


def get_rulings(db: sqlite3.Connection, name: str) -> dict:
    """Official rulings for one card, oldest first."""
    row = _find_card(db, name)
    rulings = db.execute(
        "SELECT published_at, source, comment FROM rulings WHERE oracle_id = ? ORDER BY published_at",
        [row["oracle_id"]],
    ).fetchall()
    return {
        "name": row["name"],
        "rulings": [{"date": r["published_at"], "source": r["source"], "text": r["comment"]} for r in rulings],
    }
