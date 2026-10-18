# Proxy printing: from a decklist to printed cards

Research done on 2026-10-17. The question: can an agent take a checked decklist from this repo, pick a nice printing of every card, and get the deck printed, without the user visiting mpcfill.com or Moxfield by hand? This is the evidence behind [`docs/spec/print-suite.md`](../spec/print-suite.md).

The flow being replaced: Moxfield list → paste into mpcfill.com and pick art per card → download the MPC Autofill XML → upload it to notmpc.com and pay.

## Summary

- **The art-picking step can be reproduced offline-first.** The repo already downloads every printing of every card (`default-cards.jsonl.gz`, 118,773 printings) with Scryfall's `full_art`, `border_color`, `frame_effects` (`showcase`, `extendedart`, `inverted`) and `promo_types` flags and the image URLs. That is enough to rank "nice full art" printings with no network call.
- **mpcfill.com has an open JSON API** that the site's own editor uses. Two POSTs (`/2/editorSearch/`, `/2/cards/`) return, for a card name, every community render with its Google Drive file id, dpi, source and a thumbnail. No key, no auth. Confirmed live today.
- **Community renders beat Scryfall scans for printing.** Renders are 800 to 1200 dpi with bleed already added; Scryfall's best image is 745x1040 px (about 300 dpi at trim size) with no bleed and transparent corners. Scryfall images need a generated bleed before any print shop accepts them.
- **Coverage is good but not complete.** For the 63 unique cards of deck A, mpcfill had a render for 49 and Scryfall had a borderless, full-art, showcase or extended-art printing for 27. Thirteen old, obscure cards exist only in a plain frame anywhere. The commander, a new card, had no printable image at all yet.
- **The XML format is documented and simple** (one `<order>`, cards with a Drive id and 0-indexed slots). The repo can write it without the mpcfill editor.
- **No print shop has an API.** notmpc.com accepts the XML through a web form only; the flow of a player who used this shop is the only confirmation that it resolves the Drive ids itself. MakePlayingCards is driven by the `mpc-autofill` desktop tool, which needs a human to log in. Home printing is a PDF plus `lpr`; this Mac has no printer configured today.
- **Image quality is uneven, and a local upscaler is practical.** Renders in deck A's pool run from 500 to 1300 dpi; Scryfall scans are 300 dpi with halftone; 6,726 printings are flagged `lowres`. `upscayl-bin`, the maintained Real-ESRGAN ncnn runner inside the Upscayl app, installs with one Homebrew cask, runs on Apple Silicon, and is already driven headlessly by other proxy pipelines. Its known weak spots are small text and halftone, so the spec runs it at 4x then downscales to 800 dpi, checks for colour shift, and shows a before/after in the gallery.

## What was checked

"Ran" means I made the request or ran the code today. "Read" means it comes from documentation or source and was not exercised.

