#!/usr/bin/env python3
"""Download the card and rules data the deck builder works from.

Everything lands in data/ (gitignored), grouped by who publishes it:

    data/scryfall/oracle-cards.jsonl.gz   one card per line, per Oracle ID
    data/scryfall/rulings.jsonl.gz        one ruling per line
    data/scryfall/oracle-tags.jsonl.gz    one community tag per line (board wipes, ramp, ...)
    data/scryfall/default-cards.jsonl.gz  one line per printing, used for each card's lowest price
    data/scryfall/catalogs/<name>.json    keyword, type and name lists
    data/scryfall/sets.json
    data/scryfall/symbology.json
    data/rules/comprehensive-rules.txt    as published by Wizards of the Coast
    data/spellbook/variants.json.gz       every combo Commander Spellbook knows, as one JSON object
    data/manifest.json                    what was fetched, from where, and when

Files that are already current are skipped; pass --force to fetch them anyway.
Standard library only, Python 3.9+.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MANIFEST = DATA_DIR / "manifest.json"

USER_AGENT = "mtg-deck-builder/0.1 (+https://github.com/AshleyxAdamson/MTG-Deck-Builder)"
SCRYFALL_API = "https://api.scryfall.com"
RULES_PAGE = "https://magic.wizards.com/en/rules"
COMBOS_URL = "https://json.commanderspellbook.com/variants.json.gz"

# Scryfall asks for at most 10 requests per second; stay well under it.
SCRYFALL_MIN_INTERVAL = 0.15
TIMEOUT = 60
ATTEMPTS = 4
RETRY_STATUSES = {429, 500, 502, 503, 504}

# bulk-data "type" -> path under data/
BULK_FILES = {
    "cards": ("oracle_cards", "scryfall/oracle-cards.jsonl.gz"),
    "rulings": ("rulings", "scryfall/rulings.jsonl.gz"),
    "tags": ("oracle_tags", "scryfall/oracle-tags.jsonl.gz"),
    "printings": ("default_cards", "scryfall/default-cards.jsonl.gz"),
}

# The deck-building subset of /catalog/*. Left out on purpose: artist-names,
# word-bank, flavor-words, watermarks.
CATALOGS = [
    "card-names",
    "keyword-abilities",
    "keyword-actions",
    "ability-words",
    "supertypes",
    "card-types",
    "creature-types",
    "planeswalker-types",
    "land-types",
    "artifact-types",
    "enchantment-types",
    "spell-types",
    "battle-types",
    "powers",
    "toughnesses",
    "loyalties",
]
# Not under /catalog/, but the same kind of reference data.
REFERENCE_LISTS = ["sets", "symbology"]

# Catalogs carry no version stamp, so they are re-fetched once they are this old.
CATALOG_MAX_AGE = timedelta(hours=24)

# Commander Spellbook rebuilds its export every two hours; a day-old copy is fresh enough.
COMBOS_MAX_AGE = timedelta(hours=24)
COMBOS_START = re.compile(rb'\{"timestamp": "([^"]+)", "version": "[^"]*", "variants": \[')

RULES_LINK = re.compile(r'href="(https://media\.wizards\.com/[^"]*MagicCompRules[^"]*\.txt)"')
RULES_FIRST_LINE = b"Magic: The Gathering Comprehensive Rules"

_last_scryfall_call = 0.0


def open_url(url: str, accept: str, headers: dict | None = None):
    """Open url with the headers Scryfall requires, retrying transient failures."""
    global _last_scryfall_call
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept, **(headers or {})})
    throttled = urllib.parse.urlsplit(url).hostname == "api.scryfall.com"
    for attempt in range(1, ATTEMPTS + 1):
        if throttled:
            wait = _last_scryfall_call + SCRYFALL_MIN_INTERVAL - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            _last_scryfall_call = time.monotonic()
        try:
            return urllib.request.urlopen(request, timeout=TIMEOUT)
        except urllib.error.HTTPError as error:
            if error.code not in RETRY_STATUSES or attempt == ATTEMPTS:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == ATTEMPTS:
                raise
        time.sleep(2 ** attempt)


def fetch_json(url: str):
    with open_url(url, "application/json") as response:
        return json.load(response)


def fetch_scryfall_list(url: str) -> dict:
    """Fetch a Scryfall catalog or list as one object, following any pagination."""
    result = page = fetch_json(url)
    while page.get("has_more"):
        page = fetch_json(page["next_page"])
        result["data"].extend(page["data"])
    result.pop("has_more", None)
    result.pop("next_page", None)
    return result


def download(url: str, dest: Path, accept: str = "*/*") -> Path:
    """Stream url into a .part file next to dest and return it.

    The caller checks the .part file and then moves it over dest, so a failed
    or truncated download never replaces a good file.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    with open_url(url, accept) as response, open(part, "wb") as out:
        shutil.copyfileobj(response, out, 1024 * 1024)
    return part


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    with open(part, "w", encoding="utf-8") as out:
        json.dump(value, out, ensure_ascii=False, indent=1)
        out.write("\n")
    os.replace(part, path)


