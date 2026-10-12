"""Commander deck checks: read a plain decklist and validate it against the card index.

A deck can also carry its own rules, taken from its brief: a budget, cards that must
not appear together, limits on tagged kinds of card such as board wipes, and how
many known combos it may hold.
"""
from __future__ import annotations

import json
import re
import sqlite3
import tomllib
from pathlib import Path

from .cards import COLORS, DATA_DIR, CardDataError, _find_card, suggest_names, tagged_ids
from .combos import find_combos

DECK_SIZE = 100
ENTRY = re.compile(r"(?:(\d+)x?\s+)?(.+)", re.IGNORECASE)
# The printing some sites export after the name: "(C21) 263", optionally "*F*" for foil.
# The collector number is required, so that "Hazmat Suit (Used)" keeps its name.
PRINTING_SUFFIX = re.compile(r"\s+\(\w{2,6}\)\s+\S+(?:\s+\*\w+\*)?$")
COPY_LIMIT = re.compile(r"A deck can have (?:any number of|up to (\w+)) cards named")
NUMBER_WORDS = ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")
CARD_TYPES = ("Land", "Creature", "Artifact", "Enchantment", "Instant", "Sorcery", "Planeswalker", "Battle")
# Tags counted in every report, so a deck's shape is visible at a glance.
ROLE_TAGS = ("ramp", "card-advantage", "removal", "sweeper")
RULE_KEYS = {
    "commander": (str, list),
    "budget": (int, float),
    "max_card_price": (int, float),
    "max_game_changers": (int,),
    "max_infinite_combos": (int,),
    "max_combos": (int,),
    "not_together": (list,),
    "banned": (list,),
    "limits": (dict,),
    "minimums": (dict,),
}
# Names a limit or minimum may use for a card type instead of a tag.
TYPE_NAMES = {name: kind for kind in CARD_TYPES for name in (kind.lower(), kind.lower() + "s")}
TYPE_NAMES["sorceries"] = "Sorcery"


def check_rules(rules: dict) -> dict:
    """Reject misspelled or mistyped rules, which would otherwise pass silently."""
    for key, value in rules.items():
        if key not in RULE_KEYS:
            raise CardDataError(f"Unknown deck rule {key!r}. Rules: {', '.join(RULE_KEYS)}")
        if not isinstance(value, RULE_KEYS[key]) or isinstance(value, bool):
            raise CardDataError(f"Deck rule {key!r} has the wrong kind of value: {value!r}")
    if not all(isinstance(group, list) and len(group) >= 2 for group in rules.get("not_together", [])):
        raise CardDataError("not_together takes lists of two or more card names, e.g. [[\"A\", \"B\"]]")
    for table in ("limits", "minimums"):
        if not all(isinstance(count, int) and not isinstance(count, bool) for count in rules.get(table, {}).values()):
            raise CardDataError(f"Each entry under [{table}] is a tag or card type and a number of cards, e.g. ramp = 10")
    return rules


def load_rules(path: Path) -> dict:
    """Read a deck's rules from a TOML file."""
    try:
        return check_rules(tomllib.loads(path.read_text(encoding="utf-8")))
    except OSError as error:
        raise CardDataError(f"Cannot read {path}: {error.strerror}")
    except tomllib.TOMLDecodeError as error:
        raise CardDataError(f"{path} is not valid TOML: {error}")


def parse_decklist(text: str) -> list[tuple[int, str]]:
    """(quantity, card name) per line."""
    entries = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "//")):
            continue
        quantity, name = ENTRY.fullmatch(line).groups()
        entries.append((int(quantity or 1), PRINTING_SUFFIX.sub("", name)))
    return entries


def _copy_limit(row: sqlite3.Row) -> int | None:
    """How many copies of a card a deck may hold; None for any number."""
    if "Basic" in row["type_line"] and "Land" in row["type_line"]:
        return None
    match = COPY_LIMIT.search(row["oracle_text"] or "")
    if not match:
        return 1
    # A limit we cannot read is not enforced, rather than reported wrongly.
    return NUMBER_WORDS.index(match[1]) + 1 if match[1] in NUMBER_WORDS else None


