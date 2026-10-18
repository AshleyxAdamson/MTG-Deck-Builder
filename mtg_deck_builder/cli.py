"""Command-line card search and deck checks: `uv run mtg search --type vampire --identity WB`."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from contextlib import closing
from pathlib import Path

from . import cards, combos, decks, edhrec
from .printing import art, export, ledger, printfile, send
from .printing import gallery as gallery_page

FETCH_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "fetch_data.py"
COMPARISON = re.compile(r"^\s*(<=|>=|=|<|>)?\s*(\d+(?:\.\d+)?)\s*$")
COMBO_KINDS = {"infinite": "infinite", "near-infinite": "near-infinite", "finite": "not infinite"}


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


def format_combo(combo: dict) -> str:
    results = ", ".join(combo["results"][:3]) + (", ..." if len(combo["results"]) > 3 else "")
    return f"{' + '.join(combo['cards'])}: {COMBO_KINDS[combo['kind']]} combo ({results})  {combo['url']}"


def format_check(report: dict) -> str:
    errors, budget, known = report["errors"], report["budget"], report["combos"]
    lines = [f"{' + '.join(report['commanders'])}  [{report['color_identity']}]  {report['card_count']} cards"]
    lines += [f"  PROBLEM  {errors['count']}"] if errors["count"] else []
    lines += [f"  PROBLEM  {message}" for message in errors["format"]]
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
    # A combo is a problem only when one of the deck's rules counts it out.
    broken = {rule["rule"] for rule in report["rules"] if not rule["ok"]}
    for combo in known["included"]:
        counted = "max_combos" in broken or (combo["infinite"] and "max_infinite_combos" in broken)
        lines.append(f"  {'PROBLEM ' if counted else 'COMBO   '} {format_combo(combo)}")
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
    lines.append(f"  Known combos in the deck: {len(known['included'])}"
                 f" (Commander Spellbook, as of {known['as_of']}; it lists known combos only)")
    if known["one_card_away"]:
        shown, total = len(known["one_card_away"]), known["one_card_away_total"]
        lines.append("  One card away from a combo" + (f" (the {shown} most popular of {total})" if total > shown else "") + ":")
    for combo in known["one_card_away"]:
        others = ", ".join(name for name in combo["cards"] if name != combo["missing"])
        lines.append(f"    {combo['missing']}  with {others}  ({COMBO_KINDS[combo['kind']]})")
    return "\n".join(lines)


def update(force: bool) -> None:
    """Download the latest data, then rebuild the index if any of it changed."""
    fetch = subprocess.run([sys.executable, str(FETCH_SCRIPT)] + (["--force"] if force else []))
    if fetch.returncode:
        sys.exit(fetch.returncode)
    with closing(cards.open_index()) as db:
        total = db.execute("SELECT count(*) FROM cards").fetchone()[0]
    print(f"{total} cards in the index")
    with closing(combos.open_index()) as db:
        total = db.execute("SELECT count(*) FROM combos").fetchone()[0]
    print(f"{total} combos in the index")


def format_problems(text: str, commanders: list[str]) -> list[str]:
    """Each line that would stop a decklist pasting into Moxfield as is, with its line number."""
    leading = {name.lower() for name in commanders}
    problems = []
    for number, line in enumerate(text.rstrip().splitlines(), 1):
        line = line.strip()
        if not line:
            reason = "is blank"
        elif line.startswith(("#", "//")):
            reason = "is a comment"
        elif decks.parse_decklist(line)[0][1].lower() in leading:
            reason = "names the commander, which belongs in the rules file"
        else:
            continue
        problems.append(f"Line {number} {reason}. The decklist must paste into Moxfield as is.")
    return problems


def load_deck(args: argparse.Namespace) -> tuple[list[tuple[int, str]], dict, list[str], list[str]]:
    """A decklist's entries, its rules, its commanders and its format problems, from the files and flags given."""
    decklist = Path(args.decklist)
    try:
        text = decklist.read_text(encoding="utf-8")
    except OSError as error:
        raise cards.CardDataError(f"Cannot read {decklist}: {error.strerror}")
    # A deck's rules live next to it: elenda.txt is checked against elenda.rules.toml.
    rules_file = Path(args.rules) if args.rules else decklist.with_suffix(".rules.toml")
    rules = decks.load_rules(rules_file) if args.rules or rules_file.exists() else {}
    commanders = args.commander or rules.get("commander") or []
    commanders = [commanders] if isinstance(commanders, str) else commanders
    return decks.parse_decklist(text), rules, commanders, format_problems(text, commanders)


