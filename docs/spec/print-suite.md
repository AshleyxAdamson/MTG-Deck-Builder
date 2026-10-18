# Spec: from decklist to printed deck, by talking to the agent

Status: proposal, 2026-10-17. Evidence is in [`docs/research/proxy-printing.md`](../research/proxy-printing.md).

## Goal

Today the repo stops at a checked decklist that pastes into Moxfield. From there the user does four manual steps: Moxfield, pick art on mpcfill.com, download the XML, upload it to notmpc.com. This spec adds the rest so a session goes:

> "Build deck A" → "Pick full-art printings and show me" → user clicks a few alternatives in a gallery → "Send it to notmpc" (or "print it here").

Moxfield drops out. mpcfill.com drops out as a website but stays as the image library behind the scenes. The print shop stays, because none has an API; the agent gets the user to the pay button with the order already filled.

## Non-goals

- Designing custom cards or alters. Only existing Magic cards, with existing printings or community renders.
- Running or replacing mpcfill.com. We call its public JSON API and read its XML format; we host nothing.
- Paying for the user. The final pay click on a print shop stays a human step; everything before it is automated.
- Home printing. The user has no printer and does not want one; the PDF and `lpr` targets from an earlier draft are dropped. The image preparation is shop-grade only.
- Illustrated card backs beyond matching what a deck already has.

## Decisions taken (2026-10-17, with the user)

| Question | Decision |
|---|---|
| Image source | Community renders first, Scryfall printings as fallback |
| Universes Beyond art | Scored down; shown in the gallery, chosen only when nothing else exists |
| Gallery | Served from the Mac and reachable from the phone over Tailscale, with a token |
| Checkout | Drive notmpc's form to the pay button, with a saved login so reorders are one click |
| Home printing | Out of scope |
| Basic lands | Ask per deck whether to spread copies over several arts; default is spread |
| Card back | Plain solid black for every order. The two printed decks carry illustrated backs, but everything is sleeved, so mismatch does not matter |
| Tokens | Yes, the tokens the deck makes are added to the order |
| Reprints | Only cards not yet printed go in a new order. The ledger in the decks repo (`printed/ledger.csv`, `printed/orders/*.xml`, `tools/printed.py`) is the record, and this suite reads and writes it |
| First order through the suite | The two pending to-print lists: deck A v2 (39 cards) and deck B (5 cards), as one combined order |
| Who builds | This agent, one PR per milestone (assumed) |
| Users | Just the user (assumed), so setup can assume this Mac, this notmpc account and the private decks repo |

## One interface

The user has one interface: the conversation. The agent has one command: `mtg ship`. The user touches two other things only: a gallery page to swap art, and the shop's pay button.

```bash
uv run mtg ship decks/my-deck-v2.txt --printed-as my-deck   # art → gallery → delta → XML → notmpc checkout
uv run mtg ship decks/my-deck-v2.txt --printed-as my-deck decks/other-deck.txt   # one order, two decks
```

`mtg ship` runs the steps below in order and stops only where a human is needed: it opens the gallery and waits for "done" (or `--no-gallery` to take the defaults), and it ends on notmpc's checkout page with the order filled and the user logged in. It prints only what the ledger says has not been printed. The steps stay as their own commands for repair work (swap one card, re-export) and as MCP tools for the agent; `ship` is what the `print-deck` skill calls.

## The flow

```
decks/<name>.txt ─┐
decks/printed/    ├─mtg art──▶ decks/<name>.print.toml ──mtg gallery──▶ browser (Mac or phone)
 ledger.csv       │            (one printing per card;          ▲    │ writes back
 orders/*.xml  ───┘             printed cards locked)            │    │
                                            │ ◀─────────────────────────┘
                                            ▼
                                   mtg print (delta only)
                                 ┌──────────┴──────────┐
                     decks/printed/orders/<deck>-<n>.xml   send --to notmpc (form filled, saved login, stop at pay)
                              + images                     send --to mpc    (fallback)
                                            │
                                            ▼  after "paid, order NMPC-123"
                                 printed.py add → ledger.csv
```

New commands, each also an MCP tool, each a small Python module under `mtg_deck_builder/printing/`. Everything runs from the existing `uv run mtg ...` entry point and reads the existing deck files; nothing changes for `mtg check` or the deck format.

## Step 1: choose a printing for every card (`mtg art`)

