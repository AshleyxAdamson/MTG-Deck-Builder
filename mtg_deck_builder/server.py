"""MCP server exposing the local card index to agents.

Run with `uv run mtg-mcp`; it speaks MCP over stdio.
"""
from __future__ import annotations

from contextlib import closing, contextmanager
from typing import Annotated, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from . import cards, decks

server = MCPServer(
    "mtg-cards",
    instructions=(
        "Local Magic: The Gathering card database (Scryfall Oracle data, one entry per unique card). "
        "Use search_cards to find cards for a deck, get_card for one card's full details, "
        "get_rulings for official rulings, find_tags to discover community tags such as board-wipe, ramp or "
        "sacrifice-outlet, and validate_deck to check a Commander list against the format and the deck's own "
        "rules. search_cards returns only Commander-legal cards by default; "
        "pass legal_in with another format name to search that format instead, or legal_in='any' to "
        "search every card regardless of legality. For Commander, always pass the commander's colors as "
        "color_identity so only cards that fit the deck come back."
    ),
)

Sort = Literal["popularity", "name", "mana_value", "price", "priciest", "newest"]


@contextmanager
def card_index():
    """Open the card index, passing expected failures to the agent as readable errors."""
    try:
        with closing(cards.open_index()) as db:
            yield db
    except cards.CardDataError as error:
        raise ToolError(str(error)) from error


@server.tool()
def search_cards(
    name: Annotated[str | None, Field(description="Part of the card name.")] = None,
    text: Annotated[list[str] | None, Field(
        description="Phrases that must all appear in the rules text, e.g. ['whenever a creature dies', 'draw a card']. "
                    "Matched literally, ignoring case; both faces of a double-faced card are searched.")] = None,
    types: Annotated[list[str] | None, Field(
        description="Words that must all appear in the type line, e.g. ['Legendary', 'Creature', 'Vampire'].")] = None,
    color_identity: Annotated[str | None, Field(
        description="Colors the deck may use, as letters from WUBRG, e.g. 'WB'. Returns only cards whose color "
                    "identity fits inside these colors (colorless cards always fit). 'C' means colorless only.")] = None,
    colors: Annotated[str | None, Field(
        description="Colors the card itself must be, e.g. 'G' for green cards (including multicolor). "
                    "'C' means colorless.")] = None,
    mana_value_min: Annotated[float | None, Field(description="Lowest mana value (converted mana cost).")] = None,
    mana_value_max: Annotated[float | None, Field(description="Highest mana value.")] = None,
    power_min: Annotated[float | None, Field(description="Lowest power. Cards with * power never match.")] = None,
    power_max: Annotated[float | None, Field(description="Highest power.")] = None,
    toughness_min: Annotated[float | None, Field(description="Lowest toughness.")] = None,
    toughness_max: Annotated[float | None, Field(description="Highest toughness.")] = None,
    price_min: Annotated[float | None, Field(description="Lowest price in US dollars.")] = None,
    price_max: Annotated[float | None, Field(
        description="Highest price in US dollars. Cards with no price never match a price filter. The price is "
                    "for one recent printing, not necessarily the cheapest.")] = None,
    keywords: Annotated[list[str] | None, Field(
        description="Keyword abilities the card must all have, e.g. ['Flying', 'Deathtouch'].")] = None,
    tags: Annotated[list[str] | None, Field(
        description="Community tags the card must all have, describing what it does: e.g. 'removal', "
                    "'board-wipe', 'ramp', 'card-advantage', 'counterspell', 'tutor', 'reanimate', "
                    "'sacrifice-outlet', 'anthem', 'mana-rock'. A tag includes its more specific child tags. "
                    "Use find_tags to discover others.")] = None,
    produces: Annotated[str | None, Field(
        description="Colors of mana the card can make, e.g. 'WB' with types ['Land'] for white-black lands.")] = None,
    legal_in: Annotated[str, Field(
        description="Format the card must be legal in, e.g. 'commander', 'modern', 'standard', 'pauper'. "
                    "Defaults to 'commander'. Pass 'any' to turn the legality filter off and search every card, "
                    "including ones banned in Commander.")] = "commander",
    include_extras: Annotated[bool, Field(
        description="Also return tokens, emblems, art cards, planes and schemes.")] = False,
    sort: Annotated[Sort, Field(description="'popularity' is EDHREC rank, most played first.")] = "popularity",
    limit: Annotated[int, Field(description="Cards to return, at most 100.")] = 20,
    offset: Annotated[int, Field(description="Skip this many results, for paging.")] = 0,
) -> dict:
    """Search every Magic card by name, rules text, type, colors, stats, price, keywords and legality.

    All filters given must match. Only Commander-legal cards are returned unless legal_in names
    another format, or is 'any' for no legality filter. Returns the total number of matches and a
    page of cards with name, mana cost, type line, rules text, power/toughness, color identity and price.
    """
    with card_index() as db:
        return cards.search_cards(
            db, name=name, text=text, types=types, color_identity=color_identity, colors=colors,
            mana_value_min=mana_value_min, mana_value_max=mana_value_max,
            power_min=power_min, power_max=power_max,
            toughness_min=toughness_min, toughness_max=toughness_max,
            price_min=price_min, price_max=price_max, keywords=keywords, tags=tags, produces=produces,
            legal_in=None if legal_in.lower() == "any" else legal_in,
            include_extras=include_extras,
            sort=sort, limit=limit, offset=offset,
        )


