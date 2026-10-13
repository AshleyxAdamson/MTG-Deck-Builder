# MTG Deck Builder

Tools for building Magic: The Gathering Commander decks with an agent: a local card index, the `mtg` command and the `mtg-cards` MCP server. `README.md` documents all of it.

## Before building, tuning or checking a deck

Three things must be in place on this machine. When one is missing, follow "Setting up on a new machine" in `README.md`.

- **Card data.** `uv run mtg check decks/vampire-plague-elenda.txt` runs and reports the deck, with no "is missing" error.
- **The mtg-cards MCP tools** (`search_cards`, `validate_deck` and the rest) are available in this session. The `uv run mtg ...` commands do the same job from the shell.
- **The `commander-deck` skill** is listed among this session's skills. It lives outside this repo, in [dev-tools](https://github.com/AshleyxAdamson/dev-tools) at `skills/commander-deck/`, linked into `~/.claude/skills/`. Use it for every deck build, tune or review.

## Where things go

- A deck is three files in `decks/`: `<name>.txt` (the decklist), `<name>.rules.toml` (its rules for `mtg check`) and `<name>.md` (notes). Its brief is `decks/briefs/<name>.md`.
- `data/` is downloaded, never committed; `uv run mtg update` refreshes it.
- There is no test suite. Verify a code change by running the commands against the real data.