```bash
uv run mtg art decks/my-deck.txt            # writes decks/my-deck.print.toml
uv run mtg art decks/my-deck.txt --style borderless --no-renders --basics vary
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

**Basic lands.** The agent asks once per deck: `--basics vary` (the default when unanswered) spreads the copies over the top N candidates for that land, N = min(copies, 4), all in the chosen style; `--basics same` picks one art for all copies. The print file records the split per slot and the answer, so later runs do not ask again.

**Tokens.** Every card's Scryfall record lists the tokens it makes under `all_parts` (component `token`), so no text parsing is needed. Each distinct token the deck makes gets `copies = min(4, number of cards that make it)`, with its own entry in the print file (`kind = "token"`), its art from mpcfill's `TOKEN` type first and the token's own Scryfall printings second, and the same gallery row as a card. Tokens count toward the order size and go into the ledger like cards. `--no-tokens` leaves them out.

**Already printed.** `mtg art` reads the ledger first. A card the ledger has for this deck (or for `--printed-as <deck>`, the physical deck this list upgrades) is written with `printed = true`, its art set to the ledger's `drive_id` and `art`, and `chosen_by = "ledger"`. It is not re-chosen and not re-printed unless the user asks (see "Printing only what changed").

**Output: `decks/<name>.print.toml`.** This is the deck's print state, next to its `.txt`, `.rules.toml` and `.md`, so it lives in the user's decks repo and survives sessions:

```toml
# Written by `mtg art` on 2026-10-17; edited by the gallery. Re-run `mtg art --keep` to fill gaps only.
deck = "my-deck.txt"
style = "fullart"
stock = "(S33) Superior Smooth"      # notmpc only offers S33; MPC defaults to S30
foil = false

[upscale]
engine = "upscayl"                   # upscayl | none | command
model = "ultrasharp-4x"
min_dpi = 600                        # anything below is upscaled
target_dpi = 800                     # what every image is delivered at
cardback = { kind = "plain", color = "#000000" }   # generated locally as a PNG with bleed; the same file for every order
basics = "vary"                                    # the per-deck answer: vary | same
printed_as = "my-deck"                  # the physical deck this list upgrades, for the ledger
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
upscale = "auto"                                 # auto | never | always; auto means "when under min_dpi"
upscaled_from = 300                              # written by the export: this one went 300 → 800 with ultrasharp-4x
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
name = "Sol Ring"
copies = 1
printed = true                                   # in the ledger for my-deck: nothing to choose, nothing to print
source = "mpcfill"
id = "1qJS-oUivH9Eh_piF4x24gRsNskoGFvBa"
label = "Sol Ring (JP Archive).png"
chosen_by = "ledger"

[[cards]]
name = "New Card"
copies = 1
status = "missing"                               # no high-resolution image anywhere yet

[[cards]]
name = "Elemental"                               # a token the deck makes
kind = "token"
copies = 2
source = "mpcfill"
id = "1x...."
label = "Elemental token 2/2 (Showcase)"
```

Every record carries enough to rebuild the image URL without a lookup: mpcfill ids download from `https://drive.google.com/uc?id=<id>&export=download`, Scryfall ids from the `image_png` column. Once an image we prepared has been uploaded, the record also carries `drive_id`, the id in the user's own Drive that the XML uses. `mtg art --keep` re-runs only for cards without a `chosen_by = "user"` entry, so a decklist edit does not throw away clicks.

## Printing only what changed

The user has already printed both decks once, and a deck keeps changing. A new order must contain only the cards that are not already in the box.

**The ledger already exists**, in the decks repo, and this suite adopts it as is:

- `printed/ledger.csv`: one row per card per order, with `date, order, deck, card, qty, art, drive_id, back_art, back_drive_id`. 166 rows today, from the two first orders.
- `printed/orders/<deck>-<n>.xml`: the MPC Autofill XML of every order placed, archived. The two first orders are there, so the exact art of every printed card is known.
- `tools/printed.py add <xml> --deck <deck>` records an order; `printed.py diff <deck> [--printed-as <other>]` lists what still needs printing and what to pull. Cards never move between decks, so each deck is compared only with its own prints, and `--printed-as` handles a renamed list (`my-deck-v2` against the physical `my-deck`).
- `printed/to-print/*.txt`: the current pending lists, 39 cards for deck A v2 and 5 for deck B.