@server.tool()
def get_card(
    name: Annotated[str, Field(
        description="Exact card name, any capitalization. One face's name works for double-faced cards.")],
) -> dict:
    """Full details for one card: text, colors and color identity, keywords, community tags, formats it is
    legal or banned in, Commander game-changer flag, price, rarity, popularity, each face, and how many
    rulings it has.

    If the name is not found, the error lists close matches.
    """
    with card_index() as db:
        return cards.get_card(db, name)


@server.tool()
def get_rulings(
    name: Annotated[str, Field(description="Exact card name, any capitalization.")],
) -> dict:
    """Official rulings and clarifications for one card, oldest first."""
    with card_index() as db:
        return cards.get_rulings(db, name)


@server.tool()
def find_tags(
    query: Annotated[str, Field(description="Words to look for in tag names and descriptions, e.g. 'wipe' or 'token'.")],
) -> list[dict]:
    """Find community tags to use with search_cards, largest first, with how many cards each covers."""
    with card_index() as db:
        return cards.find_tags(db, query)


@server.tool()
def validate_deck(
    commanders: Annotated[list[str], Field(
        description="The commander's exact name; two names for partners or a commander with a background.")],
    cards_in_deck: Annotated[list[str], Field(
        description="The deck, one entry per card: 'Sol Ring', or '12 Swamp' for several copies. "
                    "The commander may be included or left out; it is counted once either way.")],
    rules: Annotated[dict | None, Field(
        description="The deck's own rules, usually from its brief. Keys, all optional: budget (max total USD), "
                    "max_card_price (USD), max_game_changers (count), not_together (lists of card names that "
                    "must not all be in the deck, e.g. [['Sanguine Bond', 'Exquisite Blood']]), banned (card "
                    "names), limits (tag -> most cards allowed, e.g. {'board-wipe': 2, 'extra-turn': 0}).")] = None,
) -> dict:
    """Check a Commander deck: exactly 100 cards, one copy of each card except basic lands, every card
    inside the commanders' color identity and legal in Commander, and every name a real card.

    Reports all problems at once, with close matches for unknown names. `rules` holds one entry per deck
    rule with ok true or false; `stats` counts card types and tagged roles (ramp, card-advantage, removal,
    sweeper); `budget` gives the total price and most expensive cards. `valid` is true only when the format
    checks and every rule pass. It cannot detect combos or judge how the deck plays.
    """
    with card_index() as db:
        return decks.validate_deck(db, commanders, decks.parse_decklist("\n".join(cards_in_deck)), rules)


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()