| Claim | How |
|---|---|
| mpcfill `/2/editorSearch/` returns Drive ids for a name query, and returns nothing when `sources` is empty | Ran: POST with 3 queries and 8 sources: Cultivate 19 hits, Forest 145, "New Card" 0. The same POST with `"sources": []` returned `{"cultivate": {"CARD": []}}`. |
| mpcfill `/2/cards/` returns name, source, dpi, size, extension, tags, language, `downloadLink`, thumbnails | Ran: POST with 12 ids. Example: "Cultivate (Borderless Uichi Ukumo)", JohnPrime, 1200 dpi, 2.1 MB jpg. |
| mpcfill `/2/sources/` lists 279 sources with pk, name, description | Ran. |
| Live mpcfill is older than the GitHub repo: `/3/editorSearch/` is 404, `downloadLink` is not in the repo schema | Ran, by the research agent. |
| Anonymous Drive download works from `https://drive.google.com/uc?id=<id>&export=download` | Ran: HTTP 303 to `drive.usercontent.google.com`, then a 3288x4488 PNG (11.4 MB) for one id. |
| XML schema: `<order>` with `<details>` (quantity, stock, foil), `<fronts>`/`<backs>` of `<card>` (id, slots, name, query, optional sourceType), `<cardback>`; stocks `(S27) Smooth`, `(S30) Standard Smooth`, `(S33) Superior Smooth`, `(M31) Linen`, `(P10) Plastic`; no `<bracket>` element any more | Read: `frontend/src/features/download/downloadXML.ts`, `desktop-tool/src/order.py`, `desktop-tool/src/constants.py` at commit `ceb7c3b`, and the wiki XML page. |
| MPC order brackets are 18, 36, 55, 72, 90, 108, 126, 144, 162, 180, 198, 216, 234, 396, 504, 612; max 612 | Read: MPC's `dro_choosesize` dropdown and `frontend/src/common/constants.ts`. |
| Community print size: 63x88 mm trim plus 36 px bleed per side at 300 dpi, i.e. 816x1110 px at 300 dpi, 2176x2960 at 800, 3264x4440 at 1200; dpi estimated as `10*round(height*300/1110/10)` | Read: repo constants and real Drive files of those sizes. |
| notmpc.com template: 300 dpi, 822x1122 px with bleed, 750x1050 cut, 690x990 safe; minimum upload 447x597; S33 stock only; 63x88 mm only; max 612 per deck; US based, 1 to 2 days processing plus 3 to 5 transit | Read: notmpc product page and FAQ. |
| notmpc prints in Los Angeles; it is a real press, not a reseller of MakePlayingCards | A shipping notification from a real order named a Los Angeles facility (October 2026). Its About and FAQ copy and its S30/S33 stock codes are MakePlayingCards' own, and its FAQ says the business is registered abroad, so it looks like a US production arm of the same group or a licensee of its stock. Which one is unconfirmed. |
| notmpc accepts the MPC Autofill XML | Read: Draftsim review only (sponsored). notmpc's own pages never mention XML. A player who used this flow has done it, which is the stronger evidence. |
| notmpc pricing about $34 for a 100-card Commander deck | Read: Draftsim, 2025-11. The site's own price table is JavaScript and could not be read. Unconfirmed. |
| Scryfall `png` is 745x1040 RGBA with transparent corners | Ran: downloaded Cultivate (STA 51). |
| Scryfall `unique=prints` search lists every printing with the frame flags | Ran: 56 paper printings of Cultivate, including 3 `full_art`, 5 borderless, 1 showcase. |
| Local bulk file flag counts: `full_art` 2,470; borderless 9,199; `showcase` 3,201; `extendedart` 4,236; `inverted` 8,140; `image_status` highres_scan 111,292, lowres 6,744, placeholder 575, missing 162 | Ran, by the research agent, over the 2026-10-17 bulk file. |
| Transform and modal DFCs keep `image_uris` on `card_faces[]`, not at the root; split, adventure, flip and meld keep them at the root | Ran, by the research agent, over the bulk file. |
| Scryfall rate limits: search, named and collection 2 per second; other methods 10 per second; `*.scryfall.io` image hosts unlimited; a `User-Agent` and `Accept` header are required | Read: scryfall.com/docs/api (via web.archive.org, as the live docs sit behind a Cloudflare challenge). |
| Scryfall image rules: do not crop the copyright or artist line, do not distort or color-shift, do not watermark | Read: same page. |
| mpcfill terms: GPL code; images are under whatever licence their uploader gave; the site does not support resale or commercial use of printed cards | Read: mpcautofill.github.io/about. |
| `mpc-autofill` desktop tool is not headless: manual MPC login, interactive prompts between projects, Chrome, Edge or Brave only, and a Drive service-account key, unless every `<id>` is a local file path | Read: `desktop-tool/autofill.py`, `webdrivers.py`, `io.py`. |
| Coverage for deck A (63 unique cards): mpcfill 49, Scryfall fancy 27, neither 13, commander none | Ran: a throwaway script in the session scratchpad, against the live mpcfill API and the local bulk file. The table is below. |
| This Mac has no printer: `lpstat -p -d` says "No destinations added"; CUPS 2.3.4 is present | Ran. Home printing was then dropped from the spec at the user's request. |
| A separate private decks repo already has a print ledger: `printed/ledger.csv` (166 rows: date, order, deck, card, qty, art, drive_id, back_art, back_drive_id), the two first orders' XMLs in `printed/orders/` (100 cards each, S30, `<bracket>108`, an illustrated mpcfill cardback each, different per deck), `printed/to-print/` lists (deck A v2: 39 cards; deck B: 5) and `tools/printed.py add | diff` | Ran: read the files on `origin/main`. |
| deck A v1 → v2: 39 cards added, 33 removed, 6 fewer basics; deck B: 5 swaps | Ran: compared the lists. Matches the repo's own `to-print` files. |
| Fan-out over all 279 mpcfill sources for the 151 unique cards of both decks: the original 8 default sources covered 133, every source together 151. WillieTanner alone covered 146 (466 renders, all 800 dpi or better, all tagged borderless or full art), CompC 122 (939 renders, mostly plain frames), RustyShackleford 110 (all under 800 dpi), Chilli_Axe 109, Hathwellcrisping 107, PsilosX 82, JohnPrime 50 (all borderless). The 18 cards only other sources had were mostly the ones falling back to Scryfall scans | Ran on 2026-10-18 against `/2/editorSearch/` and `/2/cards/`. WillieTanner, CompC and Hathwellcrisping were added to the defaults. |
| Pillow and reportlab are not installed in the project's environment | Ran: `uv run python -c "import PIL"` fails. |
| The MCP server registered on this machine runs from `~/Documents/Code/10-19 Projects/11 MTG-Deck-Builder`, which is at commit `6dfd605`, three merges behind `main`; the data (`data/`) lives there too | Ran: the Claude Code MCP registration and the log of that checkout. |
| Render dpi for deck A's 682 mpcfill hits: 6 at 500 to 599, 17 at 600 to 699, 319 at 800 to 899, 340 at 1200 to 1299; the 49 default picks are all 800 or above; 583 jpg, 98 png; sizes 0.1 to 21.9 MB, median 3.2 MB | Ran: `/2/cards/` for every id the search returned. |
| No upscaler, PyTorch or MLX is installed here; the machine is an Apple M5 Max with 64 GB and Metal 4 | Ran: `which`, `python3 -c "import torch"`, `sysctl`, `system_profiler`. |
| The `upscayl` Homebrew cask exists (2.15.0, arm64, macOS 12 or later) and its engine `upscayl-bin` had a macOS release on 2025-12-07 | Ran: `brew info --cask upscayl` and the upscayl-ncnn releases API. |
| The original `realesrgan-ncnn-vulkan` macOS binary was last released 2022-04-24 (v0.2.5.0, 51.8 MB, universal x86_64 + arm64) and has an open crash report on macOS Ventura and later | Ran: the Real-ESRGAN releases API; the research agent inspected the zip with `lipo`. Read: Real-ESRGAN-ncnn-vulkan issues 48 and 13. |
| `upscayl-bin` lives at `/Applications/Upscayl.app/Contents/Resources/bin/upscayl-bin` with models in `../models`; it takes the Real-ESRGAN flags (`-i -o -m -n -s -t -f -x`) plus `-w` width and `-c` compression; bundled models are `upscayl-standard-4x`, `upscayl-lite-4x`, `high-fidelity-4x`, `remacri-4x`, `ultramix-balanced-4x`, `ultrasharp-4x`, `digital-art-4x` | Read: the Upscayl repo (`electron/utils/get-arguments.ts`, `resources/models/`) and proxdex's docs, which auto-detect that path. Not run. |
| The Real-ESRGAN runner implements `-s 2` as a 4x run plus a resize; whole-image tiling (`-t 0`) avoids seams | Read: Upscayl passes `-s` only when it differs from the model's native 4x; the Real-ESRGAN README warns about tile seams. Unconfirmed by running. |
| Real-ESRGAN models blur or mutate small text and amplify halftone dots on scans | Read: Real-ESRGAN issues 78, 456 and 320. |
| Other proxy pipelines upscale this way: proxdex runs `upscayl-bin` per card (default `digital-art-4x`, optional double pass); Proxy Scaler runs UltraSharpV2 at 4x then Lanczos-downscales to 600, 800 or 1200 dpi and notes AnimeSharp is "strong on text"; chelcomp/print-mtg-proxy-cards runs Real-ESRGAN 2x on Scryfall images and reports colour shifts; Proxyshop upscales only the art and re-renders the frame at 1200 dpi, noting most printers stop at 800 | Read: each project's README or site. |
| A Magic-specific fine-tune exists: `rullaf/RealESRGAN_MtG` on Hugging Face, BSD-3, x2, trained with halftone removal for Scryfall art crops, shipped as a `.pth` | Read: the model card. Not run. |
| Model licences: UltraSharp, Remacri and AnimeSharp are CC-BY-NC-SA; Nomos8kSC CC-BY-4.0; NMKD Siax WTFPL; Upscayl itself AGPL-3.0 | Read: openmodeldb.info and the Upscayl repo. |
| Speed of `upscayl-bin` on an M-series Mac | Not measured. The only public figure is about 40 s per card in proxdex's UI copy, hardware unstated. |