The suite does not copy this format; it calls into it. `printing/ledger.py` imports `tools/printed.py` from the decks folder (found next to the decklist) and uses its `read_ledger`, `read_deck`, `normalize` and the `add`/`diff` logic, so there is one definition of "printed". When the suite is stable, `printed.py` can move into this repo as `mtg printed add | diff` with the CSV and folder layout unchanged; until then the decks repo owns it.

**The delta** is `printed.py diff` applied per card name:

| Decklist vs ledger | Action |
|---|---|
| Card not in any order for this deck | Print it |
| Card in the ledger with fewer copies than the list | Print the difference |
| Card in the ledger with more copies than the list (Forest 38 → 32) | Nothing; the spares stay in the box |
| Card in the ledger but no longer in the list | Nothing to print; listed as "to pull" so the user knows what comes out |
| Card printed, still in the list, art changed in the gallery | Nothing by default. `--reprint "Name"` or `--reprint-art-changes` adds it |
| Token the deck now makes more of | Print the difference, same as a basic |

The preflight report shows all four groups: to print, already have, to pull, art changed but kept. `--full` ignores the ledger and prints the whole deck, for a second copy.

**Closing the loop.** `mtg print` writes the new order to `printed/orders/<deck>-<n>.xml` (n = one past the highest existing). After checkout the agent asks for the order number and date and runs `printed.py add` with them, which appends the rows to `ledger.csv`. For a combined order of several decks, one XML is written per deck (the shop takes them as separate uploads in one cart), so each deck's ledger rows point at its own file, which is what `printed.py add --deck` expects. The decks repo is its own git repo, so the agent commits the XML and the CSV there, never in this repo.

**Gallery.** Printed cards show a "printed" badge with the art from the ledger and are locked; clicking one offers "reprint with new art" instead of swapping silently.

**Small orders cost the same as 18 cards.** notmpc prices by deck size with 18 as the smallest tier, so a five-card top-up pays for 18. `mtg ship` takes several decklists and places them in one cart, and the report shows each deck's tier and free slots, so the user can add tokens or spare basics to fill one. Today's pending work: deck A v2 is 39 cards (55 tier, 16 free), deck B is 5 cards (18 tier, 13 free).

## Step 2: the gallery (`mtg gallery`)

```bash
uv run mtg gallery decks/my-deck.txt           # writes decks/my-deck.gallery.html and opens it
uv run mtg gallery decks/my-deck.txt --serve   # same, plus a local server so clicks save themselves
```

One HTML file, no build step, no framework, written from a template string in `printing/gallery.py`. One row per deck entry, grouped by role when the notes name roles, otherwise by type. Each row shows the chosen image large on the left and the alternatives as a horizontal strip of thumbnails on the right, with a caption per thumbnail (source, set or render name, artist, dpi, a "render" or "scan" badge, and a red "low res" badge when under 600 dpi). Clicking a thumbnail makes it the chosen one. Thumbnails come straight from Drive (`https://drive.google.com/thumbnail?sz=w400-h400&id=<id>`) and Scryfall (`image_normal`), so the page is light and the images are never stored before the user chooses. A filter bar at the top: style (same four as `--style`), renders only, scans only, one artist, hide Universes Beyond. A header shows the count of chosen renders, chosen scans, cards that will be upscaled, missing cards, and the estimated order size against the MPC brackets (18, 36, 55, 72, 90, 108, 126, 144, 162, 180, 198, 216, 234, 396, 504, 612).

A card that will be upscaled gets an "upscale" badge and, once the prepared image exists, a compare view: original and upscaled side by side with a zoom on the rules text, and a switch for `auto | never | always` that writes to the print file like a thumbnail click does.

**Getting clicks back to the file.** A `http.server` from the standard library serves the page and accepts `POST /choose {name, source, id}`, which rewrites that card's entry in the print file with `chosen_by = "user"`. The agent runs it in the background (the Mac is always on; a `tmux` session named `mtg-gallery` survives the agent's session), tells the user the URL, and reads the print file when the user says they are done. `mtg gallery --stop` ends it.

**From the phone.** The server binds to the Mac's Tailscale address when `tailscale` is up (`tailscale ip -4`; the CLI is installed here), else to the LAN address, else to localhost, and prints which. The URL carries a random token (`?t=...`) that every request must echo; without it the server answers 403. The server serves only the deck's gallery and its `POST /choose`, and it stops when the user says done or after 24 hours. The page is laid out for a phone first: one card per screen width, thumbnails in a horizontal strip, a tap to choose, a sticky "N changed" bar. `localStorage` keeps the scroll position only; choices never live only in the browser.

