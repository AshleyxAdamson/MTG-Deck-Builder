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

## One interface

The user has one interface: the conversation. The agent has one command: `mtg ship`. The user touches two other things only: a gallery page to swap art, and the shop's pay button.

```bash
uv run mtg ship decks/treefolk-quickbeam.txt            # art → gallery → preflight → XML → opens notmpc
uv run mtg ship decks/treefolk-quickbeam.txt --to printer
```

`mtg ship` runs the four steps below in order and stops only where a human is needed: it opens the gallery and waits for "done" (or `--no-gallery` to take the defaults), and it ends at the shop's checkout page with the order filled. The four steps stay as their own commands for repair work (swap one card, re-export) and as MCP tools for the agent; `ship` is what the `print-deck` skill calls.

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

[upscale]
engine = "upscayl"                   # upscayl | none | command
model = "ultrasharp-4x"
min_dpi = 600                        # anything below is upscaled
target_dpi = 800                     # what every image is delivered at
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

One HTML file, no build step, no framework, written from a template string in `printing/gallery.py`. One row per deck entry, grouped by role when the notes name roles, otherwise by type. Each row shows the chosen image large on the left and the alternatives as a horizontal strip of thumbnails on the right, with a caption per thumbnail (source, set or render name, artist, dpi, a "render" or "scan" badge, and a red "low res" badge when under 600 dpi). Clicking a thumbnail makes it the chosen one. Thumbnails come straight from Drive (`https://drive.google.com/thumbnail?sz=w400-h400&id=<id>`) and Scryfall (`image_normal`), so the page is light and the images are never stored before the user chooses. A filter bar at the top: style (same four as `--style`), renders only, scans only, one artist, hide Universes Beyond. A header shows the count of chosen renders, chosen scans, cards that will be upscaled, missing cards, and the estimated order size against the MPC brackets (18, 36, 55, 72, 90, 108, 126, 144, 162, 180, 198, 216, 234, 396, 504, 612).

A card that will be upscaled gets an "upscale" badge and, once the prepared image exists, a compare view: original and upscaled side by side with a zoom on the rules text, and a switch for `auto | never | always` that writes to the print file like a thumbnail click does.

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
    <card><id>cards/forest-znr-280.png</id><sourceType>Local File</sourceType><slots>62,63,...</slots><name>forest-znr-280.png</name><query>forest</query></card>
  </fronts>
  <backs>
    <card><id>cards/delver-mid-47-back.png</id><sourceType>Local File</sourceType><slots>17</slots><name>...</name><query>delver of secrets</query></card>
  </backs>
  <cardback>16g2UamJ2jzwNHovLesvsinvd6_qPkZfy</cardback>
</order>
```

Slots are 0-indexed in decklist order, copies expanded. mpcfill renders at or above `min_dpi` go in by Drive id, which is what notmpc and the mpcfill desktop tool both resolve. Scryfall images cannot go in by URL, and a render that was upscaled is no longer the Drive file, so both are written as prepared PNGs under `decks/cards/` and referenced as local files. The `<backs>` element is always written, empty when there are no double-faced cards, because the parser expects it. `--stock` overrides the print file; `--foil` is refused for `(P10) Plastic`.

Open question for a spike: whether notmpc's uploader accepts `Local File` entries, or only Drive ids. If not, the fallback is to upload the Scryfall-sourced cards to a Drive folder of the user's own, or to put them in the deck as separate single-image uploads. The spike is a 5-card XML with one Scryfall card, uploaded by hand.

**Image preparation** (`printing/prepare.py`, needs Pillow, the one new Python dependency) runs on every chosen image before it reaches an export, in this order: fill, upscale, bleed. Each output is cached under `data/art/prepared/<source>/<id>-<dpi>-<model>.png`, so a second export is instant.

1. **Fill.** Scryfall PNGs are 745x1040 RGBA with transparent rounded corners; the corners are filled with the border colour sampled at the edge midpoint, because transparent pixels confuse upscalers and print as white. Renders already have square corners.
2. **Upscale** when the image's effective dpi is below the threshold. See the next section.
3. **Bleed.** Pad 36 px per side at 300 dpi (96 px at 800) by repeating the edge row and column, then resize to the target with bleed: 816x1110 at 300 dpi, 2176x2960 at 800. That is the community standard 63x88 mm plus 1/8 inch bleed, above notmpc's 447x597 minimum and within six pixels of its 822x1122 template. Renders arrive with bleed and skip this step. Bleed comes last so the upscaler never invents detail in a region the cutter removes.

Nothing is sharpened, recoloured or cropped.

### Upscaling low-quality images (`printing/upscale.py`)

Image quality is uneven. Scryfall scans are 745x1040 (300 dpi at trim) and carry the halftone rosettes of a printed card; 6,726 Scryfall printings are flagged `lowres` and 575 `placeholder`; community renders run from 500 to 1300 dpi (in the Treefolk deck's pool of 682 renders: 6 below 600 dpi, 17 at 600 to 699, 319 at 800, 340 at 1200). The thirteen Treefolk with no fancy printing and every brand-new card come through the Scryfall path, so the cards most likely to need help are exactly the ones with no alternative.

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

**`pdf`** lays out fronts for home printing: US Letter (A4 with `--paper a4`), nine cards per page at exactly 63x88 mm trimmed (bleed removed), 2 mm gutters, hairline cut marks in the gutters and margins, page numbers, and the deck name in the footer. Backs are a second PDF, mirrored per page, written only with `--backs`. Pillow writes multi-page PDFs on its own, so no reportlab. Images go through the same preparation as the XML path, so a home print gets the upscales too; raw downloads live in `data/art/<source>/<id>.<ext>` and prepared images beside them, both reused by later runs.

**`send --to notmpc`** writes the XML, opens `https://notmpc.com/custom-game-cards/` in the browser, and prints the three things the user has to do there: choose black border and 63x88 mm, upload the XML, pay. It also prints the estimated price from a small table in `printing/shops.toml` that the user maintains (the shop's own price table is JavaScript and not scrapeable). That is as far as automation goes without an API. notmpc is the default shop: it prints in Los Angeles on the same S33 stock as MakePlayingCards, so a deck arrives in about a week with no import fees. A later step can drive the upload form itself with Playwright and stop at the pay button; the form is a fixed page, so this is brittle but small.

