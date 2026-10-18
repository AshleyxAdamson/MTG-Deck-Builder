# Spec: from decklist to printed deck, by talking to the agent

Status: proposal, 2026-10-17. Evidence is in [`docs/research/proxy-printing.md`](../research/proxy-printing.md).

## Goal

Today the repo stops at a checked decklist that pastes into Moxfield. From there the user does four manual steps: Moxfield, pick art on mpcfill.com, download the XML, upload it to notmpc.com. This spec adds the rest so a session goes:

> "Build the Treefolk deck" → "Pick full-art printings and show me" → user clicks a few alternatives in a gallery → "Send it to notmpc" (or "print it here").

Moxfield drops out. mpcfill.com drops out as a website but stays as the image library behind the scenes. The print shop stays, because none has an API; the agent gets the user to the pay button with the order already filled.

## Non-goals

- Designing custom cards or alters. Only existing Magic cards, with existing printings or community renders.
- Running or replacing mpcfill.com. We call its public JSON API and read its XML format; we host nothing.
- Paying for the user. Checkout on a print shop stays a human step.
- Tokens and card backs beyond one chosen back for the whole deck (tokens are a later milestone).

## The flow

```
decks/<name>.txt  ──mtg art──▶  decks/<name>.print.toml  ──mtg gallery──▶  browser (user clicks)
    (exists)                       (one printing per card)        ▲    │ writes back
                                            │ ◀─────────────────────────┘
                                            ▼
                                        mtg print
                          ┌─────────────────┼──────────────────┐
                     xml (notmpc / MPC)   pdf (home)        send (lpr)
```

Four new commands, each also an MCP tool, each a small Python module under `mtg_deck_builder/printing/`. Everything runs from the existing `uv run mtg ...` entry point and reads the existing deck files; nothing changes for `mtg check` or the deck format.

## Step 1: choose a printing for every card (`mtg art`)

```bash
uv run mtg art decks/treefolk-quickbeam.txt            # writes decks/treefolk-quickbeam.print.toml
uv run mtg art decks/treefolk-quickbeam.txt --style borderless --no-renders --basics vary
```

For each unique name in the decklist plus the commander from the rules file, gather candidates from two sources and pick one.

**Source A: mpcfill community renders** (`printing/mpcfill.py`). One POST to `https://mpcfill.com/2/editorSearch/` with every name (up to 300 per call) and the user's ranked source list, then one POST to `/2/cards/` with the returned ids (up to 1000) for name, source, dpi, size, tags, language and thumbnails. The default source order ships in `printing/sources.toml`: JohnPrime (borderless), MrTeferi, Chilli_Axe, WarpDandy, Nelynes, SilvanMTG, PsilosX, Trix Are For Scoot. The user can reorder or drop sources in the deck's print file. Results come back already ranked by mpcfill's priority and our source order, so the first id is the default. Needs the internet; a failure here is a warning, not an error, and the Scryfall source carries on.

**Source B: Scryfall printings** (`printing/printings.py`). Read `default-cards.jsonl.gz`, which the repo already downloads, into a new `printings` table in `data/cards.sqlite` (bump `SCHEMA_VERSION`): `oracle_id, scryfall_id, set_code, set_name, collector_number, released_at, lang, games, image_status, full_art, textless, border_color, frame, frame_effects, promo_types, finishes, set_type, security_stamp, artist, layout, image_png, image_normal, back_image_png, back_image_normal`. For transform and modal double-faced cards the image fields come from `card_faces[0]` and `card_faces[1]`; every other layout keeps them at the root. Filter out anything with `image_status` other than `highres_scan`, non-English, digital-only, oversized, and gold, silver or white borders. Offline.

**Scoring.** A `--style` picks the ranking; the default is `fullart`:

| Signal | fullart | borderless | classic | newest |
|---|---|---|---|---|
| mpcfill render whose name or tags say Borderless, Full Art, Extended or Textless | +6 | +6 | 0 | 0 |
| any other mpcfill render | +4 | +3 | 0 | 0 |
| Scryfall `border_color = borderless` | +3 | +4 | -5 | 0 |
| Scryfall `full_art` | +3 | +2 | -5 | 0 |
| Scryfall `frame_effects` has `showcase` or `extendedart` | +2 | +1 | -5 | 0 |
| Scryfall `frame_effects` has `inverted` | +1 | +1 | -5 | 0 |
| Scryfall `promo_types` has `universesbeyond` | -2 | -2 | -5 | 0 |
| Scryfall `frame = 2015`, plain black border | 0 | 0 | +3 | 0 |
| newest `released_at` among ties | tie-break | tie-break | tie-break | +1 per year |