def format_art(report: dict) -> str:
    lines = [f"{report['path']}: {report['unique']} cards ({report['cards']} with copies), {report['tokens']} tokens"]
    lines.append(f"  already printed: {report['printed']}   new: {report['new']} "
                 f"({report['renders']} renders, {report['scans']} scans)")
    if report.get("renders_online") is False:
        lines.append(f"  WARNING  mpcfill was not reachable, so only Scryfall printings were used: {report.get('renders_error')}")
    if report["will_upscale"]:
        lines.append(f"  will upscale ({len(report['will_upscale'])}): {', '.join(report['will_upscale'])}")
    if report["lowres"]:
        lines.append(f"  LOW RES  only a low-resolution scan exists: {', '.join(report['lowres'])}")
    if report["missing"]:
        lines.append(f"  MISSING  no printable image yet: {', '.join(report['missing'])}")
    return "\n".join(lines)


def format_print(report: dict) -> str:
    lines = []
    lines.append(f"{report['decklist']}: {report['quantity']} cards to print"
                 + (f", {report['bracket']}-card tier with {report['free_slots']} free slots" if report.get("bracket") else "")
                 + (" (whole deck)" if report.get("full") else f" (compared with {report['printed_as']}'s prints)"))
    if report["already"]:
        lines.append(f"  already have: {sum(report['already'].values())} cards")
    if report["to_pull"]:
        pulled = ", ".join(f"{n} {name}" if n > 1 else name for name, n in sorted(report["to_pull"].items()))
        lines.append(f"  take out of the deck: {pulled}")
    for item in report.get("upscaled", []):
        how = "resampled only (no upscaler)" if item.get("fallback") else (item.get("model") or "from cache")
        lines.append(f"  upscaled  {item['name']}: {item['from_dpi']} -> {item['to_dpi']} dpi, {how}")
    lines += [f"  PROBLEM  {problem}" for problem in report["problems"]]
    if report.get("xml"):
        lines.append(f"  XML: {report['xml']}" + ("" if report["ok"] else "  (incomplete, see problems)"))
    return "\n".join(lines)


def format_send(result: dict) -> str:
    lines = [f"{result['shop']}: " + (result.get("url") or ", ".join(result.get("folders", [])))]
    lines += [f"  {i}. {step}" for i, step in enumerate(result.get("steps", []), 1)]
    return "\n".join(lines)


def _reachable(address: str, port: int) -> bool:
    import socket
    try:
        with socket.create_connection((address, port), timeout=3):
            return True
    except OSError:
        return False


def run_gallery(db, args: argparse.Namespace) -> dict:
    """Write the gallery page and serve it; blocks until Ctrl-C unless --no-serve."""
    decklist = Path(args.decklist)
    pf = printfile.load(printfile.path_for(decklist))
    order = export.plan(db, decklist, pf, full=args.full, allow_lowres=True)
    deck_info, cards_out = art.gallery_payload(db, decklist, pf, order)
    page = decklist.with_suffix(".gallery.html")
    gallery_page.write(deck_info, cards_out, page)
    result = {"page": str(page)}
    if args.no_serve:
        return result

    def on_choose(name, source, ident, slots=None):
        art.set_art(decklist, name, source, ident, slots=slots)

    def on_upscale(name, mode):
        art.set_art(decklist, name, None, None, upscale=mode)

    def on_hide(name, ident, source_name=None):
        art.hide_render(decklist, ident, source_name)

    # A restart keeps the previous link alive: same port and token, read back from the URL file.
    url_file = decklist.with_suffix(".gallery.url")
    port, token = args.port, None
    if url_file.exists() and not args.port:
        previous = url_file.read_text(encoding="utf-8").strip()
        found = re.search(r":(\d+)/\?t=([A-Za-z0-9_-]+)", previous)
        if found:
            port, token = int(found[1]), found[2]
    try:
        server = gallery_page.serve(page, on_choose, on_upscale, on_hide=on_hide, bind=args.bind, port=port, token=token)
    except OSError:
        server = gallery_page.serve(page, on_choose, on_upscale, on_hide=on_hide, bind=args.bind, port=0, token=token)
    url_file.write_text(server.url + "\n", encoding="utf-8")
    result.update({"url": server.url, "address": server.address})
    print(f"Gallery: {server.url}\n(choices save to {printfile.path_for(decklist).name}; Ctrl-C to stop)", file=sys.stderr)
    if server.address not in ("127.0.0.1", "localhost") and not _reachable(server.address, server.port):
        local = f"http://127.0.0.1:{server.port}/?t={server.token}"
        print(f"WARNING  {server.address} does not answer from this Mac. The macOS firewall is probably blocking "
              f"python: allow it in System Settings > Network > Firewall (a prompt may be waiting on screen). "
              f"On the Mac itself use {local}", file=sys.stderr)
        result["warning"] = f"{server.address} not reachable; firewall? Local URL: {local}"
    if args.open:
        send.open_in_browser(server.url)
    try:
        while True:
            import time
            time.sleep(3600)
    except KeyboardInterrupt:
        # The URL file stays, so the next start reuses the same port and token and old links keep working.
        server.stop()
    return result