## Coverage of a real deck

Deck A (`my-deck.txt`, 63 unique names counting the commander), checked against eight mpcfill sources (MrTeferi, JohnPrime, Chilli_Axe, WarpDandy, Nelynes, SilvanMTG, Trix Are For Scoot, PsilosX) and against the local Scryfall printings, counting only English paper printings with a high-resolution scan and a black or borderless border.

| | Cards |
|---|---|
| mpcfill has at least one render | 49 of 63 |
| Scryfall has a borderless, full-art, showcase, extended-art or inverted printing | 27 of 63 |
| Only a plain-frame printing exists anywhere | 13 of 63 |
| No high-resolution image at all | 1 (the commander, a brand-new card still at placeholder quality in the 2026-10-12 data) |

Staples are rich: Sol Ring has 109 renders and 38 fancy printings; Forest has 145 renders and 118 fancy printings. Old tribal filler is poor. So the default has to degrade gracefully: best render, else best fancy printing, else the newest plain printing, and say which it chose.

## How the pieces compare

### Image sources

| | mpcfill community renders | Scryfall printings |
|---|---|---|
| Resolution | 800 to 1200 dpi, bleed included, print-ready | 745x1040 px (about 300 dpi at trim), no bleed, transparent corners |
| Coverage | Good for staples and lands; thin for obscure cards and new sets | Every printed card, including brand-new ones once scanned |
| Offline | No: two POSTs per deck (names are batched, up to 300 per call) and a Drive download per chosen image | Yes for choosing; one `*.scryfall.io` download per chosen image, no rate limit |
| Fidelity | Fan renders: alternate frames, borderless treatments, sometimes custom art | Real card scans |
| Stability | Drive ids can disappear when a source removes a file | Image URLs carry a cache-busting timestamp but re-resolve from the card id |
| Terms | No resale or commercial use | Fan Content Policy; no cropping or color-shifting; anti-counterfeit term |