A static fallback is kept for when the server is gone: a "Copy choices" button puts a TOML fragment on the clipboard, which the agent applies with `mtg art --apply -`.

Basic lands get one extra control: a "spread over N arts" stepper that sets the `slots` table.

The page never crops or recolours a card image and shows the artist under every thumbnail, which keeps it inside Scryfall's image rules.

## Step 3: export and send (`mtg print`)

```bash
uv run mtg print decks/my-deck-v2.txt xml --printed-as my-deck   # decks/printed/orders/my-deck-2.xml, delta only
uv run mtg print decks/my-deck-v2.txt xml --full                            # the whole deck, ignoring the ledger
uv run mtg print decks/my-deck-v2.txt send --to notmpc
uv run mtg print decks/my-deck-v2.txt send --to mpc
uv run mtg print decks/my-deck-v2.txt placed NMPC-12345 --date 2026-10-20    # printed.py add, then commit in the decks repo
```

**Preflight** runs first for every target: the print file exists, every card in the decklist has an entry (the decklist is the source of truth; a stale print file fails with the diff), no entry is `missing`, every image resolves (HEAD on Drive and Scryfall, cached for a day), every image is prepared (filled, upscaled where needed, bleed added) and passed its colour-shift check, and the total slot count is 100 or whatever the list sums to. Problems are listed all at once, the way `mtg check` does, followed by the upscale report.

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
    <card><id>1AbC...ourDriveId</id><slots>62,63,...</slots><name>forest-znr-280-800dpi.png</name><query>forest</query></card>
  </fronts>
  <backs>
    <card><id>1DeF...ourDriveId</id><slots>17</slots><name>delver-mid-47-back-800dpi.png</name><query>delver of secrets</query></card>
  </backs>
  <cardback>1GhI...ourDriveId</cardback>