def run(args: argparse.Namespace) -> None:
    # The download has to finish before the index is opened.
    if args.command == "update":
        return update(args.force)
    if args.command == "placed":
        decklist = Path(args.decklist)
        pf = printfile.load(printfile.path_for(decklist))
        xml = Path(args.xml) if args.xml else _latest_order(decklist, pf.get("printed_as"))
        print(ledger.record(decklist, xml, args.date, pf.get("printed_as")))
        return

    with closing(cards.open_index()) as db:
        if args.command == "art":
            pf, result = art.choose_art(
                db, Path(args.decklist), style=args.style, basics=args.basics, sources=args.source or None,
                renders=not args.no_renders, keep=args.keep, allow_lowres=args.allow_lowres,
                printed_as=args.printed_as, with_tokens=not args.no_tokens, use_ledger=not args.no_ledger,
                artist=args.artist, set_code=args.set)
        elif args.command == "pick":
            result = art.set_art(Path(args.decklist), args.name, args.source, args.id, upscale=args.upscale,
                                 copies=args.copies, drop=args.drop)
        elif args.command == "gallery":
            result = run_gallery(db, args)
        elif args.command == "print":
            result = export.export(db, Path(args.decklist), full=args.full, allow_lowres=args.allow_lowres,
                                   upload=not args.no_upload, stock=args.stock, foil=args.foil,
                                   out=Path(args.out) if args.out else None)
            if args.to and result.get("xml"):
                xml_paths = [Path(result["xml"])]
                result["send"] = (send.to_notmpc(xml_paths, open_browser=not args.no_open) if args.to == "notmpc"
                                  else send.to_mpc(xml_paths, autofill_bin=args.autofill_bin))
        elif args.command == "ship":
            result = ship(db, args)
        elif args.command == "search":
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
        elif args.command == "ideas":
            result = edhrec.commander_ideas(
                db, args.commander, theme=args.theme, per_list=args.per_list, price_max=bounds(args.price)[1])
        elif args.command == "check":
            entries, rules, commanders, problems = load_deck(args)
            if not commanders:
                raise cards.CardDataError("Name the commander with --commander, or as commander = \"...\" in the rules file.")
            result = decks.validate_deck(db, commanders, entries, rules)
            result["errors"]["format"] = problems
            result["valid"] = result["valid"] and not problems
        else:
            result = cards.get_rulings(db, args.name)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1, default=str))
    elif args.command == "art":
        print(format_art(result))
    elif args.command == "pick":
        if result.get("dropped"):
            print(f"{result['name']}: left out of the order")
        else:
            print(f"{result['name']}: {result.get('source')} {result.get('id')} x{result.get('copies')} upscale={result.get('upscale')}")
    elif args.command == "gallery":
        print(result.get("url") or result["page"])
    elif args.command == "print":
        print(format_print(result))
        if result.get("send"):
            print(format_send(result["send"]))
        if not result["ok"]:
            sys.exit(1)
    elif args.command == "ship":
        print(result["text"])
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
            for key in ("price_printing", "game_changer", "rarity", "set", "released_at", "edhrec_rank", "rulings", "scryfall_uri"):
                if key in card:
                    print(f"  {key}: {card[key]}")
    elif args.command == "ideas":
        theme = f", {result['theme']} theme" if result["theme"] else ""
        print(f"{result['commander']}{theme}: {result['decks']} decks on EDHREC (fetched {result['fetched']})")
        print("Themes: " + ", ".join(f"{t['theme']} ({t['decks']})" for t in result["themes"]))
        if result["known_combos"]:
            print("Known combos: " + "; ".join(result["known_combos"]))
        for header, ideas in result["lists"].items():
            print(f"\n{header}")
            for card in ideas:
                share = f"{card['in_decks_pct']}% of decks" if "in_decks_pct" in card else ""
                synergy = f", {card['synergy_pct']:+d}% synergy" if "synergy_pct" in card else ""
                price = f"${card['price_usd']:.2f}" if "price_usd" in card else "$?"
                print(f"  {card['name']} | {card.get('type_line', '')} | {share}{synergy} | {price}")
    elif args.command == "tags":
        for tag in result:
            print(f"{tag['tag']}  ({tag['cards']} cards)  {tag.get('description', '')}")
    else:
        print(result["name"])
        for ruling in result["rulings"]:
            print(f"  {ruling['date']}  {ruling['text']}")
    if args.command == "check" and not result["valid"]:
        sys.exit(1)


