---
name: print-deck
description: Get a Commander deck printed as proxies through the agent: pick nice art for every card, let the user swap any in a gallery, and send the order to notmpc.com, printing only the cards not already in the box. Use when the user wants to print, reprint, order, or "ship" a deck, or asks what still needs printing.
---

# Print a deck

The user talks, clicks in one gallery, and pays once. Everything else is the mtg-cards tools: `choose_art`, `art_gallery`, `set_art`, `print_deck`, `record_order`, `printed_diff`. In the repo the same things are `uv run mtg art | gallery | pick | print | placed | ship`.

The ledger in the decks repo (`decks/printed/ledger.csv`, order XMLs in `decks/printed/orders/`) says what has already been printed. Nothing in it is printed again unless the user asks.

## Steps

1. **Know the deck.** The decklist must pass `mtg check` (`validate_deck`). If the list has a new name for a deck that already exists in the box (`treefolk-quickbeam-v2.txt` for the printed `treefolk-quickbeam`), the ledger needs `printed_as = "treefolk-quickbeam"`. Ask once per deck whether basic lands should be spread over several arts (the default) or one.

2. **Choose art.** `choose_art(decklist, style, printed_as, basics)`. Read back: how many are already printed, how many are new (renders vs scans), which will be upscaled (300 dpi scans; fine, it takes about 10 seconds each), which only exist low-res, and which have no image yet. A card with no image is a new card Scryfall has not scanned; it waits for a later order or prints low-res if the user says so.

3. **Gallery.** `art_gallery(decklist)` returns a URL that works on the user's phone (Tailscale) or on the Mac. Give it to the user and wait for them to say they are done. Clicks save themselves. `set_art` handles a request like "use the John Avon one for the Forests": call it without an id to list candidates, then with the chosen id.

4. **Order.** `print_deck(decklist, to="notmpc")`. Read the report: the delta (to print, already have, take out of the deck), the size and tier, the upscales, and every problem. Common problems: images not on Google Drive yet (the user has to run `rclone config` once; say so plainly), a card with no image (print without it, or `allow_lowres`). Then give the user the shop steps from the report: open notmpc, choose black border and 63x88 mm, upload the XML, pay.

5. **Record.** When the user says they paid, `record_order(decklist, order_number, date)`. That appends the ledger and commits in the decks repo. Say that next time only new cards go in.

## Two decks at once

A small top-up still pays for notmpc's 18-card tier. Run steps 2 to 4 per deck and have the user put both XMLs in one cart; `mtg ship a.txt b.txt` does the first steps for several decks in one go.

## Things to know

- Renders come from mpcfill.com's community index and are already print-ready. Scryfall scans get corners filled, upscaled to 800 dpi and bleed added, then uploaded to the user's own Google Drive, because the shop fetches every image from Drive by id.
- The card back is plain black for every order; the user's cards are sleeved.
- Universes Beyond art is scored down, not hidden; it is still in the gallery.
- `print_deck(full=True)` prints the whole deck again, for a second copy.