</order>
```

The cardback is a plain black PNG generated locally (solid colour, full bleed, 2176x2960), uploaded to the user's Drive once, and referenced by that id on every order. The printed decks carry illustrated backs from the first orders, which does not matter because everything is sleeved. The first orders were written by the mpcfill site with `<bracket>` and `(S30) Standard Smooth`; the exporter leaves `bracket` out, as the current format does, and writes the stock from the print file. notmpc only prints S33 regardless.

Slots are 0-indexed in decklist order, copies expanded. **Every `<id>` is a Google Drive file id.** The shop never receives an image from us: it reads the ids out of the XML and fetches each file from Drive itself, which is how the mpcfill site's XML has always worked and what the two archived orders contain. The `Local File` source type is a feature of the mpcfill desktop tool only. So:

- A community render at or above `min_dpi` goes in by its own Drive id, untouched.
- Anything we produce ourselves (a Scryfall scan with corners filled and bleed added, an upscaled render or scan, the plain back) is uploaded to a folder in the user's own Google Drive, shared as "anyone with the link can view", and goes in by the id Drive returns. See "Our own Drive folder" below.

The `<backs>` element is always written, empty when there are no double-faced cards, because the parser expects it. `--stock` overrides the print file; `--foil` is refused for `(P10) Plastic`.

**Our own Drive folder** (`printing/drive.py`). One folder, `MTG proxies/`, in the user's Google Drive, with one file per prepared image named `<source>-<id>-<dpi>.png` so a re-export finds the file it already uploaded instead of uploading again (the print file records the Drive id under `drive_id` once uploaded). Uploading goes through `rclone`, which handles Google's OAuth in a one-time `rclone config` session and needs no code of ours for tokens: `rclone copy` puts the file up, `rclone link` makes it viewable by anyone with the link and returns the id. `rclone` installs with Homebrew and is listed in the README's setup. A Drive API client of our own is the alternative if `rclone` gets in the way; the module's interface (`upload(path) -> drive_id`, `exists(name) -> drive_id | None`) hides which. The shop fetches each file anonymously, so "anyone with the link" is required; the folder holds only card images. A deck's worth of prepared images is 10 to 50 files of 2 to 6 MB, well inside a free Drive.

Spike 1 checks the two things this rests on: that notmpc fetches an id from a private person's Drive the same way it fetches a community one, and that the anonymous fetch works with "anyone with the link". The test is a 5-card XML with four community ids and one id from the user's Drive, uploaded by hand.

**Image preparation** (`printing/prepare.py`, needs Pillow, the one new Python dependency) runs on every chosen image before it reaches an export, in this order: fill, upscale, bleed. Each output is cached under `data/art/prepared/<source>/<id>-<dpi>-<model>.png`, so a second export is instant.

1. **Fill.** Scryfall PNGs are 745x1040 RGBA with transparent rounded corners; the corners are filled with the border colour sampled at the edge midpoint, because transparent pixels confuse upscalers and print as white. Renders already have square corners.
2. **Upscale** when the image's effective dpi is below the threshold. See the next section.
3. **Bleed.** Pad 36 px per side at 300 dpi (96 px at 800) by repeating the edge row and column, then resize to the target with bleed: 816x1110 at 300 dpi, 2176x2960 at 800. That is the community standard 63x88 mm plus 1/8 inch bleed, above notmpc's 447x597 minimum and within six pixels of its 822x1122 template. Renders arrive with bleed and skip this step. Bleed comes last so the upscaler never invents detail in a region the cutter removes.

Nothing is sharpened, recoloured or cropped.

### Upscaling low-quality images (`printing/upscale.py`)

Image quality is uneven. Scryfall scans are 745x1040 (300 dpi at trim) and carry the halftone rosettes of a printed card; 6,726 Scryfall printings are flagged `lowres` and 575 `placeholder`; community renders run from 500 to 1300 dpi (in deck A's pool of 682 renders: 6 below 600 dpi, 17 at 600 to 699, 319 at 800, 340 at 1200). The thirteen cards with no fancy printing and every brand-new card come through the Scryfall path, so the cards most likely to need help are exactly the ones with no alternative.

**When.** Effective dpi is `10 * round(height_px * 300 / 1110 / 10)` for an image with bleed (the mpcfill convention) and `height_px * 300 / 1040` for a trimmed Scryfall image. Anything under `min_dpi` (default 600) is upscaled to `target_dpi` (default 800, the most a card press prints at and the mpcfill desktop tool's own downscale target). Per card, `upscale = "auto" | "never" | "always"` in the print file overrides the threshold; the gallery exposes this as a switch.

**Engine.** `upscayl-bin`, the maintained fork of the Real-ESRGAN ncnn Vulkan runner that ships inside Upscayl (`brew install --cask upscayl`, then `/Applications/Upscayl.app/Contents/Resources/bin/upscayl-bin` with models in `../models`). It runs on Apple Silicon through MoltenVK, needs no Python ML stack, and is what other proxy pipelines (proxdex) already drive headlessly. The original `realesrgan-ncnn-vulkan` binary was last built in April 2022 and has an open crash report on macOS Ventura and later, so it is not the default. The engine is configured, not hard-coded: `engine = "upscayl" | "none" | "command"` with a `command` template (`{input} {output} {scale} {model}`), so a PyTorch model through `spandrel` on the Metal backend, or a future Core ML model, can drop in. With `engine = "none"` or the binary missing, the step falls back to Lanczos resampling and says so in the preflight report.

```bash
upscayl-bin -i in.png -o out.png -m /Applications/Upscayl.app/Contents/Resources/models -n ultrasharp-4x -f png -t 0
```

**Method.** Run the model at its native 4x (a 745x1040 scan becomes 2980x4160, about 1200 dpi), then Lanczos-downscale to `target_dpi`. Running native and shrinking beats asking the runner for 2x, which it implements as 4x plus a resize anyway, and the downscale takes the edge off GAN texture. Tile size 0 (whole image) avoids seams; the M5 Max's 64 GB has room. Default model `ultrasharp-4x`; `digital-art-4x` and `high-fidelity-4x` ship with Upscayl too, and the model is a print-file setting so a spike can change the default without code.

**Known weaknesses, and what the pipeline does about them.**

- *Rules text and the copyright line.* Real-ESRGAN models blur or mutate small text; the maintainer says text needs a fine-tuned model. Mitigation: the downscale to 800 dpi hides most of it, the gallery shows an upscaled card beside its original with a zoom on the text box, and `upscale = "never"` is one click. A later option is a text-safe composite: Lanczos for the text box, the model for the rest. Models blended with text training, such as 4x-AnimeSharp, are candidates for the spike.
- *Halftone.* Models amplify the rosette pattern of a scan. Mitigation candidates for the spike: a 1x descreen model run first (1x-Bendel-Halftone), or the Magic-specific fine-tune `rullaf/RealESRGAN_MtG` (BSD-3, x2, trained with halftone removal, built for Scryfall art crops; a `.pth`, so it needs conversion to ncnn or the `command` engine). The spike compares both against plain `ultrasharp-4x` on a 2003-frame scan.
- *Colour shift.* One community pipeline reports colour shifts after Real-ESRGAN. Check: the prepared image is downscaled back to the input size and compared with the original (per-channel mean difference and PSNR, both Pillow-only); a shift beyond a small tolerance fails preflight for that card with the numbers.
- *Lowres and placeholder scans.* A 4x model cannot recover a 488x680 placeholder. These stay `missing` for printing until the user says `--allow-lowres`, and the gallery marks them.

**Speed.** Unmeasured on this machine. The one public figure is about 40 s per card for one pipeline's Upscayl stage on unspecified hardware. A deck typically needs 10 to 20 upscales, so the export runs them in the background while the gallery is open and reports progress; results are cached, so re-exports do no work.

**Reporting.** Preflight lists every upscaled card as `name: 300 dpi → 800 dpi, ultrasharp-4x`, every card that fell back to Lanczos, and every colour-shift failure. The print file records `upscaled_from = 300` and `model` on the card so the gallery and later runs know.

**Licences.** Upscayl is AGPL, which is fine for calling its binary. Its bundled UltraSharp and Remacri models are CC-BY-NC-SA; the MtG fine-tune is BSD-3. Non-commercial terms match the no-resale stance already in this spec.

Raw downloads live in `data/art/<source>/<id>.<ext>` and prepared images beside them, both reused by later runs.

**`send --to notmpc`** (`printing/notmpc.py`) drives the shop's order form with Playwright and stops at the pay button. notmpc is the default shop: it prints in Los Angeles on the same S33 stock as MakePlayingCards, so a deck arrives in about a week with no import fees.

- *Saved login.* The driver uses a persistent browser profile under `data/browser/notmpc/`. The first run opens a visible window on the shop's sign-in page and waits for the user to log in; every later run reuses the session. Nothing about the account is stored anywhere but that profile, and `mtg print --forget-login notmpc` deletes it.
- *The form.* Open the custom cards product, choose black border, 63x88 mm, S33 and the quantity tier, upload the XML, wait for the page to fetch every image from Drive and place it, check that the slot count on the page matches the order and that no slot is blank (a blank one means a Drive id the shop could not fetch, which is reported by card name), add to cart, repeat for the next deck's XML, then open the checkout page in a visible window. The user pays there. If the shop ever stops fetching from a personal Drive, the fallback is the single-image uploader for our own files, one by one, driven by the same script.
- *Brittleness.* Every selector lives in one table at the top of the module with a comment naming the page element. A changed page fails fast with a screenshot in `data/browser/notmpc/last-failure.png` and the message "notmpc changed their page; the XML is at ..., upload it by hand", so the fallback is always the manual path the user already knows.
- *After paying* the agent asks for the order number and runs `placed`, which records the order in the ledger and commits in the decks repo. The price is read from the checkout page and shown before the user pays.

**`send --to mpc`** is the fallback, for when notmpc is down or out of stock: the same stock from the Hong Kong factory, with weeks of shipping and import fees on a small US order. First version: write the XML into its own folder and, when the `mpc-autofill` desktop tool is installed (`--autofill-bin`), run it there with `--site MakePlayingCards`; the tool opens Chrome and waits for the user to log in. The same XML works unchanged, since our own images are on Drive by then; the tool downloads them like any other id (it needs a Drive API key of its own for that, which its release builds carry). Later: the same Playwright driver pattern with a saved MPC login.

## Agent surface

MCP tools in `server.py`, each a thin wrapper like `validate_deck`, so they work from any folder:

| Tool | Does |
|---|---|
| `choose_art(decklist, style, basics, sources?, pins?)` | Step 1. Returns the per-card choices with labels and the list of missing cards. |
| `art_gallery(decklist, serve=true)` | Step 2. Returns the URL (served) or the file path, and the port to stop. |
| `set_art(decklist, name, source, id)` | One card by hand, for "use the John Avon one for the Forests". Searches both sources for the name when `id` is omitted and returns the candidates instead. |
| `print_deck(decklist, target, options)` | Step 3. Returns the output path, the preflight report including which cards were upscaled and from what dpi, and for shops the manual steps left. |
| `prepare_images(decklist, only?)` | Runs fill, upscale and bleed ahead of time, in the background, so the gallery's compare view and the export are ready. Returns progress and the per-card result. |
| `ship_deck(decklists, to, style, printed_as?, gallery=true)` | The whole thing: steps 1 to 3 in order, for one deck or several in one cart, delta only. Returns the gallery URL while it waits, then the preflight report (to print, already have, to pull), the XML paths and the checkout state. The skill's normal entry point. |
| `printed_diff(decklist, printed_as?)` / `record_order(decklist, order, date)` | `printed.py diff` and `printed.py add` from the decks repo, so the agent can answer "what do I still need to print" and close the loop after checkout. |

A new skill, `.claude/skills/print-deck/SKILL.md`, walks the agent through: confirm the decklist passes `mtg check`; read the ledger and say what is already printed; run `choose_art` with the style the user asked for and read back the missing list and anything chosen below 600 dpi; open the gallery and wait for "done"; run the preflight and say the tiers and free slots; drive the shop to checkout and say the price; after "paid", record the order and commit in the decks repo. The `commander-deck` skill's last step gains one line pointing here.

The conversation this spec is for:

> **User:** print deck A v2's changes and deck B's swaps, full art where you can
> **Agent:** reads the ledger, runs `choose_art` on both; "Deck A v2: 39 new cards plus 2 Elemental tokens; 60 are already printed and stay as they are; 33 come out, listed in the notes. Deck B: 5 new cards. Of the 46 new ones, 35 are community renders at 800 to 1200 dpi, 9 are 300 dpi scans that will be upscaled, and the commander (a brand-new card with no scan yet) still has no high-resolution image. Gallery is at http://100.x.y.z:51234/?t=... and works on your phone; the upscales are running and will show there for comparison. Tell me when you're done."
> **User:** done, send to notmpc
> **Agent:** preflight; "Deck A is 41 cards, the 55 tier with 14 free slots; deck B is 5, the 18 tier with 13 free. The new commander: print without it, or use the low-res scan?" → writes the two XMLs into `printed/orders/` → drives the form for each → "Checkout is open in the browser, both decks in the cart, $31.20. Pay there and give me the order number."
> **User:** paid, NMPC-12345
> **Agent:** runs `placed`, commits the XMLs and the ledger in the decks repo; "Logged. Next time only new cards go in."

## Code layout

```
mtg_deck_builder/printing/
  __init__.py
  printings.py   # Scryfall printings table, scoring, choose()
  mpcfill.py     # /2/editorSearch, /2/cards, /2/sources, /2/cardbacks, Drive download, cache
  printfile.py   # read/write <name>.print.toml, --keep, --apply
  gallery.py     # HTML template (phone first), http.server with token, Tailscale/LAN bind, POST /choose and POST /upscale
  prepare.py     # Pillow: corner fill, bleed, plain back, colour-shift check, prepared-image cache
  upscale.py     # effective dpi, engine detection (upscayl-bin, command, none), 4x run + Lanczos downscale
  ledger.py      # thin wrapper over the decks repo's tools/printed.py: diff, add, next order number
  tokens.py      # tokens a deck makes, from Scryfall all_parts
  drive.py       # the user's own Drive folder via rclone: upload prepared images, share by link, remember ids
  export.py      # xml (delta or full, one file per deck), preflight
  notmpc.py      # Playwright driver: saved login, form fill per XML, one cart, stop at checkout, failure screenshot
  send.py        # dispatch: notmpc, mpc
  sources.toml   # default mpcfill source order