def count_gzip_lines(path: Path) -> int:
    """Count the lines in a gzip file; reading it through also proves it is intact."""
    with gzip.open(path, "rb") as lines:
        return sum(1 for _ in lines)


class Manifest:
    """Record of what is on disk: source URL, version and fetch time per file."""

    def __init__(self):
        self.entries = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}

    def has_version(self, name: str, version: str) -> bool:
        entry = self.entries.get(name)
        return bool(entry) and entry["version"] == version and (DATA_DIR / name).exists()

    def is_recent(self, name: str, max_age: timedelta) -> bool:
        entry = self.entries.get(name)
        if not entry or not (DATA_DIR / name).exists():
            return False
        fetched_at = datetime.fromisoformat(entry["fetched_at"])
        return datetime.now(timezone.utc) - fetched_at < max_age

    def record(self, name: str, source: str, version: str | None = None, **extra) -> None:
        self.entries[name] = {
            "source": source,
            "version": version,
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "bytes": (DATA_DIR / name).stat().st_size,
            **extra,
        }
        write_json(MANIFEST, self.entries)


def fetch_bulk(manifest: Manifest, wanted: list[str], force: bool) -> None:
    listing = {item["type"]: item for item in fetch_json(f"{SCRYFALL_API}/bulk-data")["data"]}
    for key in wanted:
        bulk_type, name = BULK_FILES[key]
        item = listing[bulk_type]
        version = item["updated_at"]
        if not force and manifest.has_version(name, version):
            print(f"  current   {name} ({version})")
            continue
        url = item.get("jsonl_download_uri")
        if not url:
            raise SystemExit(
                f"Scryfall's bulk-data entry for {bulk_type} has no jsonl_download_uri; "
                f"it offers: {sorted(k for k in item if k.endswith('_uri'))}"
            )
        print(f"  fetching  {name} ({item['compressed_size'] / 1e6:.1f} MB)")
        part = download(url, DATA_DIR / name)
        records = count_gzip_lines(part)
        os.replace(part, DATA_DIR / name)
        manifest.record(name, url, version, records=records)


def fetch_catalogs(manifest: Manifest, force: bool) -> None:
    targets = [(f"scryfall/catalogs/{c}.json", f"{SCRYFALL_API}/catalog/{c}") for c in CATALOGS]
    targets += [(f"scryfall/{r}.json", f"{SCRYFALL_API}/{r}") for r in REFERENCE_LISTS]
    for name, url in targets:
        if not force and manifest.is_recent(name, CATALOG_MAX_AGE):
            print(f"  current   {name}")
            continue
        print(f"  fetching  {name}")
        result = fetch_scryfall_list(url)
        write_json(DATA_DIR / name, result)
        manifest.record(name, url, records=len(result["data"]))