def _can_be_commander(row: sqlite3.Row, paired: bool) -> bool:
    # Only the front face of a double-faced card counts.
    front = row["type_line"].split(" // ")[0]
    return (
        ("Legendary" in front and any(kind in front for kind in ("Creature", "Vehicle", "Spacecraft")))
        or "can be your commander" in (row["oracle_text"] or "")
        # A Background is the second commander of a "Choose a Background" creature.
        or (paired and "Background" in front)
    )


def _prices_as_of() -> str | None:
    """The date of the downloaded card data, which is when its prices were current."""
    try:
        manifest = json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8"))
        return manifest["scryfall/default-cards.jsonl.gz"]["version"][:10]
    except (OSError, ValueError, KeyError):
        return None


def _rule_results(
    db: sqlite3.Connection, rules: dict, rows: dict, quantities: dict, total: float, combos: list[dict],
) -> list[dict]:
    """One entry per deck rule, saying whether it holds and which cards are involved."""
    results = []

    def add(rule: str, ok: bool, detail: str, cards: list[str] | None = None) -> None:
        results.append({"rule": rule, "ok": ok, "detail": detail, "cards": cards or []})

    def named(name: str) -> str:
        return _find_card(db, name)["name"]

    if "budget" in rules:
        add("budget", total <= rules["budget"], f"${total:.2f} of ${rules['budget']:.2f}")
    if "max_card_price" in rules:
        over = [name for name, row in rows.items() if (row["price_usd"] or 0) > rules["max_card_price"]]
        add("max_card_price", not over, f"no card over ${rules['max_card_price']:.2f}", over)
    if "max_game_changers" in rules:
        changers = [name for name, row in rows.items() if row["game_changer"]]
        allowed = rules["max_game_changers"]
        add("max_game_changers", len(changers) <= allowed, f"{len(changers)} of {allowed} allowed", changers)
    # Only combos known to be complete count; one that may be complete is a warning instead.
    for rule, counted in (("max_infinite_combos", [c for c in combos if c["infinite"]]), ("max_combos", combos)):
        if rule in rules:
            add(rule, len(counted) <= rules[rule], f"{len(counted)} of {rules[rule]} allowed",
                [" + ".join(combo["cards"]) for combo in counted])
    for group in rules.get("not_together", []):
        present = [name for name in map(named, group) if name in rows]
        add("not_together", len(present) < len(group), " + ".join(group), present)
    if "banned" in rules:
        present = [name for name in map(named, rules["banned"]) if name in rows]
        add("banned", not present, "cards this deck must not contain", present)
    def counted(kind: str) -> list[str]:
        """Cards of a type such as 'lands', or carrying a tag such as 'ramp'."""
        if kind.lower() in TYPE_NAMES:
            return [name for name, row in rows.items()
                    if TYPE_NAMES[kind.lower()] in row["type_line"].split(" // ")[0]]
        tagged = tagged_ids(db, kind)
        return [name for name, row in rows.items() if row["oracle_id"] in tagged]

    for kind, allowed in rules.get("limits", {}).items():
        present = counted(kind)
        count = sum(quantities[name] for name in present)
        add(f"limit {kind}", count <= allowed, f"{count} of {allowed} allowed", present)
    for kind, needed in rules.get("minimums", {}).items():
        count = sum(quantities[name] for name in counted(kind))
        add(f"minimum {kind}", count >= needed, f"{count} of at least {needed}")
    return results


def _stats(db: sqlite3.Connection, rows: dict, quantities: dict) -> dict:
    """Counts that show a deck's shape: card types, mana curve and common roles."""
    # Only the front face of a double-faced card counts.
    fronts = {name: row["type_line"].split(" // ")[0] for name, row in rows.items()}
    spells = [name for name in rows if "Land" not in fronts[name]]
    spell_count = sum(quantities[name] for name in spells)
    roles = {}
    for tag in ROLE_TAGS:
        tagged = tagged_ids(db, tag)
        roles[tag] = sum(quantities[name] for name, row in rows.items() if row["oracle_id"] in tagged)
    return {
        "types": {kind: sum(quantities[name] for name in rows if kind in fronts[name]) for kind in CARD_TYPES},
        "average_mana_value": round(
            sum((rows[name]["cmc"] or 0) * quantities[name] for name in spells) / spell_count, 2
        ) if spell_count else 0,
        "roles": roles,
    }