A render with a dpi below 600 loses 2. The user can pin an artist (`--artist "John Avon"`) or a set (`--set sld`) for one card or for all. A card with no candidate at all (new cards sit at placeholder quality on Scryfall for days and have no render for weeks) is written with `status = "missing"` and listed in the command's output; printing refuses until every card has an image or the user passes `--allow-lowres`.

**Basic lands.** `--basics same` (default) picks one art for all copies; `--basics vary` spreads the copies over the top N candidates for that land, N = min(copies, 4). The print file records the split per slot.

**Output: `decks/<name>.print.toml`.** This is the deck's print state, next to its `.txt`, `.rules.toml` and `.md`, so it lives in the user's decks repo and survives sessions:

```toml
# Written by `mtg art` on 2026-10-17; edited by the gallery. Re-run `mtg art --keep` to fill gaps only.
deck = "treefolk-quickbeam.txt"
style = "fullart"
stock = "(S33) Superior Smooth"      # notmpc only offers S33; MPC defaults to S30
foil = false
cardback = { source = "mpcfill", id = "16g2UamJ2jzwNHovLesvsinvd6_qPkZfy", name = "MTG back (black)" }
sources = ["JohnPrime", "MrTeferi", "Chilli_Axe", "WarpDandy", "Nelynes", "SilvanMTG", "PsilosX"]

[[cards]]
name = "Cultivate"
copies = 1
source = "mpcfill"
id = "1dhVvU5rAqsBx9a-LwwKz5RpHXeTp6xKG"
label = "Cultivate (Borderless Uichi Ukumo)"      # mpcfill name, or "STA 51, Jason Felix" for Scryfall
dpi = 1200
chosen_by = "default"                            # default | user | pinned

[[cards]]
name = "Forest"
copies = 38
source = "scryfall"
id = "a3b1...-scryfall-id"
label = "ZNR 280, Adam Paquette (full art)"
dpi = 300
chosen_by = "user"
slots = { "a3b1..." = 20, "9f0c..." = 18 }        # only when copies are spread over several arts

[[cards]]
name = "Delver of Secrets // Insectile Aberration"
copies = 1
source = "scryfall"
id = "11bf83bb-..."
back_id = "11bf83bb-..."                         # same printing, back face; a DFC always prints both faces
label = "MID 47, Nils Hamm"
dpi = 300

[[cards]]
name = "Quickbeam, Upstart Ent"
copies = 1
status = "missing"                               # no high-resolution image anywhere yet
```

Every record carries enough to rebuild the image URL without a lookup: mpcfill ids download from `https://drive.google.com/uc?id=<id>&export=download`, Scryfall ids from the `image_png` column. `mtg art --keep` re-runs only for cards without a `chosen_by = "user"` entry, so a decklist edit does not throw away clicks.

## Step 2: the gallery (`mtg gallery`)

```bash
uv run mtg gallery decks/treefolk-quickbeam.txt           # writes decks/treefolk-quickbeam.gallery.html and opens it
uv run mtg gallery decks/treefolk-quickbeam.txt --serve   # same, plus a local server so clicks save themselves
```

One HTML file, no build step, no framework, written from a template string in `printing/gallery.py`. One row per deck entry, grouped by role when the notes name roles, otherwise by type. Each row shows the chosen image large on the left and the alternatives as a horizontal strip of thumbnails on the right, with a caption per thumbnail (source, set or render name, artist, dpi, a "render" or "scan" badge, and a red "low res" badge when under 600 dpi). Clicking a thumbnail makes it the chosen one. Thumbnails come straight from Drive (`https://drive.google.com/thumbnail?sz=w400-h400&id=<id>`) and Scryfall (`image_normal`), so the page is light and the images are never stored before the user chooses. A filter bar at the top: style (same four as `--style`), renders only, scans only, one artist, hide Universes Beyond. A header shows the count of chosen renders, chosen scans, missing cards, and the estimated order size against the MPC brackets (18, 36, 55, 72, 90, 108, 126, 144, 162, 180, 198, 216, 234, 396, 504, 612).

**Getting clicks back to the file** has two modes, and the page works the same in both:

- **Served** (`--serve`, the default when the agent runs it): a `http.server` from the standard library on `127.0.0.1:<random port>` serves the page and accepts `POST /choose {name, source, id}`, which rewrites that card's entry in the print file with `chosen_by = "user"`. The agent runs it in the background, tells the user the URL, and reads the print file when the user says they are done. `Ctrl-C` or `mtg gallery --stop` ends it.
- **Static** (`file://` open, or the server is gone): choices go to `localStorage`, and a "Copy choices" button puts a TOML fragment on the clipboard for the user to paste to the agent, which applies it with `mtg art --apply -`.

Basic lands get one extra control: a "spread over N arts" stepper that sets the `slots` table.

The page never crops or recolours a card image and shows the artist under every thumbnail, which keeps it inside Scryfall's image rules.

## Step 3: export and send (`mtg print`)