Use mpcfill first, Scryfall as the fallback and as the "show me the real printings" view. Scryfall images need a bleed generated (extend the edge pixels outward 36 px and fill the transparent corners with the border colour) to reach 816x1110 before any shop accepts them.

### Print targets

| | notmpc.com | MakePlayingCards via `mpc-autofill` | Home printer |
|---|---|---|---|
| Input | MPC Autofill XML uploaded in a web form | The same XML, driven into MPC's site by a Selenium script | PDF, 3x3 cards per US Letter page |
| Automation | None. The agent writes the XML and opens the page; the user uploads and pays. | Semi: the tool needs a human to log in, then fills the order; the user pays. | Full: `lpr` to a CUPS printer. No printer is set up on this Mac today. |
| Cost | About $34 per 100 cards, S33 stock (unconfirmed, Draftsim 2025-11) | About $0.20 per card plus slow shipping from Hong Kong (2021 figure) | Paper and ink; needs cardstock and cutting |
| Quality | Good per the one review found; S33 black core | Good, variable | Lowest; about 300 dpi inkjet, hand cut |
| Time | 1 to 2 days processing, 3 to 5 in transit | Weeks | Minutes |

notmpc stays the default because it is what already works for players we know and it prints in Los Angeles, so there are no import fees and the cards arrive in about a week. MakePlayingCards is the same stock from the Hong Kong factory, with weeks of shipping and, since the US ended the small-parcel duty exemption in 2025, import fees on a small order; it is the fallback, not a cheaper equivalent. The home printer is the only target that can be fully automated, so it is worth building for test prints and single replacements; notmpc sells blank S33 sheets, which puts factory stock in a home printer.

