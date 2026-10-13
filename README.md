# MTG Deck Builder

Local card search, deck checks and an MCP server for building Magic: The Gathering Commander decks with an agent.

## Setting up on a new machine

1. Install [uv](https://docs.astral.sh/uv/) (`brew install uv` on a Mac) and the Claude Code CLI.
2. Clone this repo, and from its root download the data and build the indexes. This fetches about 145 MB into `data/`:

   ```bash
   uv run mtg update
   ```

3. Register the MCP server with Claude Code, for every project on the machine:

   ```bash
   claude mcp add --scope user mtg-cards -- uv run --directory "$PWD" mtg-mcp
   ```

4. Get the `commander-deck` skill, which lives in the [dev-tools](https://github.com/AshleyxAdamson/dev-tools) repo. Clone or update `~/dev-tools`, then run its health check, which links every skill into `~/.claude/skills/`:

   ```bash
   ~/dev-tools/bin/check-dev-tools-health.sh
   ```

5. Start a new Claude Code session in this folder and ask for a deck:

   ```text
   Use the commander-deck skill to build the deck in decks/briefs/sphinx-oracle.md.
   ```

The rest of this file explains each part.

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
| `data/scryfall/default-cards.jsonl.gz` | One line per printing of every card (about 79 MB), used to find each card's lowest price | Scryfall bulk data |
| `data/scryfall/oracle-tags.jsonl.gz` | One community tag per line (board wipes, ramp, removal and about 4,500 more), each listing the cards it applies to | Scryfall bulk data |
| `data/scryfall/catalogs/*.json` | Card names, keyword abilities, keyword actions, ability words, supertypes, card types, every subtype list, powers, toughnesses, loyalties | Scryfall `/catalog/*` |
| `data/scryfall/sets.json`, `symbology.json` | All sets; all mana and card symbols | Scryfall `/sets`, `/symbology` |
| `data/rules/comprehensive-rules.txt` | The Comprehensive Rules, byte for byte as published (UTF-8) | magic.wizards.com/en/rules |
| `data/spellbook/variants.json.gz` | Every combo Commander Spellbook knows (about 114,000), as one JSON object (29 MB; 690 MB unzipped) | [Commander Spellbook](https://commanderspellbook.com) bulk export |
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
- The combo export is rebuilt every two hours, so it is left alone until the local copy is over 24 hours old, and then downloaded only if its ETag has changed.

`--force` fetches regardless. `--only cards rulings tags printings catalogs rules combos` limits the run to the groups named.

Combo data is from [Commander Spellbook](https://commanderspellbook.com), a community project; each combo the deck check reports links to its page there.

## Card search

Searching needs [uv](https://docs.astral.sh/uv/), which installs Python 3.12 and the MCP library on first use. The first search builds a SQLite index at `data/cards.sqlite` (a few seconds); it is rebuilt automatically whenever the fetch script brings in new data. The first deck check builds a second index, `data/combos.sqlite`, the same way.

### For agents: MCP server

`uv run mtg-mcp` serves six tools over stdio:

| Tool | What it does |
|---|---|
| `search_cards` | Filter by name, rules text, type line, color identity, colors, mana value, power, toughness, price, keywords, tags, mana produced and format legality (Commander unless told otherwise). Returns the match count and a page of cards. |
| `get_card` | Full details for one card by exact name, including legalities, game-changer flag and each face. A wrong name returns close matches. |
| `get_rulings` | Official rulings for one card. |
| `find_tags` | Finds tags to search by, such as `board-wipe` or `sacrifice-outlet`. |
| `commander_ideas` | What other players run with a commander, from EDHREC: top and high-synergy cards, themes, average deck shape, known combos. Needs the internet on first lookup. |
| `validate_deck` | Checks a Commander list against the format (100 cards, singleton, color identity, legality, unknown names) and against the deck's own rules. Also reports the known combos in the deck and those one card away, card-type counts, tagged roles and total price. |

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
uv run mtg ideas "Elenda, the Dusk Rose" --theme vampires --price "<=5"
uv run mtg check decks/vampire-plague-elenda.txt
uv run mtg update
```

`--brief` prints one line per card. `uv run mtg tags` lists tags matching the words given.

A decklist in `decks/` is bare `N Card Name` lines: no `#` headers, no blank lines and no commander line. The commander lives in the deck's rules file as `commander`, and `mtg check` counts it as the 100th card. The whole file pastes into Moxfield as is (`pbcopy < decks/vampire-plague-elenda.txt` copies it), and you set the commander in Moxfield's own commander slot. Role groups go in the deck's notes. `mtg check` fails a file that isn't paste-ready and names each offending line.

`uv run mtg ideas` is the one command that needs the internet. EDHREC has no bulk download, so each commander's page is fetched on first use and cached in `data/edhrec/` for a week. It reads an unofficial endpoint that could change.

`uv run mtg update` runs the fetch script and then refreshes the index, in one step; `--force` downloads everything again.

Add `--json` before the subcommand for JSON output. `uv run mtg search --help` lists every filter.

### Checking a deck

`uv run mtg check` reads a decklist with one `1 Card Name` per line and reports every problem at once, including any line that keeps it from pasting into Moxfield as is (a `#` or `//` comment, a blank line, the commander), along with card-type counts, average mana value, how many cards are tagged ramp, card advantage, removal and board wipe, the total price, and the known combos the deck holds or is one card away from. It exits with status 1 when the deck is not valid.

A deck's own rules go in a TOML file next to the decklist with the same name: `elenda.txt` is checked against `elenda.rules.toml` (or pass `--rules`). Every key is optional:

```toml
commander = "Elenda, the Dusk Rose"     # or a list of two; replaces --commander
budget = 150                            # most the deck may cost, in US dollars
max_card_price = 20                     # most any one card may cost
max_game_changers = 0                   # cards on Commander's game-changer list
max_infinite_combos = 0                 # known infinite combos the deck may hold
max_combos = 0                          # stricter: any known combo, infinite or not
not_together = [["Sanguine Bond", "Exquisite Blood"]]   # never all of these at once
banned = ["Armageddon"]                 # never these

[limits]                                # most cards allowed with each tag or card type
board-wipe = 2
mass-land-denial = 0
extra-turn = 0

[minimums]                              # fewest cards needed with each tag or card type
lands = 36
ramp = 10
```

A misspelled rule or an unknown tag is an error, not a silent pass. Rules that depend on prices come with a warning when a card in the deck has no price.

### Combos

Every check compares the deck with Commander Spellbook's list of combos, offline, and reports three groups:

- **In the deck:** every card of the combo is in the list. These are what `max_infinite_combos` and `max_combos` count. Without such a rule they are shown as information.
- **Possible:** every named card is in the list, and the combo also needs "any persist creature" or another kind of card. Whether the deck holds one is not checked, so this is a warning and never fails a rule.
- **One card away:** the ten most popular combos, within the commander's colors, that adding one card would complete. These are the cards to be careful with when changing the deck.

A combo is called infinite when one of its results is named "Infinite ...". "Near-infinite" loops, which stop when something such as a library runs out, and combos that win or lock the game with no loop are labeled as such and are not counted as infinite; `max_combos` counts them.

A clean result means the deck has no *known* combo. The list holds what people have submitted, so it is not proof that no combo exists, and a combo's conditions ("you have a way to gain life") are not checked against the deck.

### Things to know

- Searches return only Commander-legal cards. `--legal modern` (`legal_in: "modern"` in MCP) searches another format; `--legal any` (`legal_in: "any"`) turns the legality filter off.
- `--identity WB` (`color_identity` in MCP) means the card fits in a white-black deck: its color identity is W, B, WB or colorless. This is the Commander deck-building rule.
- Tokens, emblems, art cards, dungeons, planes and schemes are left out unless you ask for extras.
- Double-faced, split and adventure cards are one entry; both faces' text is searchable and either face's name finds the card.
- A card's price is the lowest US dollar price among its paper printings, in any finish. Oversized, gold-bordered and collector's-edition printings are ignored unless nothing else is priced. Prices are a snapshot from the last download; `mtg update` refreshes them.
- Tags come from Scryfall's community Tagger project and say what a card does. A tag includes its more specific children, so `removal` covers `spot-removal` and `board-wipe`. They are other people's judgment and not every card is tagged.
- Deck checks find known combos only (see Combos above) and cannot judge how a deck plays. There is no tag for stax.

## Building decks

The `commander-deck` Claude skill walks an agent from a deck brief to a checked decklist with the tools above: read the brief, write its rules file, set role counts, gather candidates, cut to 100, check, and review how the deck will feel at the table. It lives in the [dev-tools](https://github.com/AshleyxAdamson/dev-tools) repo at `skills/commander-deck/`, with the baseline numbers for a casual deck and a starting rules file, and is linked into `~/.claude/skills/` from there.

Deck briefs live in `decks/briefs/`, and each deck is a decklist, a rules file and notes in `decks/`. The evidence behind the skill's baseline and behind combo detection is in `docs/research/`.

### Network access

The script talks to `api.scryfall.com`, `data.scryfall.io`, `magic.wizards.com`, `media.wizards.com` and `json.commanderspellbook.com`. In a sandboxed environment all five need to be allowed. `mtg ideas` also needs `json.edhrec.com`.