**`send --to mpc`** writes the XML into its own folder and, when the `mpc-autofill` desktop tool is installed (`--autofill-bin`), runs it there with `--site MakePlayingCards`. The tool opens Chrome and waits for the user to log in, then fills the order. Every Scryfall-sourced card must be a local file for this path, which the exporter already does. This is the fallback, not a cheaper equivalent: the same stock from the Hong Kong factory, with weeks of shipping and import fees on a small US order. It matters if notmpc is down or out of stock. A driver of our own, with the MPC login saved after a one-time sign-in, would remove the tool's interactive steps; that is a later milestone.

**`send --to printer`** runs the `pdf` export and then `lpr -P <printer> -o media=Letter -o fit-to-page=false -o print-quality=5 <pdf>`. `--printer` defaults to the CUPS default; with none set, which is the case on this Mac today, it lists the printers CUPS knows and stops. A dry run (`--preview`) opens the PDF instead. For paper, notmpc sells blank S33 sheets, so a home print can go on the same black-core stock the shop uses; the PDF layout takes a `--sheet` size for them once their dimensions are known.

## Agent surface

MCP tools in `server.py`, each a thin wrapper like `validate_deck`, so they work from any folder:

| Tool | Does |
|---|---|
| `choose_art(decklist, style, basics, sources?, pins?)` | Step 1. Returns the per-card choices with labels and the list of missing cards. |
| `art_gallery(decklist, serve=true)` | Step 2. Returns the URL (served) or the file path, and the port to stop. |
| `set_art(decklist, name, source, id)` | One card by hand, for "use the John Avon one for the Forests". Searches both sources for the name when `id` is omitted and returns the candidates instead. |
| `print_deck(decklist, target, options)` | Step 3. Returns the output path, the preflight report including which cards were upscaled and from what dpi, and for shops the manual steps left. |
| `prepare_images(decklist, only?)` | Runs fill, upscale and bleed ahead of time, in the background, so the gallery's compare view and the export are ready. Returns progress and the per-card result. |
| `ship_deck(decklist, to, style, gallery=true)` | The whole thing: steps 1 to 3 in order. Returns the gallery URL while it waits, then the preflight report, the output path and the remaining manual steps. The skill's normal entry point. |

A new skill, `.claude/skills/print-deck/SKILL.md`, walks the agent through: confirm the decklist passes `mtg check`; run `choose_art` with the style the user asked for and read back the missing list and anything chosen below 600 dpi; open the gallery and wait for "done"; run the preflight; say the price estimate and the manual steps; hand over the XML or PDF path. The `commander-deck` skill's last step gains one line pointing here.

The conversation this spec is for:

> **User:** print the treefolk deck, full art where you can
> **Agent:** runs `choose_art`; "63 cards. 49 are community renders at 800 to 1200 dpi, 13 only exist in the plain frame as 300 dpi scans and will be upscaled to 800, and Quickbeam has no high-resolution image yet. Opening the gallery at http://127.0.0.1:51234 so you can swap any of them; the upscales are running in the background and will show up there for comparison. Tell me when you're done."
> **User:** done, send to notmpc
> **Agent:** preflight passes except Quickbeam; "Quickbeam is still missing. Print the deck without it and add it later, or use the low-res scan?" → writes the XML → opens notmpc → "Order is 99 cards on S33, about $34. Pick black border and 63x88 mm, upload decks/treefolk-quickbeam.xml, pay."

## Code layout