```bash
uv run mtg print decks/treefolk-quickbeam.txt xml            # decks/treefolk-quickbeam.xml for notmpc or MPC
uv run mtg print decks/treefolk-quickbeam.txt pdf            # decks/treefolk-quickbeam.pdf, 3x3 per Letter page
uv run mtg print decks/treefolk-quickbeam.txt send --to notmpc
uv run mtg print decks/treefolk-quickbeam.txt send --to printer [--printer NAME]
```

**Preflight** runs first for every target: the print file exists, every card in the decklist has an entry (the decklist is the source of truth; a stale print file fails with the diff), no entry is `missing`, every image resolves (HEAD on Drive and Scryfall, cached for a day), and the total slot count is 100 or whatever the list sums to. Problems are listed all at once, the way `mtg check` does.

**`xml`** writes the MPC Autofill order:

```xml
<order>
  <details>
    <quantity>100</quantity>
    <stock>(S33) Superior Smooth</stock>
    <foil>false</foil>
  </details>
  <fronts>
    <card><id>1dhVvU5rAqsBx9a-LwwKz5RpHXeTp6xKG</id><slots>0</slots><name>Cultivate (Borderless Uichi Ukumo).jpg</name><query>cultivate</query></card>
    <card><id>cards/forest-znr-280.png</id><sourceType>Local File</sourceType><slots>62,63,...</slots><name>forest-znr-280.png</name><query>forest</query></card>
  </fronts>
  <backs>
    <card><id>cards/delver-mid-47-back.png</id><sourceType>Local File</sourceType><slots>17</slots><name>...</name><query>delver of secrets</query></card>
  </backs>
  <cardback>16g2UamJ2jzwNHovLesvsinvd6_qPkZfy</cardback>
</order>
```

Slots are 0-indexed in decklist order, copies expanded. mpcfill renders go in by Drive id, which is what notmpc and the mpcfill desktop tool both resolve. Scryfall images cannot go in by URL, so the exporter downloads the PNG to `decks/cards/`, adds the bleed (see below), and references it as a local file. The `<backs>` element is always written, empty when there are no double-faced cards, because the parser expects it. `--stock` overrides the print file; `--foil` is refused for `(P10) Plastic`.

Open question for a spike: whether notmpc's uploader accepts `Local File` entries, or only Drive ids. If not, the fallback is to upload the Scryfall-sourced cards to a Drive folder of the user's own, or to put them in the deck as separate single-image uploads. The spike is a 5-card XML with one Scryfall card, uploaded by hand.

**Bleed for Scryfall images** (`printing/bleed.py`, needs Pillow, the one new dependency): take the 745x1040 RGBA PNG, fill the transparent corners with the border colour sampled at the edge midpoint, pad 36 px on each side by repeating the edge row and column, and resize to 816x1110. The result is the community standard 63x88 mm plus 1/8 inch bleed at 300 dpi, above notmpc's 447x597 minimum and matching its 822x1122 template within six pixels. Renders are passed through untouched. Nothing is sharpened, recoloured or cropped.

**`pdf`** lays out fronts for home printing: US Letter (A4 with `--paper a4`), nine cards per page at exactly 63x88 mm trimmed (bleed removed), 2 mm gutters, hairline cut marks in the gutters and margins, page numbers, and the deck name in the footer. Backs are a second PDF, mirrored per page, written only with `--backs`. Pillow writes multi-page PDFs on its own, so no reportlab. All images are downloaded first into `data/art/<source>/<id>.<ext>` and reused by later runs.