```

`cards.py` gains the `printings` table and a `tokens_of` lookup in `build_index`, and a `printings_of(db, oracle_id)` query. `cli.py` gains `ship`, plus `art`, `gallery`, `print`, `print ... prepare` and `print ... placed` as its parts. `pyproject.toml` gains `pillow` and `playwright` (plus `uv run playwright install chromium` once, in the README's setup steps). Upscayl is an external app, installed with `brew install --cask upscayl` and listed in the README's setup steps as optional (without it, images are resampled, not upscaled). `rclone` (`brew install rclone`, then `rclone config` once for a Google Drive remote named `gdrive`) is required for any order that contains an image we prepared ourselves, which in practice is every order. `README.md` gains a "Printing a deck" section and the data table gains `data/art/` and `data/browser/`. `.gitignore` already covers `decks/`, which is where `.print.toml`, `printed/` and `cards/` land; add `/data/art/` and `/data/browser/`. The decks repo keeps `tools/printed.py`, `printed/ledger.csv` and `printed/orders/`; this repo only calls them.

## Milestones

Each one ships on its own and is checked against the real deck A, as the repo has no test suite.

1. **Spikes (one day).** Put one prepared PNG in the user's Drive with `rclone link`, then upload a hand-written 5-card XML to notmpc with four community Drive ids and that one; record whether the shop fetches it like the others. Download 100 Drive files in a row and note any throttling. Install Upscayl, time `upscayl-bin` on a 745x1040 scan on this machine, and run three models (`ultrasharp-4x`, `digital-art-4x`, `high-fidelity-4x`) plus one halftone-aware route on three test cards: a 2015-frame scan, a 2003-frame scan with visible rosettes, and a 500 dpi render. Judge the rules text and the copyright line at 800 dpi by eye and record the colour-shift numbers. Print one bleed-padded upscaled Scryfall PNG and one render through notmpc's single-card uploader to compare at the table. These settle the open questions below and fix the default model.
2. **`mtg art` with Scryfall only, plus the print file and the ledger.** Printings table, scoring, `--style`, `--basics`, `--keep`, tokens from `all_parts`, and the ledger wrapper that locks printed cards and computes the delta. Offline, so it is testable immediately: the delta for `my-deck-v2 --printed-as my-deck` must match `printed/to-print/my-deck-v2.txt` (39 cards) and deck B must give 5.
3. **mpcfill source.** Search, metadata, source ranking, token renders, Drive download with cache. `mtg art` now prefers renders.
4. **Image preparation.** Corner fill, bleed, the plain back, cache, then the upscale step with engine detection, the 4x-then-Lanczos method, the colour-shift check and the Lanczos fallback. Testable on its own against deck A's scans.
5. **Gallery.** Served page with token, Tailscale or LAN bind, phone layout, `POST /choose`, printed-card lock, the upscale compare view and switch.
6. **`mtg print xml` and `placed`** with preflight, the Drive upload of prepared images, and the delta report, one XML per deck into `printed/orders/`. The XML is uploadable by hand from here, so the flow of a player who used this shop is replaced at this point and the ledger stays current.
7. **`send --to notmpc`.** The Playwright driver: saved login, form fill per XML, one cart, checkout, failure screenshot.
8. **`mtg ship`, the MCP tools and the `print-deck` skill.** Update `commander-deck`, `CLAUDE.md` and `README.md`. From here the whole flow is one sentence to the agent.
9. **Later:** `send --to mpc` through the desktop tool, then a Playwright driver for MPC; moving `printed.py` into this repo as `mtg printed`; per-card foil; a text-safe composite for upscaled cards; art-only upscaling with a re-rendered frame for cards that only exist as poor scans.

## Open questions

- **Does notmpc fetch from a personal Drive the same way it fetches from the community drives?** It resolves Drive ids only, so our own images must live on Drive. Settled by spike 1. If a personal Drive is refused, the fallback is the shop's single-image uploader driven by the same Playwright script, or the MPC path.
- **How many anonymous Drive downloads before Google throttles?** Settled by spike 1. The desktop tool uses a service-account key; we would rather not ship one.
- **Which upscale model, and does the whole-card approach hold up on rules text?** Settled by spike 1. If text degrades at 800 dpi even after the downscale, the text-safe composite moves up from "later" into milestone 4.
- **How fast is `upscayl-bin` here?** Unmeasured. Nothing published for M-series Macs; one pipeline quotes about 40 s per card on unknown hardware. Settled by spike 1, and it decides whether upscales run in the background during the gallery or synchronously at export.
- **Which checkout does the MCP server run from?** Today it runs from `~/Documents/Code/10-19 Projects/11 MTG-Deck-Builder`, three merges behind `main`, and the data lives there. Either re-register it against the `~/work` checkout or point `MTG_DATA_DIR` at the existing data, before milestone 2 adds a table that needs a rebuild.
- **Image terms.** mpcfill's community asks for no commercial use; Scryfall's terms forbid presenting images as counterfeits. A proxy deck for one's own casual table is what both communities exist for. The tools should not be pointed at resale, and the README should say so in one line.
- **Rulings on proxies at a player's own table** are the players' business, not the tool's; nothing here changes `mtg check`.
- **Does notmpc's site tolerate a scripted browser?** Playwright with a persistent profile looks like a normal Chrome to WooCommerce, and the user is logged in as themselves. If the shop adds a bot check, the driver stops at the form and the manual upload remains. Confirmed only by trying, in spike 1.
- **Assumed, not yet confirmed:** this agent builds it, and it is for the user alone.
