# Combo detection for `mtg check`

Research done on 2026-10-12. The question: how can the deck checker tell that a decklist contains a combo, especially an infinite one, without going online at check time?

## Summary

- **Offline detection works.** Commander Spellbook publishes every combo it knows in one file (29 MB gzipped, 114,463 combos). A 100-card deck is matched against all of them in under 40 ms from a SQLite index.
- **It matched the live service exactly.** On the four requested cases plus one extra, the offline prototype returned the same "included" and "one card away" combos as Commander Spellbook's own `find-my-combos` endpoint.
- **The live endpoint had a blind spot of its own.** It silently ignores names it cannot resolve, and it did not resolve the front-face names of the deck's five double-faced cards. Matching by Scryfall Oracle ID, as the offline index does, avoids this.
- **The data is free to download for this use.** The API documentation asks tools to take the bulk file and read it locally, and asks for credit and a link back. No formal data licence is published.
- **Main limitation:** it only finds combos an editor has entered. A deck with no hits has no *known* combos, which is not proof that it has none.

Results on the test cases:

| Case | Combos in the deck (offline) | Live endpoint | Verdict |
|---|---|---|---|
| Elenda draft as it is | 0 | 0 | Clean. 17 combos are one card away. |
| + Sanguine Bond + Exquisite Blood | 2 infinite | same 2 | Correct, and it found a second loop (Vito + Exquisite Blood). |
| + Dusk Legion Sergeant | 0 | 0 | Correct. The suspected loop is not a loop (see below). |
| + Bloodthirsty Conqueror | 1 infinite | same 1 | Correct (Vito + Bloodthirsty Conqueror). |
| + Cathars' Crusade + Puppeteer Clique (extra) | 1 infinite | same 1 | Correct. Needs template matching to confirm offline. |

No false positives and nothing missed in any case.

## How this was checked

"Ran" means I made the request or ran the code today. "Read" means it comes from documentation or source code and was not exercised.

| Claim | How |
|---|---|
| Bulk file URL, size, headers, 304 on a matching ETag | Ran |
| File contents: counts, fields, shapes | Ran (parsed the whole file) |
| `find-my-combos` and `estimate-bracket` request and response | Ran (9 and 6 requests) |
| Matching rules of the live endpoint | Read (backend source), then confirmed by set equality with my own matcher |
| Rate limit of 80 requests per minute | Read (API docs). No rate-limit headers came back and I never hit a 429. |
| Bulk file rebuilt every two hours | Read (production job config). I saw one build, stamped 19:13 UTC. |
| Licence | Read (GitHub licence API, site About and Privacy pages, API docs) |
| API accepts Oracle IDs in place of names in a decklist | Read (source). Not run. |

## Sources of combo data

### Commander Spellbook

Community-run combo database at <https://commanderspellbook.com>. Its About page says it also powers EDHREC's combo feature. Backend source: <https://github.com/SpaceCowMedia/commander-spellbook-backend>.

#### Bulk export

| | |
|---|---|
| URL | `https://json.commanderspellbook.com/variants.json.gz` |
| Uncompressed twin | `https://json.commanderspellbook.com/variants.json` (687 MB, do not use) |
| Size | 29,270,348 bytes gzipped, 687,251,983 bytes of JSON |
| Format | One JSON object: `{"timestamp", "version", "variants": [...], "aliases": [...]}` |
| Contents | 114,463 variants (all with status `OK`), 5,879 aliases (old ids that redirect or were removed) |
| Refresh | Every two hours according to the production cron (`0 */2 * * *`) |
| Version stamp | HTTP `ETag` and `Last-Modified`; the document's own `timestamp` |

Response headers today:

```
content-type: application/json
content-length: 29270348
content-encoding: gzip
last-modified: Mon, 12 Oct 2026 19:13:41 GMT
etag: "0dcb0c8d136e9c39963b7c94cd630132"
```

Three things the fetch script needs to know:

1. The server labels the body `Content-Encoding: gzip`. Python's `urllib` does not decode that, so what lands on disk is the gzip file (checked: the first bytes are `1f 8b`). A client that decodes automatically, such as `requests` or `curl --compressed`, would write 687 MB instead.
2. The ETag equalled the MD5 of the downloaded file. A request with `If-None-Match: "<etag>"` returned `304` with no body. That gives a one-request "is my copy current" test.
3. The JSON is one long line, not JSONL. Loading it whole would need a few GB of memory. The prototype streams it with `json.JSONDecoder.raw_decode` over 1 MB chunks: 3.8 s to read all variants, constant memory.

#### API

Base URL `https://backend.commanderspellbook.com/`. OpenAPI schema at `/schema/?format=json` (version 7.1.9). No authentication is needed for reads. The docs ask for:

- sparse requests, "a few HTTP calls per user interaction";
- a `User-Agent` naming the tool;
- handling of `429`; "80 requests per minute should be a safe rate";
- no exporting of the dataset through the API (use the bulk file);
- credit and a link back to commanderspellbook.com.

**`POST /find-my-combos`** takes a decklist and returns the combos it contains.

Request (JSON; a plain-text decklist with `Content-Type: text/plain` is also accepted):

```json
{
  "commanders": [{"card": "Elenda, the Dusk Rose", "quantity": 1}],
  "main": [{"card": "Sol Ring", "quantity": 1}, {"card": "Swamp", "quantity": 11}]
}
```

Limits from the schema: 600 main entries, 12 commanders, names up to 256 characters. Query parameters `limit` and `offset` page the result (the view caps a page at 1,000 variants); `q` filters with the site's search syntax.

Response (trimmed; card image URLs removed):

```json
{
  "count": null, "next": null, "previous": null,
  "results": {
    "identity": "WB",
    "included": [],
    "includedByChangingCommanders": [],
    "almostIncluded": [
      {
        "id": "314-3966",
        "status": "OK",
        "uses": [
          {"card": {"id": 314, "name": "Vito, Thorn of the Dusk Rose",
                    "oracleId": "7336a541-3ae9-4ab2-acb8-f574c0a5b3a9", "typeLine": "Legendary Creature — Vampire Cleric"},
           "quantity": 1, "zoneLocations": ["B"], "mustBeCommander": false},
          {"card": {"id": 3966, "name": "Exquisite Blood",
                    "oracleId": "8f933fae-6c0c-42d7-a817-14760d8285cd", "typeLine": "Enchantment"},
           "quantity": 1, "zoneLocations": ["B"], "mustBeCommander": false}
        ],
        "requires": [],
        "produces": [
          {"feature": {"id": 14, "name": "Infinite lifegain triggers", "status": "C", "uncountable": true}, "quantity": 1},
          {"feature": {"id": 26, "name": "Infinite lifeloss", "status": "S", "uncountable": true}, "quantity": 1},
          {"feature": {"id": 15, "name": "Infinite lifegain", "status": "S", "uncountable": true}, "quantity": 1}
        ],
        "identity": "B",
        "manaNeeded": "", "manaValueNeeded": 0,
        "easyPrerequisites": "",
        "notablePrerequisites": "You have a way to gain life.",
        "description": "Gain life.\nVito triggers, causing an opponent to lose 1 life.\nExquisite Blood triggers, causing you to gain 1 life.\nRepeat from step 2.",
        "popularity": 125184,
        "bracketTag": "S",
        "legalities": {"commander": true, "...": "..."},
        "variantCount": 24
      }
    ],
    "almostIncludedByAddingColors": [],
    "almostIncludedByChangingCommanders": [],
    "almostIncludedByAddingColorsAndChangingCommanders": []
  }
}
```

Each request took 1.0 to 1.9 s.

**`POST /estimate-bracket`** takes the same body and returns `bracketTag` for the whole deck, every card with `banned`, `gameChanger`, `massLandDenial` and `extraTurn` flags, and each included combo with `relevant`, `borderlineRelevant`, `definitelyTwoCard`, `arguablyTwoCard`, `speed` and lock/extra-turn flags.

Other endpoints used: `GET /variants/<id>/` (one combo), `GET /cards/?matchedBy=<template id>` (cards that satisfy a template, 100 per page), `GET /templates/?matches=<oracle id>&matches=...` (templates a set of cards satisfies).

#### How a combo is represented

Commander Spellbook calls each concrete combo a **variant**. Field by field:

| Field | Meaning |
|---|---|
| `id` | Its own id, built from its card numbers, for example `314-6191`. Template ids follow a double dash: `2292-2744--5`. Public page: `https://commanderspellbook.com/combo/<id>/`. |
| `uses[]` | The named cards. Each has Spellbook's card number, `name`, and `oracleId` (Scryfall Oracle ID), plus `quantity`, `zoneLocations` (H hand, B battlefield, C command zone, G graveyard, L library, E exile) and `mustBeCommander`. |
| `requires[]` | Templates: a slot any matching card can fill. Each has `id`, `name` ("Persist Creature") and usually a `scryfallQuery` (`keyword:persist t:creature`). |
| `produces[]` | Results ("features"), such as `Infinite colored mana` or `Win the game`. Each has a `status`: `S` standalone payoff, `C` contextual, `H` helper. |
| `identity` | Colour identity of the whole combo, for example `WB`. |
| `manaNeeded`, `manaValueNeeded` | Mana the combo needs available. |
| `easyPrerequisites`, `notablePrerequisites` | Free-text conditions ("You have a way to gain life."). |
| `description` | The steps, one per line. |
| `legalities` | Booleans per format, including `commander`. |
| `popularity` | Number of EDHREC decks containing the combo (the backend imports it from EDHREC). |
| `bracketTag` | Spellbook's own bracket estimate for the combo taken alone. |