def _latest_order(decklist: Path, printed_as: str | None) -> Path:
    """The newest printed/orders/<deck>-<n>.xml, which `mtg print` just wrote."""
    following = ledger.next_order_path(decklist, printed_as)
    number = int(following.stem.rsplit("-", 1)[1]) - 1
    latest = following.with_name(f"{following.stem.rsplit('-', 1)[0]}-{number}.xml")
    if number < 1 or not latest.exists():
        raise cards.CardDataError(f"No order XML found for {decklist.name}; run mtg print first or pass --xml.")
    return latest


def ship(db, args: argparse.Namespace) -> dict:
    """art, then the gallery (in tmux, so it outlives this command), or straight to the XML and the shop."""
    decklists = [Path(d) for d in args.decklist]
    printed_as = args.printed_as or []
    lines, xml_paths, urls = [], [], []
    for i, decklist in enumerate(decklists):
        physical = printed_as[i] if i < len(printed_as) else None
        pf, report = art.choose_art(db, decklist, style=args.style, printed_as=physical, keep=args.keep)
        lines.append(format_art(report))
        if not args.no_gallery:
            url = start_gallery_in_tmux(decklist)
            urls.append(url)
            lines.append(f"  gallery: {url}")
            continue
        result = export.export(db, decklist, allow_lowres=args.allow_lowres)
        lines.append(format_print(result))
        if result.get("xml") and result["ok"]:
            xml_paths.append(Path(result["xml"]))
    if urls:
        lines.append("\nSwap any art in the gallery, then run `mtg print <decklist> --to notmpc` (or ship --no-gallery) to make the order.")
    elif xml_paths:
        sent = send.to_notmpc(xml_paths) if args.to == "notmpc" else send.to_mpc(xml_paths)
        lines.append(format_send(sent))
    return {"text": "\n".join(lines), "gallery_urls": urls, "xml": [str(p) for p in xml_paths]}