def validate_deck(
    db: sqlite3.Connection, commanders: list[str], cards: list[tuple[int, str]], rules: dict | None = None,
) -> dict:
    """Check a Commander deck, and its own rules if given, and report every problem found."""
    if not 1 <= len(commanders) <= 2:
        raise CardDataError("A Commander deck has one or two commanders.")
    rows = {row["name"]: row for row in (_find_card(db, name) for name in commanders)}
    commander_names = list(rows)
    quantities = dict.fromkeys(rows, 0)
    unknown: dict[str, list[str]] = {}
    unknown_count = 0
    for quantity, name in cards:
        try:
            row = _find_card(db, name)
        except CardDataError:
            unknown_count += quantity
            if name not in unknown:
                unknown[name] = suggest_names(db, name)
            continue
        rows[row["name"]] = row
        quantities[row["name"]] = quantities.get(row["name"], 0) + quantity
    # A commander counts once whether or not the list repeats it.
    for name in commander_names:
        quantities[name] = max(quantities[name], 1)

    identity = "".join(c for c in COLORS if any(c in rows[name]["color_identity"] for name in commander_names))
    card_count = sum(quantities.values()) + unknown_count
    duplicates, off_identity, not_legal, no_price = [], [], [], []
    prices = {}
    for name, quantity in quantities.items():
        row = rows[name]
        allowed = _copy_limit(row)
        if allowed is not None and quantity > allowed:
            duplicates.append({"name": name, "quantity": quantity, "allowed": allowed})
        if set(row["color_identity"]) - set(identity):
            off_identity.append({"name": name, "color_identity": row["color_identity"]})
        status = json.loads(row["legalities"]).get("commander", "not_legal")
        if status != "legal":
            not_legal.append({"name": name, "status": status})
        if row["price_usd"] is None:
            no_price.append(name)
        else:
            prices[name] = row["price_usd"]
    total = round(sum(price * quantities[name] for name, price in prices.items()), 2)
    combos = find_combos(
        {row["oracle_id"]: quantities[name] for name, row in rows.items()},
        {rows[name]["oracle_id"] for name in commander_names}, identity,
    )
    rule_results = _rule_results(db, check_rules(rules or {}), rows, quantities, total, combos["included"])

    errors = {
        "count": None if card_count == DECK_SIZE
        else f"Deck has {card_count} cards; Commander decks need exactly {DECK_SIZE}.",
        "duplicates": duplicates,
        "off_identity": off_identity,
        "not_legal": not_legal,
        "unknown": [{"name": name, "suggestions": close} for name, close in unknown.items()],
    }
    warnings = [
        f"{name} is not a legendary creature, Vehicle or Spacecraft and its text does not say it can be your commander."
        for name in commander_names
        if not _can_be_commander(rows[name], paired=len(commander_names) == 2)
    ]
    # A basic land costs next to nothing; any other unpriced card could be expensive.
    unpriced = [name for name in no_price if "Basic" not in rows[name]["type_line"]]
    if unpriced and any(key in (rules or {}) for key in ("budget", "max_card_price")):
        warnings.append(f"Price rules cannot be confirmed: no price for {', '.join(unpriced)}.")
    warnings += [
        f"Possible {combo['kind']} combo: {' + '.join(combo['cards'])} + any {' + any '.join(combo['requires'])}. "
        f"Whether the deck holds such a card is not checked. {combo['url']}"
        for combo in combos["unverified"]
    ]
    return {
        "valid": not any(errors.values()) and all(result["ok"] for result in rule_results),
        "commanders": commander_names,
        "color_identity": identity or "C",
        "card_count": card_count,
        "errors": errors,
        "rules": rule_results,
        "warnings": warnings,
        "combos": combos,
        "stats": _stats(db, rows, quantities),
        "budget": {
            "total_usd": total,
            "most_expensive": [
                {"name": name, "price_usd": price}
                for name, price in sorted(prices.items(), key=lambda item: -item[1])[:10]
            ],
            "no_price": no_price,
            "prices_as_of": _prices_as_of(),
        },
    }