Facts from parsing the file:

- 7,472 distinct cards appear in combos. Every one has an `oracleId`, and every one of those ids is in this repo's card index with an identical name. Joining on `oracle_id` needs no name matching.
- Cards per combo: 2 cards in 5,275, 3 in 51,531, 4 in 48,755, 5 or more in 8,895, 1 in 7.
- **Templates are rare.** 108,095 combos (94.4%) name every card. Only 6,368 need a template, and 177 templates are in use. There is no "any sacrifice outlet" template in the published data: the generator expands such slots into one variant per card, which is why Ashnod's Altar alone is in 6,151 variants.
- 1,236 combos have a card that must be the commander. One card entry in the whole file has a quantity above 1.
- 1,525 combos are not Commander-legal (they need a banned card).

Bracket tags, with the bracket number the backend maps each to:

| Tag | Name | Bracket | Variants |
|---|---|---|---|
| `R` | Ruthless | 4 | 6,526 |
| `S` | Spicy | 3 | 11,406 |
| `P` | Powerful | 3 | 2,541 |
| `O` | Oddball | 2 | 3,517 |
| `C` | Core | 2 | 261 |
| `E` | Exhibition | 1 | 88,687 |
| `B` | Banned | none | 1,525 |

The tag comes from a formula in the backend (`estimate_bracket` in `spellbook/models/variant.py`): how many cards the combo really needs, how little mana it needs ("speed"), and whether any result is a standalone payoff. A two-card combo that needs four mana or less and has a standalone payoff is Ruthless. Free-text notable prerequisites count as an extra "arguable" card, which is why Sanguine Bond + Exquisite Blood ("You have a way to gain life.") is Spicy and not Ruthless.

#### How it reports combos a deck almost has

The live endpoint returns every combo the deck is **at most one card or one template short of**, sorted into six lists:

| List | Meaning |
|---|---|
| `included` | Nothing missing. |
| `includedByChangingCommanders` | Nothing missing, but a card that must be the commander is in the 99. |
| `almostIncluded` | One piece missing, and the combo fits the deck's colour identity. |
| `almostIncludedByAddingColors` | One piece missing, and the missing piece is outside the deck's colours. |
| `almostIncludedByChangingCommanders`, `almostIncludedByAddingColorsAndChangingCommanders` | The same two, where the commander would also have to change. |

It does not say which piece is missing; the caller works that out from `uses` and `requires`.

#### Licence and terms