def start_gallery_in_tmux(decklist: Path) -> str:
    """Serve the gallery from a tmux session named after the deck, and return its URL."""
    import shutil
    import time
    session = f"mtg-gallery-{decklist.stem}"
    url_file = decklist.with_suffix(".gallery.url")
    # The file from a previous run is kept (its port and token are reused); wait for it to be rewritten.
    before = url_file.stat().st_mtime_ns if url_file.exists() else None
    command = f"cd {Path.cwd()} && uv run mtg gallery {decklist} 2> {decklist.with_suffix('.gallery.log')}"
    if shutil.which("tmux"):
        subprocess.run(["tmux", "kill-session", "-t", session], capture_output=True)
        subprocess.run(["tmux", "new-session", "-d", "-s", session, command], check=True)
    else:
        subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(120):
        if url_file.exists() and url_file.stat().st_mtime_ns != before:
            return url_file.read_text(encoding="utf-8").strip()
        time.sleep(0.5)
    raise cards.CardDataError(f"The gallery did not start; run `uv run mtg gallery {decklist}` by hand to see why.")


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
    ideas = commands.add_parser("ideas", help="what other players run with a commander, from EDHREC (needs internet)")
    ideas.add_argument("commander")
    ideas.add_argument("--theme", help="one theme of the commander's decks, e.g. vampires")
    ideas.add_argument("--price", help="leave out cards above this US dollar price, e.g. '<=5'")
    ideas.add_argument("--per-list", type=int, default=12, help="cards shown per list")
    check = commands.add_parser("check", help="validate a Commander decklist")
    check.add_argument("decklist", help="text file with one '1 Card Name' per line")
    check.add_argument("--commander", action="append",
                       help="commander name (give twice for partners or a background)")
    check.add_argument("--rules", help="deck rules file (default: the decklist's name with .rules.toml)")
    refresh = commands.add_parser("update", help="download the latest data and refresh the index")
    refresh.add_argument("--force", action="store_true", help="download even if the local files are current")

    art_cmd = commands.add_parser("art", help="choose a printing for every card and write <deck>.print.toml")
    art_cmd.add_argument("decklist")
    art_cmd.add_argument("--style", choices=printfile.STYLES, default="fullart")
    art_cmd.add_argument("--basics", choices=("vary", "same"), help="spread basic lands over several arts (default) or one")
    art_cmd.add_argument("--source", action="append", help="mpcfill source to use, in priority order (repeatable)")
    art_cmd.add_argument("--no-renders", action="store_true", help="Scryfall printings only, no community renders")
    art_cmd.add_argument("--keep", action="store_true", help="keep choices the user or the ledger made; fill gaps only")
    art_cmd.add_argument("--allow-lowres", action="store_true", help="accept low-resolution scans when nothing better exists")
    art_cmd.add_argument("--printed-as", help="the physical deck this list upgrades, for the ledger (e.g. treefolk-quickbeam)")
    art_cmd.add_argument("--no-tokens", action="store_true", help="leave out the tokens the deck makes")
    art_cmd.add_argument("--no-ledger", action="store_true", help="ignore what has been printed before")
    art_cmd.add_argument("--artist", help="prefer this artist everywhere")
    art_cmd.add_argument("--set", help="prefer this set code everywhere")

    pick = commands.add_parser("pick", help="set one card's art by hand")
    pick.add_argument("decklist")
    pick.add_argument("name")
    pick.add_argument("--source", choices=("mpcfill", "scryfall"))
    pick.add_argument("--id", help="Drive id (mpcfill) or Scryfall id")
    pick.add_argument("--upscale", choices=printfile.UPSCALE_MODES)
    pick.add_argument("--copies", type=int, help="how many of a token to print")
    pick.add_argument("--drop", action="store_true", help="leave a token out of the order")

    gal = commands.add_parser("gallery", help="write the art gallery page and serve it (phone-friendly)")
    gal.add_argument("decklist")
    gal.add_argument("--bind", help="address to serve on (default: Tailscale, else LAN, else localhost)")
    gal.add_argument("--port", type=int, default=0)
    gal.add_argument("--no-serve", action="store_true", help="write the page only")
    gal.add_argument("--open", action="store_true", help="open the page in the browser")
    gal.add_argument("--full", action="store_true", help="show the whole deck as to-print, ignoring the ledger")

    prt = commands.add_parser("print", help="write the order XML for what is not yet printed")
    prt.add_argument("decklist")
    prt.add_argument("--full", action="store_true", help="the whole deck, ignoring the ledger")
    prt.add_argument("--allow-lowres", action="store_true")
    prt.add_argument("--no-upload", action="store_true", help="prepare images but do not upload them to Drive")
    prt.add_argument("--stock", choices=export.STOCKS)
    prt.add_argument("--foil", action="store_true", default=None)
    prt.add_argument("--out", help="write the XML here instead of the decks repo's printed/orders/")
    prt.add_argument("--to", choices=("notmpc", "mpc"), help="also open the shop with instructions")
    prt.add_argument("--no-open", action="store_true", help="do not open the browser")
    prt.add_argument("--autofill-bin", help="path to the mpc-autofill desktop tool, for --to mpc")

    placed = commands.add_parser("placed", help="record a placed order in the ledger")
    placed.add_argument("decklist")
    placed.add_argument("order", nargs="?", help="the shop's order number (noted in the commit message)")
    placed.add_argument("--date", help="YYYY-MM-DD (default: blank, as the ledger's first rows)")
    placed.add_argument("--xml", help="the order XML (default: the newest in printed/orders/ for this deck)")

    shp = commands.add_parser("ship", help="art, gallery, XML and shop in one go, for one or more decks")
    shp.add_argument("decklist", nargs="+")
    shp.add_argument("--printed-as", action="append", help="physical deck per decklist, in order (repeatable)")
    shp.add_argument("--style", choices=printfile.STYLES, default="fullart")
    shp.add_argument("--keep", action="store_true")
    shp.add_argument("--no-gallery", action="store_true", help="take the defaults and go straight to the order")
    shp.add_argument("--allow-lowres", action="store_true")
    shp.add_argument("--to", choices=("notmpc", "mpc"), default="notmpc")

    try:
        run(parser.parse_args())
    except cards.CardDataError as error:
        sys.exit(str(error))


if __name__ == "__main__":
    main()
