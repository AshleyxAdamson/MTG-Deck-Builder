"""Command-line card search and deck checks: `uv run mtg search --type vampire --identity WB`."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from contextlib import closing
from pathlib import Path

from . import cards, decks

FETCH_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "fetch_data.py"
COMPARISON = re.compile(r"^\s*(<=|>=|=|<|>)?\s*(\d+(?:\.\d+)?)\s*$")


def bounds(value: str | None) -> tuple[float | None, float | None]:
    """Turn '<=3', '>=4', '=2' or '2' into (minimum, maximum)."""
    if value is None:
        return None, None
    match = COMPARISON.match(value)
    if not match or match.group(1) in ("<", ">"):
        raise cards.CardDataError(f"Expected a comparison like '<=3', '>=4' or '2', got {value!r}")
    operator, number = match.group(1), float(match.group(2))
    return (None if operator == "<=" else number), (None if operator == ">=" else number)


def format_brief(card: dict) -> str:
    """One line per card, for scanning long result lists."""
    stats = f" {card['power']}/{card['toughness']}" if "power" in card else ""
    price = f" ${card['price_usd']:.2f}" if "price_usd" in card else " $?"
    return f"{card['name']} | {card.get('mana_cost', '')} | {card.get('type_line', '')}{stats} | [{card['color_identity']}]{price}"


def format_card(card: dict) -> str:
    stats = f"  {card['power']}/{card['toughness']}" if "power" in card else ""
    stats += f"  loyalty {card['loyalty']}" if "loyalty" in card else ""
    price = f"  ${card['price_usd']:.2f}" if "price_usd" in card else ""
    header = f"{card['name']}  {card.get('mana_cost', '')}  [{card['color_identity']}]{price}"
    text = "\n".join(f"    {line}" for line in card.get("oracle_text", "").splitlines())
    return f"{header}\n  {card.get('type_line', '')}{stats}" + (f"\n{text}" if text else "")


def format_check(report: dict) -> str:
    errors, budget = report["errors"], report["budget"]
    lines = [f"{' + '.join(report['commanders'])}  [{report['color_identity']}]  {report['card_count']} cards"]
    lines += [f"  PROBLEM  {errors['count']}"] if errors["count"] else []
    lines += [f"  PROBLEM  {d['quantity']} copies of {d['name']} (allowed: {d['allowed']})" for d in errors["duplicates"]]
    lines += [f"  PROBLEM  {c['name']} is outside the commander's colors [{c['color_identity']}]"
              for c in errors["off_identity"]]
    lines += [f"  PROBLEM  {c['name']} is {c['status'].replace('_', ' ')} in Commander" for c in errors["not_legal"]]
    lines += [f"  PROBLEM  No card named {c['name']!r}"
              + (f"; did you mean {'; '.join(c['suggestions'])}?" if c["suggestions"] else "")
              for c in errors["unknown"]]
    for rule in report["rules"]:
        involved = f" ({', '.join(rule['cards'])})" if rule["cards"] else ""
        lines.append(f"  {'RULE ok ' if rule['ok'] else 'PROBLEM '} {rule['rule']}: {rule['detail']}{involved}")
    lines += [f"  WARNING  {warning}" for warning in report["warnings"]]
    lines.append("  Deck is valid." if report["valid"] else "  Deck is NOT valid.")
    stats = report["stats"]
    lines.append("  " + ", ".join(f"{count} {kind}" for kind, count in stats["types"].items() if count)
                 + f"; average mana value {stats['average_mana_value']}")
    lines.append("  Tagged: " + ", ".join(f"{count} {tag}" for tag, count in stats["roles"].items()))
    as_of = f" (prices as of {budget['prices_as_of']})" if budget["prices_as_of"] else ""
    lines.append(f"  Total ${budget['total_usd']:.2f}{as_of}")
    lines += [f"    ${c['price_usd']:>7.2f}  {c['name']}" for c in budget["most_expensive"]]
    if budget["no_price"]:
        lines.append(f"  No price for: {', '.join(budget['no_price'])}")
    return "\n".join(lines)


def update(force: bool) -> None:
    """Download the latest data, then rebuild the index if any of it changed."""
    fetch = subprocess.run([sys.executable, str(FETCH_SCRIPT)] + (["--force"] if force else []))
    if fetch.returncode:
        sys.exit(fetch.returncode)
    with closing(cards.open_index()) as db:
        total = db.execute("SELECT count(*) FROM cards").fetchone()[0]
    print(f"{total} cards in the index")


def run(args: argparse.Namespace) -> None:
    # The download has to finish before the index is opened.
    if args.command == "update":
        return update(args.force)

    with closing(cards.open_index()) as db:
        if args.command == "search":
            mana_min, mana_max = bounds(args.cmc)
            power_min, power_max = bounds(args.pow)
            toughness_min, toughness_max = bounds(args.tou)
            # A bare price is a ceiling: nobody searches for cards costing exactly $5.00.
            price_min, price_max = bounds(args.price)
            if args.price and args.price.strip()[0].isdigit():
                price_min = None
            result = cards.search_cards(
                db, name=args.name, text=args.text,
                types=args.type + (["Legendary"] if args.legendary else []),
                color_identity=args.identity, colors=args.colors,
                mana_value_min=mana_min, mana_value_max=mana_max,
                power_min=power_min, power_max=power_max,
                toughness_min=toughness_min, toughness_max=toughness_max,
                price_min=price_min, price_max=price_max, keywords=args.keyword,
                tags=args.tag, produces=args.produces,
                legal_in=None if args.legal.lower() == "any" else args.legal,
                include_extras=args.extras, sort=args.sort, limit=args.limit, offset=args.offset,
            )
        elif args.command == "card":
            result = [cards.get_card(db, name) for name in args.name]
        elif args.command == "tags":
            result = cards.find_tags(db, " ".join(args.query))
        elif args.command == "check":
            decklist = Path(args.decklist)
            try:
                entries = decks.parse_decklist(decklist.read_text(encoding="utf-8"))
            except OSError as error:
                raise cards.CardDataError(f"Cannot read {decklist}: {error.strerror}")
            # A deck's rules live next to it: elenda.txt is checked against elenda.rules.toml.
            rules_file = Path(args.rules) if args.rules else decklist.with_suffix(".rules.toml")
            rules = decks.load_rules(rules_file) if args.rules or rules_file.exists() else {}
            commanders = args.commander or rules.get("commander")
            if not commanders:
                raise cards.CardDataError("Name the commander with --commander, or as commander = \"...\" in the rules file.")
            result = decks.validate_deck(
                db, [commanders] if isinstance(commanders, str) else commanders, entries, rules)
        else:
            result = cards.get_rulings(db, args.name)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    elif args.command == "search":
        if args.brief:
            print("\n".join(format_brief(card) for card in result["cards"]))
        else:
            print("\n\n".join(format_card(card) for card in result["cards"]))
        shown = f"{result['offset'] + 1}-{result['offset'] + len(result['cards'])} of " if result["cards"] else ""
        print(f"\n{shown}{result['total']} cards", file=sys.stderr)
    elif args.command == "check":
        print(format_check(result))
    elif args.command == "card":
        for card in result:
            print(format_card(card))
            for key in ("keywords", "tags", "legal_in", "banned_in"):
                if card.get(key):
                    print(f"  {key}: {', '.join(card[key])}")
            for key in ("game_changer", "rarity", "set", "released_at", "edhrec_rank", "rulings", "scryfall_uri"):
                if key in card:
                    print(f"  {key}: {card[key]}")
    elif args.command == "tags":
        for tag in result:
            print(f"{tag['tag']}  ({tag['cards']} cards)  {tag.get('description', '')}")
    else:
        print(result["name"])
        for ruling in result["rulings"]:
            print(f"  {ruling['date']}  {ruling['text']}")
    if args.command == "check" and not result["valid"]:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(prog="mtg", description="Search the local Magic: The Gathering card index.")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    commands = parser.add_subparsers(dest="command", required=True)

    search = commands.add_parser("search", help="find cards matching every filter given")
    search.add_argument("--name", help="part of the card name")
    search.add_argument("--text", action="append", default=[], help="phrase in the rules text (repeatable)")
    search.add_argument("--type", action="append", default=[], help="word in the type line (repeatable)")
    search.add_argument("--legendary", action="store_true", help="legendary cards only")
    search.add_argument("--identity", help="color identity fits inside these colors, e.g. WB")
    search.add_argument("--colors", help="card is at least these colors, e.g. G")
    search.add_argument("--cmc", help="mana value, e.g. '<=3'")
    search.add_argument("--pow", help="power, e.g. '>=4'")
    search.add_argument("--tou", help="toughness, e.g. '<=2'")
    search.add_argument("--price", help="US dollar price, e.g. '<=5' or '>=20'; cards with no price never match")
    search.add_argument("--keyword", action="append", default=[], help="keyword ability (repeatable)")
    search.add_argument("--tag", action="append", default=[],
                        help="community tag such as board-wipe, ramp, removal (repeatable; see `mtg tags`)")
    search.add_argument("--produces", help="makes mana of all these colors, e.g. WB for a white-black land")
    search.add_argument("--legal", default="commander",
                        help="format the card must be legal in (default: commander); 'any' for no legality filter")
    search.add_argument("--extras", action="store_true", help="include tokens, emblems, art cards")
    search.add_argument("--sort", choices=list(cards.SORTS), default="popularity")
    search.add_argument("--limit", type=int, default=20)
    search.add_argument("--offset", type=int, default=0)
    search.add_argument("--brief", action="store_true", help="one line per card")

    card = commands.add_parser("card", help="full details for one or more cards")
    card.add_argument("name", nargs="+")
    tags = commands.add_parser("tags", help="find community tags by name or description")
    tags.add_argument("query", nargs="+")
    rulings = commands.add_parser("rulings", help="official rulings for one card")
    rulings.add_argument("name")
    check = commands.add_parser("check", help="validate a Commander decklist")
    check.add_argument("decklist", help="text file with one '1 Card Name' per line")
    check.add_argument("--commander", action="append",
                       help="commander name (give twice for partners or a background)")
    check.add_argument("--rules", help="deck rules file (default: the decklist's name with .rules.toml)")
    refresh = commands.add_parser("update", help="download the latest data and refresh the index")
    refresh.add_argument("--force", action="store_true", help="download even if the local files are current")

    try:
        run(parser.parse_args())
    except cards.CardDataError as error:
        sys.exit(str(error))


if __name__ == "__main__":
    main()
