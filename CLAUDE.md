# MTG Deck Builder

Tools for building Magic: The Gathering Commander decks with an agent: a local card index, the `mtg` command and the `mtg-cards` MCP server. `README.md` documents all of it.

## Before building, tuning or checking a deck

Three things must be in place on this machine. When one is missing, follow "Setting up on a new machine" in `README.md`.

- **Card data.** `uv run mtg card "Sol Ring"` prints the card, with no "is missing" error.
- **The mtg-cards MCP tools** (`search_cards`, `validate_deck` and the rest) are available in this session. The `uv run mtg ...` commands do the same job from the shell.
- **The `commander-deck` skill** is listed among this session's skills. It lives in this repo at `.claude/skills/commander-deck/`, so a session started in this folder loads it. Use it for every deck build, tune or review.

## Where things go

- A deck is three files in `decks/`: `<name>.txt` (the decklist), `<name>.rules.toml` (its rules for `mtg check`) and `<name>.md` (notes). Its brief is `decks/briefs/<name>.md`. The `.txt` is only `N Card Name` lines (no headers, comments, blank lines or commander line) so it pastes into Moxfield as is, and `mtg check` fails it otherwise; role groups go in the notes.
- `decks/` is ignored by this repo, so each person's decks stay out of it. It may be its own git repo: when `decks/.git` exists, commit deck changes there, never here. `examples/brief.md` is the sample brief that ships.
- `data/` is downloaded, never committed; `uv run mtg update` refreshes it.
- There is no test suite. Verify a code change by running the commands against the real data.

## Printing a deck

Use the `print-deck` skill (`.claude/skills/print-deck/`) for every print, reprint or order. The decks repo's `printed/` folder is the ledger of what is already in the box; never print a card the ledger has unless the user asks. The order XML and the ledger are committed in the decks repo, not here. `docs/spec/print-suite.md` is the design; `docs/research/proxy-printing.md` and `docs/research/upscale-spike.md` the evidence.