```
mtg_deck_builder/printing/
  __init__.py
  printings.py   # Scryfall printings table, scoring, choose()
  mpcfill.py     # /2/editorSearch, /2/cards, /2/sources, /2/cardbacks, Drive download, cache
  printfile.py   # read/write <name>.print.toml, --keep, --apply
  gallery.py     # HTML template, http.server, POST /choose and POST /upscale
  prepare.py     # Pillow: corner fill, bleed, colour-shift check, prepared-image cache
  upscale.py     # effective dpi, engine detection (upscayl-bin, command, none), 4x run + Lanczos downscale
  export.py      # xml, pdf, preflight
  send.py        # notmpc, mpc, printer
  sources.toml   # default mpcfill source order
```

`cards.py` gains the `printings` table in `build_index` and a `printings_of(db, oracle_id)` query. `cli.py` gains `ship`, plus `art`, `gallery`, `print` and `print ... prepare` as its parts. `pyproject.toml` gains `pillow`. Upscayl is an external app, installed with `brew install --cask upscayl` and listed in the README's setup steps as optional (without it, images are resampled, not upscaled). `README.md` gains a "Printing a deck" section and the data table gains `data/art/`. `.gitignore` already covers `decks/`, which is where `.print.toml`, `.xml`, `.pdf` and `cards/` land; add `/data/art/`.

## Milestones

Each one ships on its own and is checked against the real Treefolk deck, as the repo has no test suite.

1. **Spikes (one day).** Upload a hand-written 5-card XML to notmpc with four Drive ids and one `Local File`; record what the uploader does with each. Download 100 Drive files in a row and note any throttling. Install Upscayl, time `upscayl-bin` on a 745x1040 scan on this machine, and run three models (`ultrasharp-4x`, `digital-art-4x`, `high-fidelity-4x`) plus one halftone-aware route on three test cards: a 2015-frame scan, a 2003-frame scan with visible rosettes, and a 500 dpi render. Judge the rules text and the copyright line at 800 dpi by eye and record the colour-shift numbers. Print one bleed-padded upscaled Scryfall PNG and one render through notmpc's single-card uploader to compare at the table. These settle the open questions below and fix the default model.
2. **`mtg art` with Scryfall only, plus the print file.** Printings table, scoring, `--style`, `--basics`, `--keep`. Offline, so it is testable immediately.
3. **mpcfill source.** Search, metadata, source ranking, cardbacks, Drive download with cache. `mtg art` now prefers renders.
4. **Image preparation.** Corner fill, bleed, cache, then the upscale step with engine detection, the 4x-then-Lanczos method, the colour-shift check and the Lanczos fallback. Testable on its own against the Treefolk scans.
5. **Gallery.** Static page first, then `--serve`, `POST /choose`, and the upscale compare view and switch.
6. **`mtg print xml` and `send --to notmpc`**, with preflight. This is the point where the friend's flow is fully replaced.
7. **`mtg print pdf` and `send --to printer`.**
8. **`mtg ship`, the MCP tools and the `print-deck` skill.** Update `commander-deck`, `CLAUDE.md` and `README.md`. From here the whole flow is one sentence to the agent.
9. **Later:** `send --to mpc` through the desktop tool, then our own Playwright drivers for the notmpc upload form and the MPC order flow, each stopping at the pay button; tokens from mpcfill's TOKEN type; per-card foil; a text-safe composite for upscaled cards; art-only upscaling with a re-rendered frame for cards that only exist as poor scans.

## Open questions

- **Does notmpc resolve `Local File` entries, or Drive ids only?** Settled by spike 1. If Drive only, Scryfall-sourced cards go into a Drive folder of the user's (one-time OAuth, or a manual drag) or into MPC's path instead.
- **How many anonymous Drive downloads before Google throttles?** Settled by spike 1. The desktop tool uses a service-account key; we would rather not ship one.
- **Which upscale model, and does the whole-card approach hold up on rules text?** Settled by spike 1. If text degrades at 800 dpi even after the downscale, the text-safe composite moves up from "later" into milestone 4.
- **How fast is `upscayl-bin` here?** Unmeasured. Nothing published for M-series Macs; one pipeline quotes about 40 s per card on unknown hardware. Settled by spike 1, and it decides whether upscales run in the background during the gallery or synchronously at export.
- **Which checkout does the MCP server run from?** Today it runs from `~/Documents/Code/10-19 Projects/11 MTG-Deck-Builder`, three merges behind `main`, and the data lives there. Either re-register it against the `~/work` checkout or point `MTG_DATA_DIR` at the existing data, before milestone 2 adds a table that needs a rebuild.
- **Image terms.** mpcfill's community asks for no commercial use; Scryfall's terms forbid presenting images as counterfeits. A proxy deck for the user's own casual table is what both communities exist for. The tools should not be pointed at resale, and the README should say so in one line.
- **Rulings on proxies at the user's tables** are the user's business, not the tool's; nothing here changes `mtg check`.