**`send --to notmpc`** writes the XML, opens `https://notmpc.com/custom-game-cards/` in the browser, and prints the three things the user has to do there: choose black border and 63x88 mm, upload the XML, pay. It also prints the estimated price from a small table in `printing/shops.toml` that the user maintains (the shop's own price table is JavaScript and not scrapeable). That is as far as automation goes without an API.

**`send --to mpc`** writes the XML into its own folder and, when the `mpc-autofill` desktop tool is installed (`--autofill-bin`), runs it there with `--site MakePlayingCards`. The tool opens Chrome and waits for the user to log in, then fills the order. Every Scryfall-sourced card must be a local file for this path, which the exporter already does. Lower priority than notmpc: it is the same XML, and the tool is interactive.

**`send --to printer`** runs the `pdf` export and then `lpr -P <printer> -o media=Letter -o fit-to-page=false -o print-quality=5 <pdf>`. `--printer` defaults to the CUPS default; with none set, which is the case on this Mac today, it lists the printers CUPS knows and stops. A dry run (`--preview`) opens the PDF instead.

## Agent surface

MCP tools in `server.py`, each a thin wrapper like `validate_deck`, so they work from any folder:

| Tool | Does |
|---|---|
| `choose_art(decklist, style, basics, sources?, pins?)` | Step 1. Returns the per-card choices with labels and the list of missing cards. |
| `art_gallery(decklist, serve=true)` | Step 2. Returns the URL (served) or the file path, and the port to stop. |
| `set_art(decklist, name, source, id)` | One card by hand, for "use the John Avon one for the Forests". Searches both sources for the name when `id` is omitted and returns the candidates instead. |
| `print_deck(decklist, target, options)` | Step 3. Returns the output path, the preflight report, and for shops the manual steps left. |

A new skill, `.claude/skills/print-deck/SKILL.md`, walks the agent through: confirm the decklist passes `mtg check`; run `choose_art` with the style the user asked for and read back the missing list and anything chosen below 600 dpi; open the gallery and wait for "done"; run the preflight; say the price estimate and the manual steps; hand over the XML or PDF path. The `commander-deck` skill's last step gains one line pointing here.

The conversation this spec is for:

> **User:** print the treefolk deck, full art where you can
> **Agent:** runs `choose_art`; "63 cards. 49 are community renders at 800 to 1200 dpi, 13 only exist in the plain frame, and Quickbeam has no high-resolution image yet. Opening the gallery at http://127.0.0.1:51234 so you can swap any of them. Tell me when you're done."
> **User:** done, send to notmpc
> **Agent:** preflight passes except Quickbeam; "Quickbeam is still missing. Print the deck without it and add it later, or use the low-res scan?" → writes the XML → opens notmpc → "Order is 99 cards on S33, about $34. Pick black border and 63x88 mm, upload decks/treefolk-quickbeam.xml, pay."

## Code layout

```
mtg_deck_builder/printing/
  __init__.py
  printings.py   # Scryfall printings table, scoring, choose()
  mpcfill.py     # /2/editorSearch, /2/cards, /2/sources, /2/cardbacks, Drive download, cache
  printfile.py   # read/write <name>.print.toml, --keep, --apply
  gallery.py     # HTML template, http.server, POST /choose
  bleed.py       # Pillow: bleed + corners for Scryfall PNGs
  export.py      # xml, pdf, preflight
  send.py        # notmpc, mpc, printer
  sources.toml   # default mpcfill source order
```

`cards.py` gains the `printings` table in `build_index` and a `printings_of(db, oracle_id)` query. `cli.py` gains `art`, `gallery`, `print`. `pyproject.toml` gains `pillow`. `README.md` gains a "Printing a deck" section and the data table gains `data/art/`. `.gitignore` already covers `decks/`, which is where `.print.toml`, `.xml`, `.pdf` and `cards/` land; add `/data/art/`.

## Milestones

Each one ships on its own and is checked against the real Treefolk deck, as the repo has no test suite.

1. **Spikes (half a day).** Upload a hand-written 5-card XML to notmpc with four Drive ids and one `Local File`; record what the uploader does with each. Download 100 Drive files in a row and note any throttling. Print one bleed-padded Scryfall PNG and one render through notmpc's single-card uploader to compare at the table. These settle the two open questions below.
2. **`mtg art` with Scryfall only, plus the print file.** Printings table, scoring, `--style`, `--basics`, `--keep`. Offline, so it is testable immediately.
3. **mpcfill source.** Search, metadata, source ranking, cardbacks, Drive download with cache. `mtg art` now prefers renders.
4. **Gallery.** Static page first, then `--serve` and `POST /choose`.
5. **`mtg print xml` and `send --to notmpc`**, with bleed and preflight. This is the point where the friend's flow is fully replaced.
6. **`mtg print pdf` and `send --to printer`.**
7. **MCP tools and the `print-deck` skill.** Update `commander-deck`, `CLAUDE.md` and `README.md`.
8. **Later:** `send --to mpc` through the desktop tool; tokens from mpcfill's TOKEN type; per-card foil.

## Open questions

- **Does notmpc resolve `Local File` entries, or Drive ids only?** Settled by spike 1. If Drive only, Scryfall-sourced cards go into a Drive folder of the user's (one-time OAuth, or a manual drag) or into MPC's path instead.
- **How many anonymous Drive downloads before Google throttles?** Settled by spike 1. The desktop tool uses a service-account key; we would rather not ship one.
- **Which checkout does the MCP server run from?** Today it runs from `~/Documents/Code/10-19 Projects/11 MTG-Deck-Builder`, three merges behind `main`, and the data lives there. Either re-register it against the `~/work` checkout or point `MTG_DATA_DIR` at the existing data, before milestone 2 adds a table that needs a rebuild.
- **Image terms.** mpcfill's community asks for no commercial use; Scryfall's terms forbid presenting images as counterfeits. A proxy deck for the user's own casual table is what both communities exist for. The tools should not be pointed at resale, and the README should say so in one line.
- **Rulings on proxies at the user's tables** are the user's business, not the tool's; nothing here changes `mtg check`.
