# MTG Deck Builder

## Data

Card and rules data is downloaded on demand, not committed. Fetch it with:

```bash
python3 scripts/fetch_data.py
```

It needs Python 3.9+ and nothing else. Files land in `data/`, which is gitignored:

| Path | What it is | Source |
|---|---|---|
| `data/scryfall/oracle-cards.jsonl.gz` | One card object per line, one per unique card (Oracle ID) | Scryfall bulk data |
| `data/scryfall/rulings.jsonl.gz` | One ruling per line, joined to cards by `oracle_id` | Scryfall bulk data |
| `data/scryfall/oracle-tags.jsonl.gz` | One community tag per line (board wipes, ramp, removal and about 4,500 more), each listing the cards it applies to | Scryfall bulk data |
| `data/scryfall/catalogs/*.json` | Card names, keyword abilities, keyword actions, ability words, supertypes, card types, every subtype list, powers, toughnesses, loyalties | Scryfall `/catalog/*` |
| `data/scryfall/sets.json`, `symbology.json` | All sets; all mana and card symbols | Scryfall `/sets`, `/symbology` |
| `data/rules/comprehensive-rules.txt` | The Comprehensive Rules, byte for byte as published (UTF-8) | magic.wizards.com/en/rules |
| `data/manifest.json` | Source URL, version, fetch time, size and record count for each file | written by the script |

The bulk files stay gzipped. Read them a line at a time:

```python
import gzip, json

with gzip.open("data/scryfall/oracle-cards.jsonl.gz", "rt", encoding="utf-8") as cards:
    for line in cards:
        card = json.loads(line)
```

### Re-running

A second run only downloads what changed:

- Bulk files are skipped while Scryfall's `updated_at` matches the manifest (Scryfall rebuilds them about once a day).
- The Comprehensive Rules are skipped while the published file name, which carries the date, is unchanged.
- Catalogs, sets and symbology have no version stamp, so they are re-fetched once the local copy is over 24 hours old.

`--force` fetches regardless. `--only cards rulings tags catalogs rules` limits the run to the groups named.

## Card search

Searching needs [uv](https://docs.astral.sh/uv/), which installs Python 3.12 and the MCP library on first use. The first search builds a SQLite index at `data/cards.sqlite` (about 2 seconds); it is rebuilt automatically whenever the fetch script brings in new data.

### For agents: MCP server

`uv run mtg-mcp` serves five tools over stdio:

| Tool | What it does |
|---|---|
| `search_cards` | Filter by name, rules text, type line, color identity, colors, mana value, power, toughness, price, keywords, tags, mana produced and format legality (Commander unless told otherwise). Returns the match count and a page of cards. |
| `get_card` | Full details for one card by exact name, including legalities, game-changer flag and each face. A wrong name returns close matches. |
| `get_rulings` | Official rulings for one card. |
| `find_tags` | Finds tags to search by, such as `board-wipe` or `sacrifice-outlet`. |
| `validate_deck` | Checks a Commander list against the format (100 cards, singleton, color identity, legality, unknown names) and against the deck's own rules. Also reports card-type counts, tagged roles and total price. |

Register it with Claude Code once, for every project on this machine:

```bash
claude mcp add --scope user mtg-cards -- uv run --directory "$PWD" mtg-mcp
```

### For people: command line

```bash
uv run mtg search --type vampire --identity WB --price "<=5"
uv run mtg search --type sphinx --identity WUB --legendary
uv run mtg search --tag board-wipe --identity WB --brief
uv run mtg search --type land --produces WB --identity WB
uv run mtg tags sacrifice outlet
uv run mtg card "Unesh, Criosphinx Sovereign" "Sharuum the Hegemon"
uv run mtg rulings "Blood Moon"
uv run mtg check decks/vampire-plague-elenda.txt
uv run mtg update
```

`--brief` prints one line per card. `uv run mtg tags` lists tags matching the words given.

`uv run mtg update` runs the fetch script and then refreshes the index, in one step; `--force` downloads everything again.

Add `--json` before the subcommand for JSON output. `uv run mtg search --help` lists every filter.

### Checking a deck

`uv run mtg check` reads a decklist with one `1 Card Name` per line (`#` starts a comment) and reports every problem at once, along with card-type counts, average mana value, how many cards are tagged ramp, card advantage, removal and board wipe, and the total price. It exits with status 1 when the deck is not valid.

A deck's own rules go in a TOML file next to the decklist with the same name: `elenda.txt` is checked against `elenda.rules.toml` (or pass `--rules`). Every key is optional:

```toml
commander = "Elenda, the Dusk Rose"     # or a list of two; replaces --commander
budget = 150                            # most the deck may cost, in US dollars
max_card_price = 20                     # most any one card may cost
max_game_changers = 0                   # cards on Commander's game-changer list
not_together = [["Sanguine Bond", "Exquisite Blood"]]   # never all of these at once
banned = ["Armageddon"]                 # never these

[limits]                                # most cards allowed with each tag
board-wipe = 2
mass-land-denial = 0
extra-turn = 0
```

A misspelled rule or an unknown tag is an error, not a silent pass. Rules that depend on prices come with a warning when a card in the deck has no price.

### Things to know

- Searches return only Commander-legal cards. `--legal modern` (`legal_in: "modern"` in MCP) searches another format; `--legal any` (`legal_in: "any"`) turns the legality filter off.
- `--identity WB` (`color_identity` in MCP) means the card fits in a white-black deck: its color identity is W, B, WB or colorless. This is the Commander deck-building rule.
- Tokens, emblems, art cards, dungeons, planes and schemes are left out unless you ask for extras.
- Double-faced, split and adventure cards are one entry; both faces' text is searchable and either face's name finds the card.
- Prices are for the one recent printing Scryfall picks per card, not the cheapest printing, and some cards have no price. They are a snapshot from the last download; `mtg update` refreshes them.
- Tags come from Scryfall's community Tagger project and say what a card does. A tag includes its more specific children, so `removal` covers `spot-removal` and `board-wipe`. They are other people's judgment and not every card is tagged.
- Deck checks cannot detect combos or judge how a deck plays. There is no tag for stax, and "no infinite combos" stays a matter for whoever builds the deck.

### Network access

The script talks to `api.scryfall.com`, `data.scryfall.io`, `magic.wizards.com` and `media.wizards.com`. In a sandboxed environment all four need to be allowed.