### Upscalers

The question is which images need help and what runs on this Mac without a Python ML stack.

**Who needs it.** In deck A's pool, every default render pick is 800 dpi or better, so renders rarely need upscaling; the 23 renders under 700 dpi only matter when the user picks one by hand. The Scryfall path is the real customer: every scan is 300 dpi at trim with halftone rosettes, and the Scryfall path is what the thirteen plain-only cards and every new card take. `lowres` (6,726) and `placeholder` (575) printings are below what any model can rescue.

| | `upscayl-bin` (Upscayl) | `realesrgan-ncnn-vulkan` (original) | `spandrel` + PyTorch on Metal | chaiNNer | Apple first-party |
|---|---|---|---|---|---|
| Install | `brew install --cask upscayl` | 2022 zip from GitHub | pip, several hundred MB to GBs | DMG, heavy | nothing to install |
| Apple Silicon | Yes, via MoltenVK, maintained (Dec 2025 release) | Universal binary, but an open crash report on Ventura and later | Yes; MPS speed and operator coverage unconfirmed | Yes | `sips` resamples only; VideoToolbox super-resolution is for video frames on macOS 26 and needs a Swift wrapper |
| Headless | Yes, plain CLI; proxdex does it | Yes | Yes, with your own tiling code | Experimental CLI, documented as buggy | No |
| Models | 7 bundled ESRGAN-style 4x models; custom ncnn models drop in | 2 photo + 3 anime models | Any `.pth` or `.safetensors` from OpenModelDB, including the Magic fine-tune | Any | None |
| Verdict | Default engine | Avoid | The `command` engine for experiments and the Magic fine-tune | Prototype chains only | No |

**What other proxy pipelines do.** All four found upscale after choosing the image and before adding bleed. Two run the model at its native 4x and downscale to the print dpi with Lanczos. One upscales only the art and re-renders the frame from templates, which sidesteps the text problem at the cost of a frame renderer this repo does not have. One reports colour shifts after Real-ESRGAN, so the spec checks for them.

**Known failure modes**, all from upstream issues, none yet reproduced here: small text blurs or mutates; halftone rosettes on scans get amplified; tiling produces seams unless the whole image is processed at once. The spike in the spec exercises each on real cards before a default model is fixed.

### Things that could break

- **mpcfill's live API lags its repo.** Code against the live `/2/` endpoints, not `/3/`, and check `/2/searchEngineHealth/` before a batch.
- **Google Drive throttling** on anonymous downloads is not measured. A 100-card deck is about 100 downloads of 2 to 4 MB each. Cache downloads under `data/art/` keyed by Drive id.
- **New cards** have placeholder images on Scryfall for a few days and no community render for weeks. The gallery has to say so instead of printing a blurry card.
- **Image terms.** mpcfill asks for no commercial use; Scryfall asks that images not be cropped, color-shifted or presented as counterfeits. Printing a casual proxy deck for the table is the common use case both communities serve; selling the cards is not.
- **notmpc is a small shop** with a registered-abroad payment system and reader complaints about shipping charges and support. It prints in Los Angeles on the same stock MakePlayingCards uses, so it is a different press from the Hong Kong factory, not a front for it. Keep the XML so the same order can go to MPC instead; the trade is weeks of shipping and import fees for the same stock.
