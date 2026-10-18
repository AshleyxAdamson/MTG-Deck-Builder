"""The tokens a deck makes, from Scryfall's related parts, so they can be printed too."""
from __future__ import annotations

import sqlite3
from collections import Counter

from .. import cards

MAX_COPIES = 4


def tokens_for_deck(db: sqlite3.Connection, rows: dict[str, sqlite3.Row]) -> list[dict]:
    """One entry per distinct token the deck's cards make.

    copies = min(4, number of cards that make it). Each token is identified by its own
    Oracle ID, so the same token across sets counts once; its name and type come from
    its newest printing.
    """
    makers: dict[str, list[str]] = {}
    for name, row in rows.items():
        for token_id in cards.token_oracle_ids(db, row["oracle_id"]):
            makers.setdefault(token_id, []).append(name)
    tokens = []
    for token_id, names in makers.items():
        printings = cards.printings_of(db, token_id)
        if not printings:
            continue
        newest = printings[0]
        tokens.append({
            "oracle_id": token_id,
            "token": newest["name"],
            "name": f"{newest['name']} token",
            "copies": min(MAX_COPIES, len(names)),
            "made_by": sorted(names),
        })
    # Two different tokens can share a name (a 2/2 Treefolk and a 0/4 Treefolk); tell them apart by a maker.
    by_name = Counter(t["name"] for t in tokens)
    for token in tokens:
        if by_name[token["name"]] > 1:
            token["name"] = f"{token['token']} token ({token['made_by'][0]})"
    tokens.sort(key=lambda t: t["name"])
    return tokens


def token_counts(tokens: list[dict]) -> Counter:
    return Counter({t["name"]: t["copies"] for t in tokens})