- **Code:** MIT (GitHub's licence API for the backend repository; the About page says the same of site and backend).
- **Data:** no licence is stated anywhere I looked (About page, Privacy Policy, API docs, schema). The Privacy Policy says: "Commander Spellbook is unofficial Fan Content permitted under the Fan Content Policy." Card text and names belong to Wizards of the Coast.
- **Permission in practice:** the API documentation tells tools to download the bulk file and use it locally: "Fetch it on a schedule of your own and read it locally." It asks: "Please credit us, and link back to https://commanderspellbook.com where applicable."

For a personal, non-commercial tool that keeps the file in a gitignored `data/` folder, this is plainly the intended use. Two things to do: credit Commander Spellbook in the README and in the check output that lists combos, and link each reported combo to its page. Do not commit or republish the file. This is my reading of published text, not legal advice.

### EDHREC

EDHREC shows combo pages such as <https://edhrec.com/combos/orzhov>. The JSON behind them exists (`https://json.edhrec.com/pages/combos/orzhov.json` returned 200 with 100 combos; `.../wb.json` returned 403). It is not usable as the source, for three reasons:

- It is Commander Spellbook's data. The entries carry Spellbook combo ids (`"comboId": "2018-2292--73"`) with EDHREC's deck counts added.
- It is the top 100 per colour identity, not the full set.
- It is undocumented, with no stated terms for reuse.

The one thing EDHREC adds, deck counts, is already in the Spellbook file as `popularity`. The repo's `commander_ideas` tool already reads EDHREC's "known combos" panel for a commander; that stays useful as a hint and is the same underlying data.

### Others

Scryfall has no combo data (taken from the task brief, not re-checked here). I found no other maintained, downloadable combo database.

## Offline versus online

### Offline is feasible

The prototype loads the bulk file into SQLite and matches a deck with one indexed query:

```sql
SELECT c.id, c.card_count - SUM(MIN(cc.quantity, deck.quantity)) AS missing_cards
FROM combo_cards cc
JOIN deck USING (oracle_id)          -- temp table: the deck's oracle ids and quantities
JOIN combos c ON c.id = cc.combo_id
GROUP BY c.id
HAVING missing_cards <= 1;
```

`combo_cards` is indexed by `oracle_id`, so the query only touches combos that share a card with the deck.

| Measure | Value |
|---|---|
| Combos | 114,463 |
| Combo-card rows | 404,725 |
| Build the index from the gzip | 5.8 s |
| Match a 100-card deck (82 distinct cards) | 36 to 39 ms |
| Index size, prototype schema | 171 MB |
| Index size, lean schema with step text | 96 MB |
| Index size, lean schema without step text | 40 MB |

The lean schema uses integer combo keys and `WITHOUT ROWID` tables. Half of what remains is the step-by-step `description` text (50 MB).

### What offline loses: templates

The bulk file gives a template's name and its Scryfall query, but not the list of cards that satisfy it. The live service keeps that list in its database and uses it when matching. So for the 5.6% of combos with a template, an offline checker has to decide for itself whether the deck holds a matching card.

Three ways to handle it, all tried:

**1. Do not resolve templates.** A combo whose named cards are all in the deck but which needs a template is reported as "unverified: also needs a Persist Creature". Nothing is missed and nothing is wrongly failed. The cost is noise in the one-card-away list: for the draft deck it grew from 17 real entries to 33, and the off-colour list from 11 to 84, because combos that are really two pieces away look like one.

**2. Evaluate the Scryfall query locally** against this repo's card index, for the deck's cards only. The prototype (`template_eval.py`, about 250 lines) handles type, keyword, mana value, mana cost, power, toughness, colour, oracle tags (`otag:`, from the tag file this repo already downloads), exact names, plain rules-text matches and `and`/`or`/`-`. It answers yes, no or "cannot tell", and never guesses.

- 136 of 177 templates resolve over the whole card index; 146 resolve for this deck's 86 cards. Evaluating a deck takes about 0.25 s including start-up.
- Checked against the live service: Persist Creature 24 of 24 cards, "Artifact Castable for {0} that survives" 59 of 59, "Vampire with MV <= 1" 31 of 31. "Creature Castable for One Colored Mana" gave 1,202 locally against 1,208 live (I only compared the first 100, all of which matched).
- For the deck's own cards, 22 of 23 locally resolved templates agreed with the live service. The one disagreement was a false positive on a two-faced card: Scheming Silvertongue // Sign in Blood matched "Instant or Sorcery that costs {B}{B} or less" because the prototype mixed one face's cost with the other face's type.
- Not resolved: 24 templates that have no query (an editor keeps a hand-written card list, for example "Haste Enabler": 16 cards), and 17 that use rules-text patterns the prototype will not guess at (`~` for the card's own name, Scryfall-only regex shortcuts, card layout).

With this, the offline result equalled the live result in all five cases, including every one-card-away list.

**3. Download the card list per template from the API** (`/cards/?matchedBy=<id>`). It works, but pages hold 100 cards of about 2 KB each and some templates match over a thousand cards. Doing it for all 177 templates would be several hundred requests, which is what the API docs ask tools not to do. It is reasonable only for the 24 hand-written lists, which are short.

### What else differs

- **Names.** The live endpoint drops any name it cannot resolve and says nothing. Sent the deck file's names, it resolved 77 of 82 cards. The five it dropped were the double-faced cards written by front face: Scheming Silvertongue, Edgar, Charmed Groom, Bloodline Keeper, Henrika Domnathi, Legion's Landing. Three one-card-away combos using Bloodline Keeper went missing as a result (two in colours, one off colour). Sending full names (`Bloodline Keeper // Lord of Lineage`) fixed it. The offline index joins on Oracle ID, which this repo already resolves from either face name.
- **Freshness.** The live service is at most two hours behind its editors. Offline is as old as the last `mtg update`.
- **Bracket estimate for the whole deck.** Only `estimate-bracket` gives this directly. The per-combo `bracketTag` is in the bulk file. The whole-deck formula is short and could be ported, but that is a separate feature.
- **Privacy and speed.** Offline sends nothing and answers in milliseconds; live takes a second or two and sends the decklist.

The live API is not required. It is useful as an optional cross-check.

## Test results

Deck: `decks/vampire-plague-elenda.txt`, commander Elenda, the Dusk Rose. Offline runs used the bulk file stamped `2026-10-12T19:13:28Z` with local template evaluation. Live runs sent full card names.

### 1. The draft as it is

| | Offline | Live |
|---|---|---|
| Included | 0 | 0 |
| One away, in colours | 17 | 17 (same ids) |
| One away, other colours | 11 | 11 (same ids) |

Live `estimate-bracket`: `E` (Exhibition, bracket 1), no combos, no flagged cards.

The builder's belief holds: the database knows no combo in this list. The 17 in-colour near misses, by popularity:

| Missing card | Completes with | Infinite |
|---|---|---|
| Exquisite Blood | Vito, Thorn of the Dusk Rose | yes |
| Bloodthirsty Conqueror | Vito | yes |
| Beacon of Immortality | Vito | near-infinite |
| Abdel Adrian, Gorion's Ward | Animate Dead | yes |
| Blood Tribute | Vito | yes (kills one opponent) |
| Revival // Revenge | Vito | near-infinite |
| Leonin Relic-Warder | Animate Dead | yes |
| Shard of the Nightbringer | Vito | yes (kills one opponent) |
| Tombstone Stairwell | Blood Artist; also Falkenrath Noble | near-infinite |
| Serra Avatar; Soul of Eternity | Swords to Plowshares + Vito | near-infinite |
| Enduring Angel | Vito | near-infinite |
| Archon of Falling Stars | Animate Dead + Viscera Seer | yes |
| Spawnsire of Ulamog | Kaya, Geist Hunter | yes |
| Thornbite Staff | Bloodline Keeper + Viscera Seer; also + Bloodthrone Vampire | yes |

Vito and Animate Dead are the two cards to watch when changing this deck.

### 2. Plus Sanguine Bond and Exquisite Blood

Offline and live both return two included combos:

| Id | Cards | Produces | Tag |
|---|---|---|---|
| `690-3966` | Sanguine Bond + Exquisite Blood | Infinite lifegain, infinite lifeloss | S |
| `314-3966` | Vito, Thorn of the Dusk Rose + Exquisite Blood | Infinite lifegain, infinite lifeloss | S |

Both list the prerequisite "You have a way to gain life." The deck is full of lifelink, so neither is a false positive. The second one matters: the brief's `not_together` rule names only Sanguine Bond + Exquisite Blood, and Exquisite Blood alone already goes infinite with Vito, which is in the draft. One away: 32 in colours and 14 off colour, the same ids both ways. Live bracket estimate for the deck: `S`.

### 3. Plus Dusk Legion Sergeant

Offline and live both return nothing included, and the same near misses as case 1.

The database has exactly one combo using Dusk Legion Sergeant: `1404-2506-4050-6925`, Molten Echoes + Cordial Vampire + Phyrexian Altar + Dusk Legion Sergeant. It needs a red card and is four cards, so it appears in no list for this deck.

The suspected loop (Sergeant + Cordial Vampire + Viscera Seer) is not in the database, and by my reading of the rules that is right:

- Sergeant's ability gives persist "until end of turn" to the nontoken Vampires you control when it resolves.
- Sergeant's own ruling (2023-11-10) says: "Once persist returns the creature, it's considered a new object with no relation to the object that it was."
- So a Vampire that dies and comes back no longer has the granted persist. Cordial Vampire's counter cancels the -1/-1 counter, but there is no persist left to trigger again. Each Vampire comes back once.

The one database combo confirms the mechanism: it loops only because Molten Echoes makes a fresh token Sergeant each cycle, which grants persist again.

So this case is a correct "no", not a miss. It also shows the limit of the approach: the checker can say a suspected loop is not a known combo, but the reasoning about why had to come from the rules.

### 4. Plus Bloodthirsty Conqueror

Offline and live both return one included combo:

| Id | Cards | Produces | Tag |
|---|---|---|---|
| `314-6191` | Vito, Thorn of the Dusk Rose + Bloodthirsty Conqueror | Infinite lifegain, infinite lifeloss | S |

Same prerequisite ("You have a way to gain life."), met by the deck. The suspicion was right. One away: 26 and 14, the same ids both ways. Live bracket estimate: `S`.

### 5. Extra: a combo that depends on a template

Added Cathars' Crusade and Puppeteer Clique (a black creature with persist) to exercise templates.

| | Offline, templates evaluated | Offline, templates not evaluated | Live |
|---|---|---|---|
| Included | 1 | 0, plus 1 "unverified" | 1 |
| One away, in colours | 42 | 46 | 42 |
| One away, other colours | 78 | 93 | 78 |

The combo is `2292-2744--5`, Viscera Seer + Cathars' Crusade + any Persist Creature: infinite death triggers. Its tag is `E` (Exhibition) and `estimate-bracket` marks it `relevant: false`, because none of its results is a standalone payoff. In this deck, infinite death triggers with Blood Artist on the table win the game. **A rule against infinite combos must not rely on the bracket tag.**

### Live with the deck file's names as written

For comparison, the first live runs sent the names exactly as the deck file has them. Included combos were the same in all four cases, but the one-away lists were short (15 and 10 for case 1 instead of 17 and 11) because five double-faced cards were dropped, as described above.

## Infinite versus not infinite

The database holds combos only. It is not a list of synergies: 97.3% of variants produce something infinite or near-infinite, and the rest win, lock or wipe on the spot.

| Class | Test on `produces[].feature.name` | Variants | Examples |
|---|---|---|---|
| Infinite | A name contains "infinite" and not "near-infinite" | 107,429 | Infinite lifeloss; Infinite creature tokens; Infinite death triggers |
| Near-infinite only | A name contains "near-infinite", none is infinite | 3,915 | Vito + Beacon of Immortality; Tombstone Stairwell + Blood Artist |
| Neither | No name contains "infinite" | 3,119 | Thassa's Oracle + Demonic Consultation ("Win the game"); locks; mass land denial |

There is no boolean "infinite" field. The feature name is the only signal, and it is consistent: 503 feature names say "Infinite", 161 say "Near-infinite", 437 say neither.

What a "no infinite combos" rule should key on:

- **Use:** any produced feature whose name contains "infinite" and not "near-infinite", whatever its status. Helper results such as "Infinite death triggers" count, because a deck built around death triggers turns them into a win.
- **Do not use `bracketTag`.** 84,408 infinite combos are tagged `E`. The tag measures how fast and compact a combo is, not whether it loops.
- **Do not use feature `status` to exclude.** Same reason.
- **Report near-infinite and "neither" separately.** They are not infinite by the letter of the brief, but a casual table would want to know about a two-card instant win. Thassa's Oracle + Demonic Consultation is "neither".

One wrinkle: "infinite" in a feature name is editorial. Vito + Blood Tribute produces "Infinite lifeloss for target opponent" though it is a one-shot kill. Erring that way suits this rule.

For the Commander Brackets question about two-card infinite combos, the bulk file has what is needed: count the cards in `uses` plus templates in `requires` (4,032 combos have exactly two cards and no template, 2,940 of them infinite), and read `manaValueNeeded` for "early". The `bracketTag` already folds these together and can be shown as extra information.

## Recommended design

> This section is the proposal as researched. The implementation in `mtg_deck_builder/combos.py` differs in places: the combo index is a separate file that is not attached to the card index, the third combo kind is called `finite` (not "other"), combos needing a banned card are left out, and template combos are reported as unverified without an evaluator.

### Fetch: `scripts/fetch_data.py`

Add a group `combos`:

| | |
|---|---|
| Source | `https://json.commanderspellbook.com/variants.json.gz` |
| Destination | `data/spellbook/variants.json.gz` (kept gzipped, like the Scryfall files) |
| Manifest key | `spellbook/variants.json.gz` |
| Version | The response `ETag` |
| Extra manifest fields | `records` (variant count), `built_at` (the document's `timestamp`), `spellbook_version` |

Steps:

1. If the manifest entry is under 24 hours old and `--force` is not set, print `current` and stop. The file is rebuilt every two hours, so comparing versions alone would download 29 MB on every run.
2. Otherwise send `GET` with `If-None-Match: <stored etag>`. On `304`, refresh `fetched_at` and stop.
3. On `200`, stream to `variants.json.gz.part`, read it through once to count variants (this proves the gzip and the JSON are whole), then `os.replace` it over the old file and record the manifest entry.

Details: send the existing `User-Agent` and `Accept: application/json`. Do not send `Accept-Encoding` and do not decompress the body. `open_url` needs a way to pass the extra `If-None-Match` header, and `urllib` raises `HTTPError` for a `304`, so the combos function has to catch it. No throttle is needed for one request. The streaming reader in the prototype (`spellbook_stream.py`, 50 lines, standard library) can be reused as it is.

Add a README line crediting Commander Spellbook with a link.

### Index

Keep combos in their own file, `data/combos.sqlite`, built from `data/spellbook/variants.json.gz` with its own source stamp (schema version, file size, mtime), the same way `cards.sqlite` is built. Reasons: the combo file and the Scryfall files change on different schedules, so neither rebuild should force the other; and the combo build adds about 6 s. `open_index()` attaches it read-only (`ATTACH 'file:.../combos.sqlite?mode=ro' AS spellbook`), so `validate_deck` still receives one connection and can join on `oracle_id`. If the file is missing, the check runs without combos and says so.

Tables:

```sql
CREATE TABLE combos (
    n INTEGER PRIMARY KEY,            -- compact key for the join tables
    id TEXT UNIQUE,                   -- Spellbook id, e.g. '314-6191'
    identity TEXT,                    -- 'WB'
    card_count INTEGER,               -- sum of quantities in uses
    template_count INTEGER,           -- sum of quantities in requires
    kind TEXT,                        -- 'infinite', 'near-infinite' or 'other', from the feature names
    legal_commander INTEGER,
    bracket_tag TEXT,
    popularity INTEGER,
    mana_needed TEXT,
    easy_prerequisites TEXT,
    notable_prerequisites TEXT,
    description TEXT                  -- the steps; drop this column to save 50 MB
);
CREATE TABLE combo_cards (
    oracle_id TEXT, combo INTEGER, quantity INTEGER, must_be_commander INTEGER,
    PRIMARY KEY (oracle_id, combo)
) WITHOUT ROWID;
CREATE TABLE combo_templates (
    combo INTEGER, template_id INTEGER, quantity INTEGER,
    PRIMARY KEY (combo, template_id)
) WITHOUT ROWID;
CREATE TABLE templates (id INTEGER PRIMARY KEY, name TEXT, scryfall_query TEXT);
CREATE TABLE features (id INTEGER PRIMARY KEY, name TEXT, status TEXT);
CREATE TABLE combo_features (combo INTEGER, feature_id INTEGER, PRIMARY KEY (combo, feature_id)) WITHOUT ROWID;
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);   -- source stamp, built_at
```

Card names are not stored: `cards.sqlite` has them under the same `oracle_id`. Skip variants whose `status` is not `OK` (none today) and the `aliases` array. Measured size: 96 MB with `description`, 40 MB without. I would keep it; the steps are what let a builder or an agent judge whether a reported combo really applies.

### Matching in `validate_deck`

1. Put the deck's `(oracle_id, quantity)` pairs, commanders included, in a temp table and run the query from "Offline is feasible" with `HAVING missing_cards <= 1`.
2. Drop combos that are not Commander-legal.
3. For each remaining combo, check its templates against the deck (see below) and add missing templates to the missing count. Keep combos missing at most one piece.
4. A card with `must_be_commander` only counts if it is one of the deck's commanders. Otherwise treat the combo as not included and leave it out of the report.
5. Sort into three groups:
   - **included:** nothing missing, all templates confirmed;
   - **unverified:** all named cards present, at least one template could not be decided;
   - **one card away:** exactly one card or template missing and the combo's `identity` fits the deck's. Off-colour near misses are dropped; the deck cannot add those cards.

Templates, in two stages:

- **First version:** do not evaluate. Combos with templates go to "unverified" when their named cards are all present, and are left out of "one card away". This is safe and small, and on the draft deck it changes nothing in the verdict.
- **Second version:** add the query evaluator for the deck's cards (yes, no, cannot tell). Port `template_eval.py`, fix the two-faced card case by evaluating each face on its own, and keep the rule that anything not understood is "cannot tell". Optionally fetch the 24 hand-written lists (`/cards/?matchedBy=<id>`, 24 small requests, weekly at most) into `data/spellbook/template-cards.json`.

Report shape, added to the result of `validate_deck`:

```json
"combos": {
  "data_as_of": "2026-10-12",
  "source": "Commander Spellbook, https://commanderspellbook.com",
  "included": [
    {
      "id": "314-6191",
      "url": "https://commanderspellbook.com/combo/314-6191/",
      "cards": ["Vito, Thorn of the Dusk Rose", "Bloodthirsty Conqueror"],
      "templates": [],
      "kind": "infinite",
      "produces": ["Infinite lifegain", "Infinite lifeloss", "Infinite lifegain triggers"],
      "prerequisites": "You have a way to gain life.",
      "mana_needed": "",
      "bracket_tag": "S",
      "popularity": 93017
    }
  ],
  "unverified": [],
  "one_card_away": [
    {"id": "314-3966", "missing": "Exquisite Blood", "with": ["Vito, Thorn of the Dusk Rose"], "kind": "infinite", "popularity": 125184}
  ]
}
```

List `produces` with standalone results first. Text output, one line per combo:

```
  RULE FAIL  max_infinite_combos: 1 of 0 allowed
             Vito, Thorn of the Dusk Rose + Bloodthirsty Conqueror: infinite lifegain, infinite lifeloss
             needs: You have a way to gain life.   https://commanderspellbook.com/combo/314-6191/
  One card from an infinite combo: Exquisite Blood (with Vito), Bloodthirsty Conqueror (with Vito), ...
  Combo data: Commander Spellbook, 2026-10-12
```

Report combos on every check, whether or not the deck has a combo rule, the same way role counts are always shown. Update the `validate_deck` tool description in `server.py`, which currently says it cannot detect combos.

### The per-deck rule

`check_rules` rejects boolean values today, and every existing limit is a number, so use numbers:

```toml
max_infinite_combos = 0     # fail when the deck holds more infinite combos than this
max_combos = 0              # stricter: also counts near-infinite loops, instant wins and locks
allowed_combos = ["2292-2744--5"]   # optional: ids accepted on purpose, not counted
```

- `max_infinite_combos` counts included combos of kind `infinite`. This is the direct translation of "Infinite combos: None".
- `max_combos` counts every included combo. Use it for a deck that should have no known combo of any kind.
- Each failing rule lists the combos and their cards in `cards`, like `not_together` does.
- **Unverified combos do not fail a rule.** They produce a warning naming the template, for example: "Possible infinite combo: Viscera Seer + Cathars' Crusade + any Persist Creature. Could not confirm offline." Once templates are evaluated, this warning becomes rare.
- If a combo rule is set and `data/combos.sqlite` is missing, add a warning that the rule could not be checked, the way price rules warn about unpriced cards. Do not pass silently.

For the Elenda deck, `max_infinite_combos = 0` replaces the hand-written `not_together` pair and also covers Vito + Exquisite Blood, which the pair missed.

### "Almost there" combos

Information, never a failure. They answer the builder's real question when editing: which single card would break the brief?

- Show only in-colour, Commander-legal combos, infinite ones first, then by `popularity`.
- Group by the missing card: "Exquisite Blood (with Vito)".
- Text output shows the top 10; JSON carries them all (17 for this deck).
- An agent adding a card should run the check again; a card on this list turns into a rule failure the moment it is added.

### Optional: online cross-check

A flag such as `mtg check --online` could post the list to `find-my-combos` and print any difference from the offline result. If added: one request per check, send full card names (both faces) or Oracle IDs, and treat any name missing from the response as an error. Not needed for the rule to work.

## Known limitations

1. **Only known combos.** The database is curated by people. A new or obscure loop is not found, and a clean result means "no known combo". Case 3 came out right, but because the suspicion was wrong, not because the tool reasoned about it.
2. **Prerequisites are prose.** "You have a way to gain life" or "the creature has no -1/-1 counter" cannot be checked. A combo can be reported for a deck that cannot meet its conditions. That did not happen in the test cases, and reporting too much is the safe direction for this rule.
3. **Templates are approximate offline.** 31 to 41 of 177 templates cannot be decided locally and show up as "unverified". Local evaluation re-implements part of Scryfall's search and can drift from it; one false positive on a two-faced card was seen in the prototype.
4. **"Infinite" is a naming convention,** not a field. It is consistent today, but a renamed feature could change a classification without notice. A test that counts features containing "infinite" after each index build would catch a large shift.
5. **Presence, not likelihood.** A four-card combo needing nine mana counts the same as a two-card one. `card_count`, `mana_needed`, `bracket_tag` and `popularity` are there to help a person weigh it; the rule does not.
6. **Staleness.** New sets add combos. The check should print the data's date.
7. **Card resolution must be right.** Matching is by Oracle ID, so a mistyped name that the checker already reports as unknown is also invisible to combo matching.
8. **No formal data licence.** Use rests on the documented invitation to download the bulk file. If the tool is ever published with data included, ask first.

## Prototype

All in the scratchpad, nothing in the repo:

`/private/tmp/claude-501/-Users-gxa-Library-Application-Support-Claude-scratch-workspaces-41a383e5-2e68-4af6-91b3-99be6b2ed2b6-339776c1-8666-4d5d-b922-71e15de8eb29-scratch-2026-10-12-428aae/9f2c02c2-1e55-4318-89fc-e41438765ece/scratchpad/proto/`

| File | What it does |
|---|---|
| `spellbook_stream.py` | Streams `variants.json.gz` one variant at a time. |
| `build_index.py` | Builds the SQLite combo index. |
| `check_offline.py` | Matches a decklist against the index; `--add` appends cards, `--templates` supplies template matches. |
| `template_eval.py` | Evaluates template queries against `data/cards.sqlite`. |
| `check_live.py` | Posts a decklist to `find-my-combos` and `estimate-bracket`. |
| `compare.py` | Compares offline and live results by combo id. |
| `stats.py` | Counts used in this document. |

To reproduce (paths shortened: `$S` is the scratchpad, `$R` the repo):

```bash
python3 -I $S/proto/build_index.py $S/dl-variants/variants.json.gz $S/out/combos.sqlite
python3 -I $S/proto/template_eval.py $S/out/combos.sqlite $R/data/cards.sqlite $S/out/template-matches-local.json
python3 -I $S/proto/check_offline.py $S/out/combos.sqlite $R/data/cards.sqlite $R/decks/vampire-plague-elenda.txt \
    --commander "Elenda, the Dusk Rose" --templates $S/out/template-matches-local.json --add "Bloodthirsty Conqueror"
```

Downloaded data is beside it: `dl-variants/` (the bulk file), `dl-live/` and `dl-live-fullnames/` (API responses for each case), `dl-templates/` (template card lists), `dl-src/` (backend source files read). Built outputs are in `out/`.

Requests made to outside services during this research: 24 to the Commander Spellbook API, 8 to its file host (one full download), 3 pages of its website, 3 to EDHREC, about 16 to GitHub for source and licence. All carried a descriptive User-Agent.
