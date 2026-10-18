"""Community card renders from mpcfill.com: search by name, details by Drive id, download.

Needs the internet. mpcfill has an open JSON API that its own editor uses (no key); this
module talks to the live /2/ endpoints, which lag the GitHub repo's /3/. Answers are cached
under data/mpcfill/ and downloaded images under data/art/mpcfill/. The endpoints are
unofficial and may change without notice.
"""
from __future__ import annotations

import difflib
import json
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

from ..cards import DATA_DIR, CardDataError

BASE = "https://mpcfill.com"
USER_AGENT = "mtg-deck-builder/0.1 (+https://github.com/AshleyxAdamson/MTG-Deck-Builder)"
CACHE_DIR = DATA_DIR / "mpcfill"
ART_DIR = DATA_DIR / "art" / "mpcfill"
CACHE_SECONDS = 7 * 24 * 3600
TIMEOUT = 60
MIN_INTERVAL = 0.2
SEARCH_BATCH = 300
CARDS_BATCH = 1000
CARD_TYPES = ("CARD", "TOKEN", "CARDBACK")
FANCY_WORDS = ("borderless", "full art", "fullart", "full-art", "extended", "textless", "showcase")
SOURCES_FILE = Path(__file__).with_name("sources.toml")
DOWNLOAD_EXTENSIONS = {
    "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif", "image/tiff": "tiff",
}

DEFAULT_SOURCES: list[str] = tomllib.loads(SOURCES_FILE.read_text(encoding="utf-8"))["sources"]

_last_request = 0.0


def _throttle() -> None:
    """At most one request per MIN_INTERVAL seconds, across every call in this process."""
    global _last_request
    wait = _last_request + MIN_INTERVAL - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()


def _open(request: urllib.request.Request):
    _throttle()
    return urllib.request.urlopen(request, timeout=TIMEOUT)


def _request(path: str, body: dict | None = None) -> dict:
    """GET (or POST, when there is a body) a JSON endpoint and return the parsed answer."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers)
    try:
        with _open(request) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise CardDataError(
            f"mpcfill answered HTTP {error.code} for {path}. Its API is unofficial and may have changed; try again later.")
    except (urllib.error.URLError, TimeoutError) as error:
        raise CardDataError(f"Could not reach mpcfill ({getattr(error, 'reason', error)}); this lookup needs the internet.")
    except json.JSONDecodeError:
        raise CardDataError(f"mpcfill sent something that is not JSON for {path}. Its API may have changed; try again later.")


def _read_cache(path: Path):
    """The cached JSON, or None when it is missing, unreadable or older than the cache lifetime."""
    try:
        if time.time() - path.stat().st_mtime < CACHE_SECONDS:
            return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    return None


def _write_cache(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def sources() -> list[dict]:
    """Every source mpcfill knows: {pk, key, name, sourceType, externalLink, description}."""
    cached = _read_cache(CACHE_DIR / "sources.json")
    if cached is not None:
        return cached
    found = list(_request("/2/sources/")["results"].values())
    _write_cache(CACHE_DIR / "sources.json", found)
    return found


def _source_pks(source_names: list[str] | None) -> list[list]:
    """[[pk, True], ...]: the preferred names first (that order sets result priority), then every other source.

    Every source is searched, so a card nobody preferred has rendered is still found; the preferred
    ones win ties.
    """
    names = DEFAULT_SOURCES if source_names is None else source_names
    by_name = {source["name"].lower(): source for source in sources()}
    pks, seen = [], set()
    for name in names:
        source = by_name.get(name.lower())
        if source is None:
            close = difflib.get_close_matches(name.lower(), list(by_name), n=5, cutoff=0.5)
            hint = ", ".join(by_name[c]["name"] for c in close) or "run sources() to list them"
            raise CardDataError(f"mpcfill has no source called {name!r}. Closest: {hint}")
        pks.append([source["pk"], True])
        seen.add(source["pk"])
    pks.extend([source["pk"], True] for source in sources() if source["pk"] not in seen)
    return pks


def tag_aliases() -> dict[str, tuple[str, list[str]]]:
    """mpcfill's tag taxonomy as {alias or name, lowercased: (canonical name, [ancestors])}.

    Tags on a render may use any alias; the ancestors let 'Minimalist' also count as
    'Custom-Made Frame' and 'Frame'. Cached for 7 days.
    """
    tree = _read_cache(CACHE_DIR / "tags.json")
    if tree is None:
        tree = _request("/2/tags/")
        _write_cache(CACHE_DIR / "tags.json", tree)
    aliases: dict[str, tuple[str, list[str]]] = {}

    def walk(nodes, ancestors):
        for node in nodes:
            name = node["name"]
            for alias in [name, *node.get("aliases", [])]:
                aliases.setdefault(alias.lower(), (name, ancestors))
            walk(node.get("children", []), [*ancestors, name])

    walk(tree.get("tags", []), [])
    return aliases


def _search_settings(source_names: list[str] | None) -> dict:
    return {
        "searchTypeSettings": {"fuzzySearch": False, "filterCardbacks": False},
        "sourceSettings": {"sources": _source_pks(source_names)},
        "filterSettings": {
            "minimumDPI": 0, "maximumDPI": 1500, "maximumSize": 30,
            "languages": [], "includesTags": [], "excludesTags": ["NSFW"],
        },
    }


def _query(name: str) -> str:
    """mpcfill's form of a card name: lowercase, front face only."""
    return name.split(" // ")[0].strip().lower()