def fetch_rules(manifest: Manifest, force: bool) -> None:
    name = "rules/comprehensive-rules.txt"
    with open_url(RULES_PAGE, "text/html") as response:
        page = response.read().decode("utf-8", errors="replace")
    match = RULES_LINK.search(page)
    if not match:
        raise SystemExit(f"No Comprehensive Rules .txt link found on {RULES_PAGE}")
    # The published link has a literal space in it ("MagicCompRules 20260925.txt").
    url = urllib.parse.quote(match.group(1), safe=":/%")
    # The file name is the only version stamp Wizards publishes.
    version = urllib.parse.unquote(url).rsplit("/", 1)[-1]
    if not force and manifest.has_version(name, version):
        print(f"  current   {name} ({version})")
        return
    print(f"  fetching  {name} ({version})")
    part = download(url, DATA_DIR / name, accept="text/plain")
    with open(part, "rb") as rules:
        start = rules.read(len(RULES_FIRST_LINE) + 3)
    if RULES_FIRST_LINE not in start:
        part.unlink()
        raise SystemExit(f"{url} does not look like the Comprehensive Rules; kept the old file")
    os.replace(part, DATA_DIR / name)
    manifest.record(name, url, version)


def fetch_combos(manifest: Manifest, force: bool) -> None:
    name = "spellbook/variants.json.gz"
    if not force and manifest.is_recent(name, COMBOS_MAX_AGE):
        print(f"  current   {name}")
        return
    dest = DATA_DIR / name
    entry = manifest.entries.get(name) if dest.exists() else None
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    try:
        # The ETag is the only version stamp; sending it back gets a 304 when nothing changed.
        unchanged = {"If-None-Match": entry["version"]} if entry and not force else {}
        with open_url(COMBOS_URL, "application/json", unchanged) as response, open(part, "wb") as out:
            version = response.headers["ETag"]
            print(f"  fetching  {name} ({int(response.headers['Content-Length']) / 1e6:.1f} MB)")
            # Served with "Content-Encoding: gzip", which urllib leaves alone: this writes the .gz as is.
            shutil.copyfileobj(response, out, 1024 * 1024)
    except urllib.error.HTTPError as error:
        if error.code != 304:
            raise
        print(f"  current   {name} (built {entry['built_at']})")
        manifest.record(name, COMBOS_URL, entry["version"], built_at=entry["built_at"])
        return
    # Reading the file through proves it is intact.
    with gzip.open(part, "rb") as export:
        start = COMBOS_START.match(export.read(200))
        while export.read(1024 * 1024):
            pass
    if not start:
        part.unlink()
        raise SystemExit(f"{COMBOS_URL} does not look like Commander Spellbook's export; kept the old file")
    os.replace(part, dest)
    manifest.record(name, COMBOS_URL, version, built_at=start.group(1).decode())


def main() -> None:
    groups = [*BULK_FILES, "catalogs", "rules", "combos"]
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--force", action="store_true", help="fetch even if the local file is current")
    parser.add_argument("--only", nargs="+", choices=groups, metavar="GROUP",
                        help=f"fetch only these groups (choices: {', '.join(groups)})")
    args = parser.parse_args()
    wanted = args.only or groups

    manifest = Manifest()
    bulk = [g for g in BULK_FILES if g in wanted]
    try:
        if bulk:
            print("Scryfall bulk data")
            fetch_bulk(manifest, bulk, args.force)
        if "catalogs" in wanted:
            print("Scryfall catalogs")
            fetch_catalogs(manifest, args.force)
        if "rules" in wanted:
            print("Comprehensive Rules")
            fetch_rules(manifest, args.force)
        if "combos" in wanted:
            print("Commander Spellbook combos")
            fetch_combos(manifest, args.force)
    except urllib.error.HTTPError as error:
        sys.exit(f"HTTP {error.code} from {error.url}")
    except urllib.error.URLError as error:
        sys.exit(f"Network error: {error.reason}")
    print(f"Done. Data is in {DATA_DIR}")


if __name__ == "__main__":
    main()