def search(queries: list[str], source_names: list[str] | None = None, card_type: str = "CARD") -> dict[str, list[str]]:
    """Drive ids of the renders of each card name, best first. Keys are the normalised names."""
    if card_type not in CARD_TYPES:
        raise CardDataError(f"card_type must be one of {', '.join(CARD_TYPES)}, not {card_type!r}.")
    wanted = list(dict.fromkeys(_query(q) for q in queries))
    settings = _search_settings(source_names)
    found: dict[str, list[str]] = {}
    for start in range(0, len(wanted), SEARCH_BATCH):
        batch = wanted[start:start + SEARCH_BATCH]
        body = {"queries": [{"query": q, "cardType": card_type} for q in batch], "searchSettings": settings}
        results = _request("/2/editorSearch/", body).get("results", {})
        for q in batch:
            found[q] = list(results.get(q, {}).get(card_type, []))
    return found


def cards(ids: list[str]) -> dict[str, dict]:
    """Details of each render by Drive id: name, source, dpi, size, tags, language, thumbnails.

    Remembered per id for a week, so repeated runs only ask about ids not seen before.
    Ids mpcfill no longer knows are left out of the answer.
    """
    path = CACHE_DIR / "cards.json"
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        stored = {}
    now = time.time()
    fresh = {i: e["card"] for i, e in stored.items() if now - e.get("fetched", 0) < CACHE_SECONDS}
    missing = [i for i in dict.fromkeys(ids) if i not in fresh]
    for start in range(0, len(missing), CARDS_BATCH):
        batch = missing[start:start + CARDS_BATCH]
        got = _request("/2/cards/", {"cardIdentifiers": batch}).get("results", {})
        for identifier, card in got.items():
            stored[identifier] = {"fetched": now, "card": card}
            fresh[identifier] = card
    if missing:
        # Keep only what is still fresh, so the file does not grow without bound.
        keep = {i: e for i, e in stored.items() if now - e.get("fetched", 0) < CACHE_SECONDS}
        _write_cache(path, keep)
    return {i: fresh[i] for i in ids if i in fresh}


def cardbacks(source_names: list[str] | None = None) -> list[str]:
    """Drive ids of the illustrated card backs in the given sources."""
    answer = _request("/2/cardbacks/", {"searchSettings": _search_settings(source_names)})
    return list(answer.get("cardbacks", answer.get("results", [])))


def thumbnail_url(drive_id: str, size: int = 400) -> str:
    return f"https://drive.google.com/thumbnail?sz=w{size}-h{size}&id={drive_id}"


def download_url(drive_id: str) -> str:
    return f"https://drive.google.com/uc?id={drive_id}&export=download&confirm=t"


def download(drive_id: str, dest_dir: Path | None = None, extension: str | None = None) -> Path:
    """Fetch a render from Google Drive to <dest_dir>/<drive_id>.<ext>; an existing file is reused."""
    folder = Path(dest_dir) if dest_dir else ART_DIR
    folder.mkdir(parents=True, exist_ok=True)
    if extension:
        target = folder / f"{drive_id}.{extension.lstrip('.')}"
        if target.exists() and target.stat().st_size > 0:
            return target
    else:
        for existing in folder.glob(f"{drive_id}.*"):
            if existing.suffix != ".part" and existing.stat().st_size > 0:
                return existing
    request = urllib.request.Request(download_url(drive_id), headers={"User-Agent": USER_AGENT})
    failure = (f"Could not fetch Drive file {drive_id} (Google's quota or confirmation page, or the file is gone). "
               "Try again later, or pick another render.")
    try:
        with _open(request) as response:
            content_type = response.headers.get_content_type()
            if content_type == "text/html":
                raise CardDataError(failure)
            if not extension:
                extension = _extension(content_type, response.headers.get("Content-Disposition", ""))
            target = folder / f"{drive_id}.{extension}"
            partial = target.with_suffix(target.suffix + ".part")
            with partial.open("wb") as out:
                while chunk := response.read(1 << 16):
                    out.write(chunk)
    except urllib.error.HTTPError as error:
        raise CardDataError(f"{failure} (HTTP {error.code})")
    except (urllib.error.URLError, TimeoutError) as error:
        raise CardDataError(f"Could not reach Google Drive ({getattr(error, 'reason', error)}); this download needs the internet.")
    if partial.stat().st_size == 0:
        partial.unlink()
        raise CardDataError(failure)
    partial.replace(target)
    return target


def _extension(content_type: str, disposition: str) -> str:
    if content_type in DOWNLOAD_EXTENSIONS:
        return DOWNLOAD_EXTENSIONS[content_type]
    for part in disposition.split(";"):
        part = part.strip()
        if part.lower().startswith("filename="):
            name = part.split("=", 1)[1].strip().strip('"')
            if "." in name:
                return name.rsplit(".", 1)[1].lower()
    return "jpg" if content_type == "application/octet-stream" else content_type.rsplit("/", 1)[-1] or "jpg"


def is_fancy(card: dict) -> bool:
    """Does the name or any tag say borderless, full art, extended, textless or showcase?"""
    text = [card.get("name") or "", *(card.get("tags") or [])]
    return any(word in part.lower() for part in text for word in FANCY_WORDS)


def health() -> bool:
    """Is mpcfill's search engine up? Lenient about the answer's shape ({"online": true} today)."""
    try:
        answer = _request("/2/searchEngineHealth/")
    except CardDataError:
        return False
    if isinstance(answer, dict):
        for key in ("online", "status", "healthy", "ok", "up"):
            if key in answer:
                value = answer[key]
                return value.lower() in ("ok", "up", "online", "true", "healthy") if isinstance(value, str) else bool(value)
        return bool(answer)
    return bool(answer)
