# What a functional Commander deck contains

Research notes for (a) a deck-building skill and (b) machine-checkable rules in `mtg check`.
Researched 2026-10-12. Everything here was read from the linked source on that date unless it is marked **unverified** or **secondary**.

How to read the evidence labels used throughout:

- **Maths**: derived from probability or simulation that the source shows.
- **Data**: counted from real decklists.
- **Convention**: a number guides repeat without showing where it came from.
- **Own calc**: I computed it for this document (method stated where it appears).

---

## 1. Consensus baseline

For a casual, mid-power (Bracket 2) deck with a commander that costs about four mana. Counts are for the 99 plus commander. A card may count in more than one row; every template that still adds up allows this.

| Category | Recommended range | Best tool tag | Support |
|---|---|---|---|
| Lands | 36 to 38 as the common guide number. Maths-based sources say 38 to 42 before discounts for cheap ramp and draw. Do not go below 36. | type `land` | **High** that 36 is a floor. **Contested** above that (see section 8). |
| Ramp | 10 (range 8 to 12). 12 when the commander costs 4 or more. Up to 15 for big-mana decks. | `ramp` (over-counts by 1 to 3, see section 4) | **High**. Maths for the "have one early" odds. |
| Card advantage | 10 to 12 | `card-advantage` (over-counts by 2 to 4) | **High** on the range, definitions differ. |
| Targeted removal / disruption | 6 to 10 pieces of removal. Up to 12 if counterspells, bounce and graveyard hate are counted in. | `spot-removal`, plus `counterspell` | **Medium**. The biggest spread between guides, and real decks run fewer than guides say. |
| Board wipes | 2 to 4. The brief's cap is 1 to 2. | `sweeper` (alias `board-wipe`) | **Medium**. |
| Protection | No template number. Real decks run 2 to 5. Voltron runs 11 or more. | `protection` | **Low** (data only, no guide number). |
| Recursion | 2 to 3 | `recursion` | **Low to medium**. |
| Graveyard hate | 1 to 2 | `hate-graveyard` | **Medium**. Every guide that mentions it says "at least one". |
| Tutors (nonland) | 0 to 2 at this power level | none that fits (see section 4) | **Medium**. |
| Win conditions / finishers | 1 dedicated finisher at minimum. One guide says 7 cards that answer "how does this deck win". | none | **Low**. Definitions differ too much to compare. |
| Theme / synergy ("plan") cards | 25 to 30 | theme-specific tags only | **Convention**. It is what is left after the rest. |
| Average mana value (nonland) | 2.8 to 3.3 | reported by `mtg check` | **Data**. |

The short version an agent can hold in its head: **37 or 38 lands, 10 ramp, 10 to 12 card advantage, 8 to 10 interaction including 2 to 3 wipes, a few protection and recursion pieces, one graveyard-hate card, and about 30 cards that are the deck's plan.**

---

## 2. Templates and where they come from

### The Command Zone template (the most cited)

Podcast by Jimmy Wong and Josh Lee Kwai. Three versions:

| Version | Date | Numbers | Verified? |
|---|---|---|---|
| Episode 151, "The Commander Deck Building Template" | 21 March 2017 | Ramp 10, card draw 10, single-target removal 5, board wipes 5, then "standalone", "enhancer" and "enabler" cards. | Date and title verified on Apple Podcasts. Numbers are **secondary** (a listener comment and third-party summaries, which disagree on which episode they belong to). |
| Episode 379, "The NEW Commander Deck Building Template" | 2 March 2021 | Lands 36 to 38, ramp 10 to 12, card draw 10, targeted removal 10 to 12, board wipes 3 to 4. | Date and title verified. Numbers **secondary** (commanderdeckmaker.com). |
| Episode 658, "Commander Deckbuilding Template for the New Era" | 18 February 2025 | Lands 38, card advantage 12, ramp 10 (12 if the commander costs 4+), targeted disruption 12, mass disruption 6, plan cards 30 including the commander. Sums to 108 because cards overlap. | Date, title and show notes verified. Numbers come from two independent viewers' written notes and one third-party article that agree with each other. I could not get the audio or a transcript, so treat as **well corroborated, not primary**. |
| Episode 659, "The Problem with Deckbuilding Templates" | 26 February 2025 (EDHREC post date) | Follow-up on when to break the template, with chapters on exceptions for each category. | Title, date and chapter list verified. Content not read. |

What the 2025 version counts, per the viewers' notes:

- **Lands (38)**: includes modal double-faced land cards.
- **Card advantage (12)**: cards that turn one card into more than one. Repeatable draw, big one-shot draw, impulse draw, and self-mill in graveyard decks. Card *selection* such as Ponder does not count.
- **Ramp (10)**: permanent acceleration only. Dark Ritual does not count.
- **Targeted disruption (12)**: one card answers one opposing card. Creature removal, counterspells, bounce, phasing.
- **Mass disruption (6)**: anything that hits several opposing cards. Board wipes, mass artifact or enchantment removal, attack-tax effects such as Propaganda, graveyard hate (the two sets of notes file graveyard hate differently; one puts it under targeted disruption). One note-taker's reading was "2 to 3 actual wipes, plus enchantment answers and graveyard interaction".
- **Plan cards (30)**: split into enablers, payoffs and enhancers.

The show notes for episode 658 link Frank Karsten's land article, a hypergeometric calculator and the Salubrious Snail calculators, so the 2025 numbers are probability-anchored, not just habit.

### Frank Karsten's mana maths

Hall of Fame player with a PhD in game theory and probability. Three TCGplayer articles, all written in 2022 and still live (page stamps say updated Feb and Aug 2025):

- **"What's an Optimal Mana Curve and Land/Ramp Count for Commander?"** Simulation that maximises mana spent over the first seven turns. Result: 42 lands plus Sol Ring for 2- and 3-mana commanders, 38 to 39 lands plus Sol Ring plus 7 to 9 two-mana rocks for 4- to 6-mana commanders. Advice: start at 42 lands, cut one land for every two or three extra mana rocks, and do not go below 37 for a mid-power deck.
- **"How Many Lands Do You Need in Your Deck? An Updated Analysis."** Regression on about 95,000 successful 60-card tournament decks, ported to 99 cards. Formula: `lands = 31.42 + 3.13 x average mana value - 0.28 x (cheap ramp and draw pieces)`.
- **"How Many Sources Do You Need to Consistently Cast Your Spells? A 2022 Update."** The table of coloured sources per mana cost, with a 99-card column (section 6).

### Tomer Abramovici's deckbuilding checklist (MTGGoldfish)

"The Power of a Deckbuilding Checklist", 11 March 2020. Aimed at budget, casual to mid-power decks that win around turns 8 to 12.

| Category | Count |
|---|---|
| Mana (lands + ramp) | 50, usually 37 lands + 13 ramp |
| Card draw | 10 |
| Targeted removal | 6 |
| Board wipes | 3 (2 to 4) |
| Graveyard recursion | 2 |
| Flexible tutors | 2 |
| Graveyard hate | 1 |
| Surprise "I win" card | 1 |

It is the only popular template that names recursion, tutors, graveyard hate and a finisher as their own lines.

### EDHREC

EDHREC publishes guidance in articles, not one official template, and the articles do not agree with each other:

- **Brian Cain, "How to Build a Commander Deck"**, 25 Nov 2024: lands 36 to 38 (more if the commander costs 5+), ramp 8 to 12, card velocity 8 to 10, interaction 8 to 10 in total with at least 2 wraths, at least 7 win-condition cards, a couple of recursion pieces, 1 to 2 tutors, 1 to 2 hate cards.
- **Cooper Gottfried, "EDHREC Guide to Upgrading Your Commander Deck"** (undated, about Oct 2025): ramp about 10 (up to 15 for big mana, never below 7), card advantage 12 or more, removal about 10 (5 to 7 for aggro, 15+ for control), board wipes 2, graveyard hate at least 1.
- **Bennie Smith, "Foundations: How to Build Mana Bases"**, 29 Nov 2024: 39 lands, and do not cut lands to fit mana rocks.
- **Dana Roach, "Superior Numbers: Land Counts"**, 20 Feb 2019: the average deck on EDHREC then ran about 29 to 31 lands and 4 mana rocks, which the author called far too low. Cites a formula from Nate Burgess: `31 + colours in the commander's identity + commander's mana value`. The 2019 averages are out of date, and I did not read Burgess's original.

EDHREC's *data* (what people actually build) is a separate anchor, used in section 5.

### 8x8 and 7x9

- **8x8 theory**: commander + 35 lands + 8 "effects you want to see", 8 cards each. The Tumblr blog that carries the name describes it as a way to start "the rough draft of an EDH decklist". Its earliest visible post is October 2019 and it does not say who invented it. Origin **unverified**.
- **7x9**: 36 lands + commander + 63 cards, as nine categories of seven or seven of nine. A 2022 Substack post (WitchPHD, 12 Aug 2022) explains the logic: 7 copies in 99 cards gives the same opening-hand odds (about 41%) as a 4-of in a 60-card deck. I checked this: 41.2% versus 39.9%. Origin of the template itself **unverified**.

Both are slot-counting aids, not claims about how much ramp or removal a deck needs. Their land counts (35 and 36) are low by every maths-based source.

### Others

- **Draftsim** (Alex Barker, updated 11 June 2026): 33 to 41 lands depending on curve, start from about 40 and adjust, about two mana rocks per land cut. Cites no outside source.
- **Tolarian Community College**: I found no written source for a specific template from this channel. **Unverified**, so it is not used here.
- **Wizards of the Coast**: no numeric template found. The Brackets articles cover power level, not deck composition.

---

## 3. What the numbers anchor to

**Probability (well supported).** Own calc, hypergeometric, 99-card library:

| Lands | 3+ lands in opening 7 | 3 lands by turn 3 | 4 lands by turn 4 |
|---|---|---|---|
| 34 | 45% | 74% | 56% |
| 36 | 50% | 78% | 62% |
| 38 | 55% | 82% | 68% |
| 40 | 59% | 85% | 73% |
| 42 | 64% | 88% | 77% |

("By turn N" means N draws after the opening hand, no mulligans, no ramp or card draw.) The Command Zone's "38 lands gives about 55%" matches. Each extra land is worth about 3 points on hitting four lands on time.

| Copies of an effect | In opening 7 | By turn 2 | In first 15 cards | In first 20 cards |
|---|---|---|---|---|
| 2 | 14% | 17% | 28% | 36% |
| 6 | 36% | 44% | 64% | 75% |
| 8 | 46% | 55% | 75% | 85% |
| 10 | 54% | 63% | 82% | 91% |
| 12 | 61% | 70% | 88% | 94% |

This is where "10 ramp" and "12 card advantage" come from: 10 copies is the point where you have one in hand or by turn 2 more often than not (63%), and 12 pushes it to 70%. It is also why 2 board wipes means you see one in barely a quarter of games by turn 8.

**Data.** Karsten's land formula is a regression on winning tournament decks. EDHREC, Archidekt and Playgroup counts describe what people build, which is not the same as what works: observed land counts (35 to 37) sit below every maths-based recommendation.

**Convention.** The round tens (10 ramp, 10 draw, 10 removal), the 8x8 and 7x9 grids, and "about 30 theme cards" are memorable numbers that happen to sit near the probability sweet spots. The split between targeted removal and wipes, the count of win conditions, protection and recursion have no maths behind them in any source I found.

**Where guides agree:** ramp near 10; card advantage 10 to 12; at least two wipes for a typical deck; at least one graveyard-hate card; templates are a first draft, to be changed by commander and archetype.

**Where they disagree:** lands (35 to 42); how much targeted removal (5 to 12); what counts as card advantage (does Ponder count?) and as ramp (do rituals and cost reducers count?); whether mana rocks replace lands.

---

## 4. Categories in detail, with tool tags

Tag checks were run against the tool's own index on 2026-10-12 (`uv run mtg search --tag ... --identity WB --brief`, and a staple list of 30 to 50 cards per category looked up through `tagged_ids`). "Catches" and "misses" below are from those checks.

A general warning for machine rules: **Scryfall tags are broader than guide definitions.** A tag-based count will usually come out higher than a human's count of the same deck. Use tag thresholds as "probably fine / look closer", not pass or fail.

### Lands

- **Range:** 36 to 38 in most guides; 38 to 42 from Karsten and Playgroup; 39 from EDHREC's mana-base article. Go up for high curves, X spells, mana sinks, landfall and commanders costing 5+. Go down only for genuinely low curves with lots of cheap draw.
- **Counts:** lands and land-faced modal double-faced cards. Karsten counts a spell/land MDFC as 0.38 of a land (0.74 if it can enter untapped).
- **Mistakes:** cutting lands to fit spells; counting mana rocks as lands; too many colourless utility lands (EDHREC: at most 4 in two colours, 7 in one).
- **Tool:** type count `Land` in `mtg check`. MDFCs whose front face is a spell are counted as spells, so a deck with several of them will look land-light. Useful extra tags: `tapland` (always tapped), `conditional-tapland`, `utility-land`, `fetchland`.

### Ramp

- **Range:** 10 (8 to 12). 12 with a 4+ mana commander. 13 to 15 for big-mana decks. Cheap commanders (2 to 3 mana) need less; Karsten's simulation wanted zero two-mana rocks for them, only Sol Ring and more lands.
- **Counts:** mana rocks, mana creatures, land-fetching spells, extra-land-drop effects, repeatable treasure makers. Cost reducers count if they cover most of the deck. One-shot rituals do not count in the Command Zone or Tomer definitions; EDHREC's ramp guide includes them.
- **Mistakes:** ramp that costs the same as the commander (it competes for the same turn); three-mana rocks in a deck that wants to act on turn 3; too much ramp and nothing to ramp into; over-relying on ramp to justify too few lands.
- **Tool:** `ramp`. Catches every staple checked: Sol Ring, signets, talismans, Cultivate, Rampant Growth, mana dorks, Smothering Tithe, Wayfarer's Bauble. **Over-includes:** lands that make extra mana (Ancient Tomb, Cabal Coffers, Nykthos, Myriad Landscape, Temple of the False God), rituals (Dark Ritual), Lotus Petal, treasure one-shots (Deadly Dispute), Ashnod's Altar, and cards that ramp an *opponent* (Path to Exile is tagged `ramp`). **Misses:** cost reducers (Herald's Horn, Urza's Incubator are under `cost-reducer`), Land Tax. Children worth using on their own: `mana-rock`, `mana-dork`, `land-ramp`, `ritual`.

### Card draw / card advantage

- **Range:** 10 to 12. Decks whose commander draws cards can go lower; decks that empty their hand fast (aggro, tokens, voltron) should not.
- **Counts:** repeatable draw engines, burst draw, impulse draw, and in graveyard decks self-mill. Cantrips and looting are selection, not advantage, in the strict definition. Prefer a mix of engines and bursts.
- **Mistakes:** counting cantrips as draw; all draw tied to the commander staying alive; all draw at 5+ mana.
- **Tool:** `card-advantage`. Catches all draw staples checked, and play-from-top effects (Future Sight, Bolas's Citadel), Necropotence, regrowth effects (Eternal Witness). **Over-includes:** cantrips and selection (Ponder, Opt, Brainstorm), looting (Faithless Looting), mana rocks that can be cashed in for a card (Mind Stone, Commander's Sphere), and utility lands (War Room, Buried Ruin). **Does not include** tutors or reanimation. Stricter options: `draw-engine` (repeatable sources only), `burst-draw`, `repeatable-card-advantage`.

### Targeted removal / disruption

- **Range:** 6 to 10 removal spells. Tomer says 6, EDHREC about 10, the Command Zone 12 but with counterspells, bounce and graveyard hate included. Measured decks are lower: a September 2026 sample of 6,532 Archidekt decks had a median of 5 per deck at every bracket from 1 to 4 (text-match method, probably an under-count).
- **Counts:** answers to creatures, artifacts and enchantments. Spread across permanent types. Cheap and instant-speed is better. Commanders or engines that remove things repeatedly count.
- **Mistakes:** only creature removal and no answer to an enchantment or artifact; all removal at sorcery speed; cutting interaction first when the deck is over 100.
- **Tool:** `spot-removal`. Catches all staples checked, including aura-based removal (Darksteel Mutation), bounce (Unsummon), edicts (Fleshbag Marauder, Grave Pact) and removal on a body (Ravenous Chupacabra). **Over-includes:** land destruction (Strip Mine, Demolition Field), creatures and planeswalkers with an incidental removal ability (Walking Ballista, Sorin, Lord of Innistrad, Aetherflux Reservoir), utility lands (Eiganjo). **Does not include** counterspells; add `counterspell` for a total "interaction" count. The parent `removal` covers spot removal and sweepers together. By permanent type: `removal-creature`, `removal-artifact`, `removal-enchantment`.

### Board wipes

- **Range:** 2 to 4. EDHREC's upgrade guide says 2, Tomer 3, the older Command Zone template 3 to 4. Creature-heavy decks run fewer and prefer one-sided ones. Creature-light decks run more.
- **Counts:** mass creature removal first. Mass artifact/enchantment removal is a separate need that the newer Command Zone template folds into "mass disruption".
- **Mistakes:** zero wipes in a deck that can fall behind on board; symmetrical wipes in a go-wide deck with no way to rebuild.
- **Tool:** `sweeper` (alias `board-wipe`). Catches all 40 wipes checked. Children: `sweeper-one-sided`, and `symmetrical` marks the two-sided ones. **Over-includes:** permanents with a sweeping ability (Elesh Norn, Grand Cenobite; Elspeth, Sun's Champion; Steel Hellkite; Liliana, Dreadhorde General), Living Death, and Armageddon (also in `mass-land-denial`). **Misses** the non-wipe "mass disruption" the Command Zone counts: Propaganda and similar are under `pillowfort`, fogs under `fog`.

### Counterspells

- **Range:** no general number. 0 outside blue. Blue decks in Playgroup's tracked lists typically run 2 to 5. Control decks run about 8.
- **Tool:** `counterspell`. Caught all 29 checked. Clean tag.

### Protection

- **Range:** no guide gives one. Playgroup's typical values by colour identity run from 1 or 2 (Jund, Dimir, Rakdos) to 9 (mono-white), with Orzhov at 5 and Esper and Sultai at 3. EDHREC average decks for the 30 most popular commanders: median 5 by this tool's tag. Decks that depend on the commander or on one board need more.
- **Counts:** hexproof/indestructible/phasing effects for one creature or the whole board, boots and greaves, flicker used defensively, "return it when it dies" effects.
- **Mistakes:** none in a commander-centric or go-wide deck; shroud on a voltron commander (stops your own auras).
- **Tool:** `protection`. Caught 45 of 50 staples. Children: `protects-creature`, `protects-all` (the board-wide ones, the best check for go-wide decks), `gives-hexproof`, `gives-indestructible`, `cheat-death`. **Over-includes:** flicker spells (Ephemerate), The One Ring, Darksteel Mutation, swords of X and Y, Sphere of Safety. **Misses:** redirection (Deflecting Swat, Imp's Mischief), counterspells used as protection, Cavern of Souls.

### Recursion

- **Range:** 2 (Tomer), "a couple" (EDHREC). Graveyard decks: 12 or more.
- **Tool:** `recursion`. Children `reanimate` (to battlefield), `regrowth` (to hand), `restock` (to library). Caught all 31 recursion spells checked. Does not include enablers such as Entomb or Buried Alive (those are `tutor`) or self-mill (`mill-self`).

### Tutors

- **Range:** 0 to 2 at casual power. Tomer says 2 on a budget and "around 10" with none. Wizards removed the explicit "few tutors" rule for Brackets 1 to 3 in October 2025 and now relies on the Game Changers list to catch the strongest ones.
- **Tool:** **no clean tag.** `tutor` includes every land tutor: Cultivate, Rampant Growth, Evolving Wilds, all fetchlands, even Path to Exile. A limit on `tutor` would flag an ordinary mana base. `tutor-card` (unrestricted tutors such as Demonic Tutor) is clean but misses type-restricted ones (Enlightened, Worldly, Mystical, Idyllic Tutor). What is needed is "`tutor` minus `tutor-land`", which the checker cannot express today.

### Graveyard hate

- **Range:** at least 1; 1 to 2 is typical. On a land (Bojuka Bog, Scavenger Grounds) it is nearly free.
- **Tool:** `hate-graveyard`. Caught all 30 checked. Slight over-inclusion of cards that exile from graveyards for their own benefit (Mimic Vat, The Scarab God).

### Win conditions / finishers

- **Range:** Tomer: 1 surprise "I win" card. EDHREC (Cain): at least 7 cards that answer "how do I win". Command Zone: inside the 30 plan cards.
- **For the briefs:** Bracket 2 wants wins that are "incremental, telegraphed, and disruptable", which matches the briefs. A finisher here means something that turns a built-up board into a win (a mass pump, a big drain), not a combo.
- **Tool:** **no tag.** Nearest: `overrun` (trample plus pump), `anthem`, `alternate-win-condition`, `bottomless-mana-sink`, `extra-combat-phase`. None of these identifies "this deck can close a game".

### Theme / synergy cards

- **Range:** 25 to 30. The Command Zone splits them into enablers, payoffs and enhancers; a deck short on any one of the three does not function.
- **Tool:** per theme only. Useful ones found: `typal-vampire` (and `typal-<type>`, though `typal-sphinx`, `typal-gorgon` and `typal-hydra` have 2 to 3 cards each, so use the type line instead), `anthem`, `repeatable-creature-tokens`, `token-doubler`, `sacrifice-outlet`, `free-sacrifice-outlet`, `death-trigger`, `drain-life`, `lifegain`, `lifegain-matters`, `top-deck-manipulation`, `top-matters`, `play-from-top`, `scry`, `surveil`, `gives-deathtouch`, `synergy-deathtouch`, `pp-counters-matter`, `counter-doubler`, `landfall`, `extra-land`, `mill-self`, `reanimate`, `group-hug`, `copy-spell`, `cost-reducer`.

### Categories with no usable tag

- **Nonland tutors** (tag exists but is swamped by land tutors).
- **Win conditions / finishers.**
- **Stax** (no tag; partial cover from `tax`, `rule-of-law`, `hatebear`, `lockdown`, `mass-land-denial`).
- **Two-card infinite combos** (no tag; cannot be detected by tags at all).
- **Mass disruption that is not a wipe** (spread over `pillowfort`, `fog`, `hate-graveyard`).
- **Land-faced MDFCs** (no tag; only per-set cycle tags).
- **Coloured sources and curve shape** are not tags but could be computed from fields the index already has (`produced_mana`, `cmc`).

---

## 5. Archetypes

### How the baseline moves

Own calc. For each EDHREC theme I took the eight most popular commanders listed on the theme page (json.edhrec.com, 2026-10-12), fetched each one's EDHREC "average deck", and counted it with this tool's tags. Values are medians of the eight. "Overall" is the 30 most popular commanders of the past year.

Read the table for **differences between rows**, not as targets: EDHREC average decks are land-light, the tags over-count (section 4), and themes share commanders. Ramp excludes lands.

| Archetype | Lands | Avg MV | Ramp | Card adv. | Spot removal | Wipes | Counters | Protection | Recursion | Creatures | Instants + sorceries |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Overall (top 30)** | 35 | 3.0 | 16 | 14 | 7.5 | 2 | 1 | 5 | 3 | 30 | 18 |
| Vampires | 35.5 | 3.2 | 9.5 | 12.5 | 9 | 3 | 0 | 3 | 3 | 31 | 16 |
| Tokens | 34 | 2.9 | 11 | 11 | 8.5 | 2.5 | 0 | 4 | 0.5 | 30 | 16.5 |
| Aristocrats | 34 | 2.9 | 13 | 12 | 9.5 | 4 | 0 | 2 | 3 | 32 | 15 |
| Voltron | 35.5 | 2.5 | 10.5 | 10 | 7 | 2 | 0.5 | 13.5 | 4 | 18.5 | 15.5 |
| Spellslinger | 34 | 2.6 | 13.5 | 23.5 | 12 | 2 | 5 | 1 | 3 | 16 | 35.5 |
| Reanimator | 35 | 3.2 | 15 | 19.5 | 9 | 2.5 | 1.5 | 2.5 | 14.5 | 34.5 | 16.5 |
| Graveyard | 35.5 | 3.1 | 17 | 17.5 | 8.5 | 2 | 0 | 2 | 17.5 | 31 | 17 |
| +1/+1 counters | 35.5 | 2.8 | 13 | 15 | 6 | 2.5 | 1.5 | 6.5 | 2 | 33 | 16 |
| Landfall | 39 | 3.4 | 28 | 13 | 5 | 1 | 0 | 1.5 | 7.5 | 28.5 | 19 |
| Control | 34 | 2.8 | 15.5 | 17.5 | 10 | 3.5 | 8.5 | 3.5 | 2 | 17.5 | 27.5 |
| Group hug | 35.5 | 2.9 | 21.5 | 27 | 5.5 | 1 | 3.5 | 3 | 1.5 | 23.5 | 20 |
| Top of library | 35 | 3.8 | 9.5 | 21.5 | 6 | 3 | 2 | 3 | 6 | 22.5 | 22 |
| Sphinxes | 35 | 4.0 | 11 | 24 | 7.5 | 3 | 4 | 2 | 4.5 | 27.5 | 19 |
| Snakes | 34.5 | 2.8 | 15.5 | 14 | 6.5 | 1.5 | 0 | 5 | 3.5 | 32.5 | 16.5 |
| Hydras | 35.5 | 2.6* | 16 | 15 | 7.5 | 1 | 1.5 | 4 | 1 | 30.5 | 18 |
| Deathtouch | 34.5 | 2.8 | 13.5 | 12.5 | 13 | 1.5 | 0 | 5.5 | 3 | 31.5 | 18 |
| Big mana | 35.5 | 5.4 | 24.5 | 19 | 10.5 | 3.5 | 2.5 | 4 | 5 | 30 | 16 |

\* Hydra mana value is understated because X counts as zero.

The Gorgon theme has too few decks on EDHREC (1 to 95 per commander) to trust; its one clear signal is a very high `spot-removal` count (18.5), because "destroy the creature this damages" effects are tagged as removal.

### What each archetype needs that the baseline does not list

Signature counts are medians from the same data. Guide advice is cited.

| Archetype | Extra needs | Signature tag counts in real decks | Guide advice |
|---|---|---|---|
| **Creature typal / go-wide tokens** (vampire deck) | Enough bodies of the type; anthems or lords; board-wide protection or a rebuild plan against wipes; draw that scales with creatures. Fewer own wipes, and one-sided where possible. | Vampires: `anthem` 5, `sacrifice-outlet` 5.5, `death-trigger` 9, `lifegain` 20.5. Tokens: `repeatable-creature-tokens` 11.5, `anthem` 3. | Draftsim: 30+ creatures for typal. EDHREC: no hard quota, but the usual expectation is that about 75% of the creatures share the type. Tokens need doublers, sac outlets or mass pump or the 1/1s do nothing. |
| **Aristocrats / sacrifice** | Three legs: outlets, fodder, payoffs. Free outlets. Recursion to reuse fodder. | `sacrifice-outlet` 12.5, `death-trigger` 14.5, `repeatable-creature-tokens` 9. | TCGplayer (Alex Ullman): 7 to 12 sacrifice outlets, and never go for the win without a backup outlet. EDHREC: payoffs are the leg most builders neglect, which produces long turns where nothing changes. |
| **Voltron** | Protection roughly triples. Evasion. Tutors for the key equipment or aura. Draw, because the deck trades many cards for one threat. Fewer creatures. | `protection` 13.5, auras + equipment 22.5, nonland tutors 5, creatures 18.5, avg MV 2.5. | TCGplayer (Chase Carroll): the five needs are card draw, tutors, protection, evasion, big buffs. Draftsim: 20 to 30 creatures. Avoid shroud. |
| **Spellslinger** | A critical mass of instants and sorceries; cheap cantrips; a few payoff permanents and backups for the commander; a real finisher. | Instants + sorceries 35.5, creatures 16, `card-advantage` 23.5 (mostly cantrips), avg MV 2.6. | Card Kingdom (Scott Cullen): permanents dilute the deck; cost reducers are overrated; do not rely on the commander alone. Draftsim: no more than 25 creatures. Published lists range from 35 to 52 instants and sorceries. |
| **Graveyard / reanimator** | Three legs: ways to fill the graveyard, reanimation, and targets worth returning. A plan for graveyard hate. | `recursion` 14.5 to 17.5, `reanimate` 11 to 14.5, `mill-self` 5.5 to 11.5. | EDHREC (Mike Carrozza): the classic failure is drawing the wrong mix of the three. Hold one reanimation effect back. Self-mill counts as card advantage here (Command Zone). |
| **+1/+1 counters** | Counter sources, payoffs, a doubler or two, proliferate, and more protection than average because the value sits on a few creatures. | `pp-counters-matter` 9 (17 for hydras), `protection` 6.5, creatures 33. | EDHREC: green is the best colour for it, black the weakest. |
| **Landfall / ramp** | More lands and far more land ramp; extra land drops; payoffs. Less interaction in practice. | Lands 39, `land-ramp` 22.5, `landfall` 17, `extra-land` 8, spot removal 5, wipes 1. | Draftsim: "as many lands as possible". Playgroup: 38 to 42. |
| **Control** | Double the interaction, instant speed, card advantage to keep up with three opponents, and a compact way to actually win. | Interaction 20 (spot 10, counters 8.5, wipes 3.5), instants + sorceries 27.5, creatures 17.5. | EDHREC: 15+ removal for long-game control decks. Creature-light decks want more wipes (Tomer). |
| **Group hug / social** | A real win condition, effects that favour you slightly more than the table, and defence. Removal is usually cut too far. | `group-hug` 22.5, `card-advantage` 27, spot removal 5.5, wipes 1. | Card Kingdom (Tom Anderson): win by outlasting, by resource overload into mana sinks, or by gifts that hurt. EDHREC: a hug deck with no win condition just picks the winner. |
| **Top of library / Sphinx** (Esper deck) | Top-deck manipulation as the engine; payoffs for it; because the curve is top-heavy, more lands and ramp than the baseline. | Top-of-library theme: `top-deck-manipulation` 31, avg MV 3.8. Sphinx commanders: avg MV 4.0, 26 nonland cards at 5+ mana, `evasion` 27.5, `card-advantage` 24, counters 4. | No dedicated guide found. See the note below. |
| **Deathtouch / snakes / hydras** (Sultai deck) | Deathtouch decks lean on removal-like effects; hydras are X spells that work as mana sinks. | Deathtouch: `spot-removal` 13. Snakes: `land-ramp` 7.5, creatures 32.5. Hydras: ramp 16, `pp-counters-matter` 17. | Draftsim: decks with mana sinks and X spells want 39 to 42 lands. |

### Notes for the three current briefs

- **Deck B (WB vampires):** matches the vampire and aristocrats rows closely (section 9).
- **Sphinx Oracle (Esper):** this is the brief where the baseline is most wrong. Real sphinx lists average mana value 4.0. Karsten's formula at 4.0 with 8 cheap ramp or draw pieces gives about 42 lands; even discounting heavily, plan for 38 to 40 lands and 12 ramp, and use the cheap scry/surveil/top-manipulation cards as the low end of the curve. `card-advantage` will read very high in this deck because every selection spell is tagged; do not treat that as "enough draw".
- **Sultai gorgon / snake / hydra:** if hydras are a real part of the deck, count X spells as expensive when judging the curve (the tool's average mana value will understate it) and lean to 38 to 39 lands. Green makes land ramp the natural choice, which also fits a graveyard foundation.

---

## 6. Mana

### Land count against mana value and ramp

Karsten's regression, with "cheap" meaning mana value 2 or less:

`lands = 31.42 + 3.13 x (average mana value of nonland cards) - 0.28 x (cheap ramp + cheap draw)`

| Avg MV | 6 cheap pieces | 8 | 10 | 12 |
|---|---|---|---|---|
| 2.6 | 37.9 | 37.3 | 36.8 | 36.2 |
| 3.0 | 39.1 | 38.6 | 38.0 | 37.5 |
| 3.3 | 40.1 | 39.5 | 39.0 | 38.4 |
| 3.6 | 41.0 | 40.5 | 39.9 | 39.3 |
| 4.0 | 42.3 | 41.7 | 41.1 | 40.6 |

Caveats Karsten states himself: the base data is 60-card tournament play, the port to 99 cards is a back-of-envelope adjustment (minus 1.35 lands for the free mulligan and first-turn draw), and the fit is loose (R squared 0.395). Read it as "about 39, give or take two", not as 39.5.

Rules of thumb from the same author's simulation article: start at 42 lands plus Sol Ring; cut one land per two or three extra mana rocks, per three or four cheap cantrips, and per three or four mana dorks; do not go below 37; decks under 38 lands with more than nine rocks would usually be better swapping a rock for a land.

### Coloured sources

Karsten's 99-card table (assumes 41 lands, about 90% reliability on curve):

| Cost | Sources needed | | Cost | Sources needed |
|---|---|---|---|---|
| C on turn 1 | 19 (untapped) | | 1CC | 28 |
| 1C | 19 | | CC | 30 |
| 2C | 18 | | 2CC | 26 |
| 3C | 16 | | 3CC | 23 |
| 4C | 15 | | 4CC | 22 |
| 5C | 14 | | 1CCC | 33 |

What counts as a source, per the article: a land that makes the colour is 1; a mana rock is about 0.75 for spells costing 3+; a fragile mana creature 0.5; a fetch-a-basic land about two-thirds per colour.

What this means in practice (my reading of the table, not a quoted rule):

- **Two colours:** with 37 lands where 8 to 10 make both colours, each colour ends up with 22 to 26 land sources plus rocks. That covers single pips and most double pips at 4+ mana. Double pips at two or three mana (CC, 1CC) need 28 to 30 and are only reliable in the deck's main colour. Triple pips want to be in a near-mono colour.
- **Three colours:** 37 lands cannot give three colours 26 sources each without most lands making two or three colours. Aim for 18 to 20 of each colour for a deck of single-pip spells, more for the main colour, and keep double-pip cards at three mana or less to one colour. This is where green land ramp or two-mana rocks earn their slots as fixing.

No other guide gives per-colour numbers for Commander. EDHREC's mana-base article only says most lands in a two-colour deck should make both colours.

### Tapped lands

No source gives a Commander number. What exists:

- Karsten, for 60-card decks: no more than 3 taplands in aggro decks with one-drops, no more than 9 in midrange or control. A conditional land counts as about a quarter of a tapland. Scaled by share of lands, the midrange ceiling for a 99-card deck is roughly 13 to 15 "tapland equivalents". This scaling is my extrapolation, and it is for decks with no one-drops.
- Card Kingdom (Kristen Gregory, 19 May 2026): a tapped land is only painless on turn 1, on turn 3 with a two-drop, or on turn 4 with a three-drop. Prefer taplands that do something (scry, surveil, cycling, Bojuka Bog, Path of Ancestry) and play more basics. Cheap commanders make taplands worse.
- Data: EDHREC average decks carry a median of 3 always-tapped and 8 or 9 conditional lands.

A workable rule for budget two- and three-colour decks: **at most 6 to 8 always-tapped lands, fewer if the commander costs 3 or less**, and count conditional lands lightly. Tool tags: `tapland`, `conditional-tapland`.

### Mana rocks against land ramp

From EDHREC's ramp guide (John Sherwood) and mana-base article (Bennie Smith):

- **Land ramp** is the hardest to remove, fixes colours through basics, and survives board wipes. It is almost all green and mostly costs two or three.
- **Rocks** work in every colour and have no summoning sickness, but die to artifact removal and to artifact-inclusive wipes. Two-mana rocks are the standard; three-mana rocks are acceptable in casual games but compete with the turn-three play.
- **Mana creatures** are the cheapest and the most fragile, and die to every creature wipe.
- **Non-green decks** should use rocks for both ramp and fixing. Green decks should prefer land ramp.
- Do not cut lands to make room for rocks (Smith). Karsten allows one land per two or three rocks, from a start of 42.

---

## 7. Curve

- **Average mana value:** observed nonland averages are 3.0 to 3.2 at Brackets 1 to 4 (Archidekt sample) and 3.0 for the top 30 EDHREC commanders (own calc). Aim for 2.8 to 3.3; above 3.5 the deck needs more lands and ramp to match.
- **Shape, per the Command Zone's 2025 episode** (viewers' notes, for 62 nonland cards): 1 mana: 9; 2 mana: 18; 3 mana: 15; 4 mana: 10; 5 mana: 5; 6+: 5. The two sets of notes differ by a card at 3, 5 and 6+. Peak at two, most of the deck at two and three, keep 5+ small, and be suspicious of six-mana permanents that do not win the game.
- **Data check** (own calc, mean of the top-30 EDHREC average decks, commander included): 1: 8.4; 2: 18.1; 3: 16.9; 4: 8.8; 5: 5.5; 6: 2.6; 7+: 4.1. Almost the same shape, so the Command Zone curve describes what popular decks look like.
- **Karsten's simulated optimum** for a 4-mana commander: 6 one-drops, 12 two-drops plus 8 two-mana rocks, 13 three-drops, 0 four-drops, 13 five-drops, 8 six-drops, 39 lands. His usable insights: put the bulk at 2 to 4 mana; run fewer cards at the commander's own mana value because the commander already fills that turn; more expensive commanders want more two-mana ramp; small deviations cost almost nothing (a few cards moved is 99.96% as good), large ones (six lands swapped for spells) cost about 2%.
- **Common mistakes:** too many cards at the commander's cost; ramp and interaction above four mana (EDHREC wants both at 2 to 4); judging a deck with X spells by its printed average.

---

## 8. Brackets, power level and "feel-bad"

### Commander Brackets, current state

Wizards' system, written by Gavin Verhey for the Commander Format Panel. Still labelled beta. Timeline:

- **11 Feb 2025:** introduced.
- **22 Apr 2025:** Game Changers list revised (about 18 added, 2 removed, and 5 cards unbanned straight onto it).
- **21 Oct 2025:** the structural update. Added expected game length to each bracket, removed the tutor restriction for Brackets 1 to 3, stopped defining Bracket 2 as "precon level", removed 10 Game Changers.
- **9 Feb 2026:** the most recent update. Added Farewell and Biorhythm to Game Changers. No structural change. Said the next update would come around May or June 2026 and that the beta label might be dropped later in the year.
- **After that:** I found no later Brackets update. Wizards' banned-and-restricted announcement of 12 Oct 2026 does not mention Commander (next one: 30 Nov 2026). The Scryfall data in this repo, dated 12 Oct 2026, flags 53 Game Changers, which is exactly the October 2025 list plus those two. So the February 2026 state appears current, but an update is overdue by Wizards' own estimate and could land soon.

| Bracket | Name | Game should not end before | Game Changers | Mass land denial | Extra turns | Two-card infinite combos |
|---|---|---|---|---|---|---|
| 1 | Exhibition | turn 9 | none | none | none | none |
| 2 | Core | turn 8 | none | none | a few, never chained | none |
| 3 | Upgraded | turn 6 | up to 3 | none | a few, never chained | none that come together cheaply or before about turn 6 |
| 4 | Optimized | turn 4 | no limit | allowed | allowed | allowed |
| 5 | cEDH | any turn | no limit | allowed | allowed | allowed |

Sources for the table: turn counts and descriptions from the October 2025 article; Game Changer limits from Wizards' Commander format page; the mass land denial, extra turn and combo columns from the February 2025 article and EDHREC's bracket guide, which reflects the October 2025 infographic. The October 2025 article text I read does not restate those three columns, so treat them as **current as far as I can tell**.

Definitions that matter:

- **Game Changers:** cards that "dramatically warp Commander games": fast mana, cheap broad tutors, free interaction, runaway resource engines. The tool has the flag (`max_game_changers`).
- **Mass land denial:** effects that regularly destroy, exile or bounce other lands, keep lands tapped, or change what four or more lands per player produce, without replacing them. Examples from Wizards: Armageddon, Ruination, Sunder, Winter Orb, Blood Moon. The `mass-land-denial` tag uses this wording.
- **Tutors:** no bracket rule since October 2025. The cheapest broad ones are Game Changers.
- **Intent:** Wizards calls it the most important part of the system. A deck that obeys the letter of a bracket but plays above it should be declared at the higher bracket. A combo that happens by accident is not a violation.

**Bracket 2 (Core) is the target for the briefs.** Its description: unoptimised and straightforward decks, wins that are "incremental, telegraphed, and disruptable", low-pressure and social play. That is close to a restatement of the vampire brief ("opponents should be able to see the threat building and respond").

Cards in or near the briefs that the bracket system flags:

- **Tergrid, God of Fright** is a Game Changer and was ranked the 4th saltiest card in EDHREC's 2025 poll. It is on the vampire brief's candidate list. The current draft does not run it.
- **Consecrated Sphinx** is a Game Changer (Wizards called it borderline in October 2025). It is the obvious sphinx for the Esper deck and would take the deck out of Bracket 2 unless the table agrees otherwise.
- **Sanguine Bond + Exquisite Blood** is a two-card infinite combo, already excluded by the vampire brief.
- **Farewell** has been a Game Changer since February 2026, which matters for any white deck picking its one or two wipes.

### What guides say makes a deck unfun to play against

- **Wizards (Feb 2025):** resource runaways, mass land denial ("frustrating to most players"), and chained extra turns, which take time from other players and leave the table unable to catch up.
- **EDHREC salt poll, 2025 results** (Andy Zupke, 13 Oct 2025): the top 15 were Stasis, Winter Orb, Vivi Ornitier, Tergrid, Rhystic Study, The Tabernacle at Pendrell Vale, Armageddon, Static Orb, Vorinclex Voice of Hunger, Thassa's Oracle, Grand Arbiter Augustin IV, Smothering Tithe, Jin-Gitaxias Core Augur, The One Ring, Humility. Grouping these is my reading, not the article's: resource denial (stax, land destruction, tax effects) dominates, followed by "pay or I get ahead" taxes, mass discard or steal, and instant wins. The 2026 poll closed on 9 Oct 2026; I found no results yet.
- **Archetype guides:** aristocrats decks are known for long solo turns that change little (EDHREC); group hug decks without a win condition decide who wins instead of winning (EDHREC, Card Kingdom); trying to combo off and failing puts a target on you (TCGplayer).

Rules a skill can apply for "not feel-bad", in rough order of how well supported they are:

1. No Game Changers, no mass land denial, no extra-turn cards, no two-card infinite combos (all four are checkable or already checked, except combos).
2. Avoid effects that stop opponents using their resources: stax, heavy taxes, mass discard, repeated theft. Tags to watch: `tax`, `rule-of-law`, `lockdown`, `discard`, `theft`, `hatebear`.
3. Wins should be visible a turn ahead and answerable by a wipe or a removal spell.
4. Keep turns short: limit long non-deterministic loops and heavy tutor chains.
5. Keep wipes few (the brief's rule) and prefer ones that end a stall instead of resetting the game.

### Budget and power

- Wizards' brackets do not use price at all.
- Card Kingdom (Scott Cullen, 19 July 2022): budget has "very little impact" on power level; expensive staples are usually the most efficient version of an effect or the only one in a colour, so the cheap replacement costs some efficiency, not function. The author runs most decks under $150.
- EDHREC's commander pages split decks into budget, mid and expensive. A popular commander's page, for example, lists 698 budget, 5,587 mid and 698 expensive decks, so the same commander is built at every price.
- Where budget really bites is the mana base (more tapped lands, fewer dual lands) and fast mana and tutors, which are also exactly the Game Changer categories. A $150 deck with no Game Changers lands in Bracket 2 almost by construction. The practical cost of budget is consistency: more taplands, so respect the tapland ceiling and the land count.
- Tomer's checklist was written for budget decks, so its numbers (37 lands, 13 ramp, 10 draw) are the best-matched template for a $150 build.

---

## 9. Sanity check: a vampire deck draft

`uv run mtg check decks/<deck>.txt` on 2026-10-12: valid, $142.27, 36 lands, 33 creatures, average mana value 3.3, tagged 9 ramp, 15 card-advantage, 12 removal, 2 sweepers. Extra counts below are own calc with the same tags.

| Measure | Draft | Guidance | EDHREC vampire decks (median) | Verdict |
|---|---|---|---|---|
| Lands | 36 | 37 to 38 (templates); about 39 by Karsten's formula at MV 3.3 with 8 cheap pieces | 35.5 | One or two short. Legion's Landing is a partial land. |
| Ramp, tagged | 9 | 10, or 12 for a 4-mana commander | 9.5 | Real count is 7 rocks: two of the nine tagged cards are Path to Exile (false positive) and Legion's Landing. Herald's Horn is a cost reducer the tag misses. So 8 at best. Low. |
| Card advantage, tagged | 15 | 10 to 12 | 12.5 | Fine. About 12 or 13 after removing Mind Stone and Voldaren Estate, which are tagged only for an incidental draw ability. Seven are repeatable engines by the `draw-engine` tag. |
| Spot removal, tagged | 10 | 6 to 10 | 9 | Fine. Seven real spells plus three incidental. Covers creatures, artifacts and enchantments. |
| Board wipes | 2 | 2 to 4 (brief cap 2) | 3 | At the cap. Both are one-sided for a vampire board, which is what guides advise for go-wide. |
| Protection | 0 | 2 to 5 | 3 | **Gap.** Nothing protects the board from someone else's wipe, the standard go-wide weakness. |
| Recursion | 6 | 2 to 3 | 3 | High on purpose (the "raise their dead" package). |
| Graveyard hate | 1 | 1 to 2 | 2 | Kaya, Geist Hunter only by tag. A Bojuka Bog would be a free second. |
| Nonland tutors | 0 | 0 to 2 | 0.5 | Fine. |
| Game Changers | 0 | 0 for Bracket 2 | 0.5 | Fine. |
| Creatures / vampires | 33 / 32 | 30+ for typal | 31 | Fine. |
| Anthems | 11 | no number | 5 | Heavy, by design. |
| Sacrifice outlets | 5 (2 free) | 7 to 12 for a full aristocrats deck | 5.5 | Fine for a deck where sacrifice is a side plan. |
| Taplands | 4 always, 4 conditional | at most 6 to 8 always-tapped | 4.5 / 4 | Fine. |
| Curve | 1: 6, 2: 15, 3: 19, 4: 13, 5: 6, 6: 1, 7+: 4 | peak at 2; thin the commander's own slot | 1: 8, 2: 17, 3: 17, 4: 10, 5: 7, 6: 4, 7+: 2 | Peaks at three, and 13 four-drops sit on the same turn as a 4-mana commander. A little slow. |
| Colour sources (lands) | W 24, B 26 | see section 6 | n/a | The deck has 16 cards with BB or BBB and none with WW. By Karsten's table 1BB wants 28 and 1BBB wants 33. Black is slightly under and white is over. Swapping two Plains for Swamps would help. |

Overall the draft sits almost exactly on what real vampire decks look like. Against the guidance its soft spots are: lands and ramp both on the low side for a 3.3 curve with a 4-mana commander, no protection, and a curve bunched at three and four.

---

## 10. Suggested machine-checkable rules

Not implemented; a sketch for whoever writes the checks. `decks.py` currently lists a `minimums` rule key next to `limits`, though the README documents only `limits`; confirm it is finished before relying on it.

Tag thresholds are set a little above the guide numbers where the tag over-counts.

| Check | Suggested rule | Severity |
|---|---|---|
| Lands | at least 36; warn below 37 when average MV is over 3.2; warn below 38 when over 3.6 | error under 36, else warning |
| `ramp` | at least 10 by tag (roughly 8 real) | warning |
| `card-advantage` | at least 12 by tag (roughly 10 real); or `draw-engine` at least 4 | warning |
| `spot-removal` + `counterspell` | at least 8 | warning |
| `sweeper` | 1 to 4, or the brief's own cap | warning under, error over cap |
| `protection` | at least 2; at least 4 for go-wide and commander-centric decks | warning |
| `hate-graveyard` | at least 1 | warning |
| `recursion` | at least 2 | info |
| `tapland` | at most 8 | warning |
| Average mana value | 2.6 to 3.5 | warning outside |
| Game Changers, `mass-land-denial`, `extra-turn` | 0 for Bracket 2 | error (already supported) |

Things that would need new code, in order of value: a per-colour source count against pip demand (the index has `produced_mana` and `mana_cost`); a curve histogram with a warning for too many cards at the commander's mana value; "tutor minus tutor-land"; treating land-faced MDFCs as partial lands; applying Karsten's formula as a suggested land count. Archetype minimums (sacrifice outlets, anthems, self-mill and so on) fit the existing per-deck rules file better than a global rule.

Not checkable from tags at all: two-card combos, whether the deck has a way to win, how long its turns take.

---

## 11. Disagreements and open questions

1. **Lands: 35, 37 or 40?** Observed decks sit at 35 to 37. Templates say 36 to 38. Karsten's maths and Playgroup's opening-hand data say 38 to 42, and Karsten argues directly that 36 is too few. The Command Zone moved up to 38 in 2025 and cites Karsten. The gap is partly real (casual players under-run lands) and partly definitional (rocks, MDFCs and cheap draw substitute for some lands). For a budget deck with more taplands and few cheap cantrips, the higher end is the safer reading.
2. **Do rocks replace lands?** EDHREC's mana-base article says never cut lands for rocks. Karsten says one land per two or three rocks, from a base of 42. Draftsim says about two rocks per land from a base of 40. These land in similar places (37 to 39 lands with 8 to 10 rocks) because they start from different bases.
3. **How much targeted removal?** 5 or 6 (Tomer, the first Command Zone template, measured decks) against 10 to 12 (the later Command Zone templates, EDHREC's upgrade guide). The trend in guides since 2021 is clearly upward. Part of the gap is that newer templates count counterspells, bounce and graveyard hate in the same bucket.
4. **Board wipes:** 2 (EDHREC) to 5 (2017 Command Zone). The newer advice is fewer true wipes. The brief's cap of 1 to 2 is at the low end of every guide but consistent with the go-wide advice.
5. **What is card advantage?** The Command Zone excludes selection (Ponder). EDHREC's "card velocity" and Scryfall's tag include it. This changes the count by 3 to 10 cards in blue decks.
6. **Is the Brackets system about to change?** Wizards said in February 2026 that it was considering splitting Bracket 3 and might drop the beta label, with an update expected mid-2026. I found none. Re-check before the skill hard-codes bracket rules.
7. **Unverified items a later pass could close:** the exact numbers and wording of Command Zone episodes 151, 379 and 658 (needs the audio or a transcript); Tolarian Community College's advice; the origin of 8x8 and 7x9; Nate Burgess's original formula; EDHREC's 2026 salt results.
8. **No guide gives numbers for protection, per-colour sources in Commander, or tapped lands.** The ranges in this document for those three are from data and from scaling 60-card advice, and are the least certain numbers here.
9. **Third-party datasets** (Playgroup, the Archidekt sample published by ScrollVault) are from commercial sites that sell deck tools. Their numbers are plausible and agree with EDHREC, but I could not audit their methods.

---

## 12. Sources

All accessed 2026-10-12.

### Templates and general guides

- The Command Zone 658, "Commander Deckbuilding Template for the New Era", 18 Feb 2025. Show notes: https://podcasts.apple.com/ca/podcast/commander-deckbuilding-template-for-the-new-era-658/id898023861?i=1000693689243 and https://edhrec.com/articles/the-command-zone-commander-deckbuilding-template-for-the-new-era-the-command-zone-658-mtg-edh-magic-gathering. Supports: date, title, chapter list, links to Karsten and calculators.
- Viewer notes on episode 658: https://note.com/black777cat/n/n588a5c571b7d?hl=en and https://www.alanwsmith.com/en/38/z9/2w/vi/ (Jan 2026). Support: the template numbers, category definitions, curve. Secondary.
- https://github.com/OlliTapio/mtg-deck-optimizer/blob/main/command_zone_template.md and https://commanderdeckmaker.com/learn/deckbuilding/command-zone-template. Third-party summaries of the older templates. Secondary, and they disagree with each other.
- The Command Zone 659, "The Problem with Deckbuilding Templates": https://edhrec.com/articles/the-command-zone-the-problem-with-deckbuilding-templates-the-command-zone-659-mtg-edh-magic-gathering. Supports: date and chapter list only.
- The Command Zone 379, 2 Mar 2021: https://podcasts.apple.com/us/podcast/the-new-commander-deck-building-template-379/id898023861?i=1000511316766. Date and title only.
- The Command Zone 151, 21 Mar 2017: https://podcasts.apple.com/sg/podcast/the-commander-deck-building-template-151/id898023861?i=1000382919297. Date and title only.
- Tomer Abramovici, "The Power of a Deckbuilding Checklist", MTGGoldfish, 11 Mar 2020: https://www.mtggoldfish.com/articles/the-power-of-a-deckbuilding-checklist-commander-quickie. Supports: the checklist table.
- Brian Cain, "How to Build a Commander Deck", EDHREC, 25 Nov 2024: https://edhrec.com/articles/how-to-build-a-commander-deck
- Cooper Gottfried, "EDHREC Guide to Upgrading Your Commander Deck" (undated; image path suggests Oct 2025): https://edhrec.com/guides/edhrec-guide-to-upgrading-your-commander-deck
- 8x8 Theory blog: https://the8x8theory.tumblr.com/
- WitchPHD, "7x9, Every Time", 12 Aug 2022: https://witchphd.substack.com/p/7x9-every-time

### Mana and curve

- Frank Karsten, "What's an Optimal Mana Curve and Land/Ramp Count for Commander?", TCGplayer (written 2022, page updated 28 Aug 2025): https://www.tcgplayer.com/content/article/What-s-an-Optimal-Mana-Curve-and-Land-Ramp-Count-for-Commander/e22caad1-b04b-4f8a-951b-a41e9f08da14/. Supports: simulated curves, 42-land start, "not below 37", rock-for-land rates.
- Frank Karsten, "How Many Lands Do You Need in Your Deck? An Updated Analysis", TCGplayer (written 2022, page updated 13 Feb 2025): https://www.tcgplayer.com/content/article/How-Many-Lands-Do-You-Need-in-Your-Deck-An-Updated-Analysis/cd1c1a24-d439-4a8e-b369-b936edb0b38a/. Supports: the 99-card formula, MDFC weights, definition of "cheap".
- Frank Karsten, "How Many Sources Do You Need to Consistently Cast Your Spells? A 2022 Update", TCGplayer (page updated 13 Feb 2025): https://www.tcgplayer.com/content/article/How-Many-Sources-Do-You-Need-to-Consistently-Cast-Your-Spells-A-2022-Update/dc23a7d2-0a16-4c0b-ad36-586fcca03ad8/. Supports: coloured-source table, tapland guidance, partial-source weights.
- Bennie Smith, "Foundations: How to Build Mana Bases", EDHREC, 29 Nov 2024: https://edhrec.com/articles/foundations-how-to-build-mana-bases
- John Sherwood, "The EDHREC Guide to Ramp in Commander" (undated; about Jan 2026): https://edhrec.com/guides/the-edhrec-guide-to-ramp-in-commander
- Dana Roach, "Superior Numbers: Land Counts", EDHREC, 20 Feb 2019: https://edhrec.com/articles/superior-numbers-land-counts. Old data; source for the Burgess formula.
- Kristen Gregory, "Are Tapped Lands Viable in Modern Day Commander?", Card Kingdom, 19 May 2026: https://blog.cardkingdom.com/are-tapped-lands-viable-in-modern-day-commander/
- Alex Barker, "How Many Lands Should You Really Play in Commander?", Draftsim, updated 11 June 2026: https://draftsim.com/mtg-edh-deck-number-of-lands/
- Playgroup, "How many lands" and "Deck template" (third-party tracked-game data; categories from Scryfall tags): https://playgroup.gg/commander/how-many-lands and https://playgroup.gg/commander/deck-template
- ScrollVault, "Commander Deck Ratios by Bracket" (6,532 Archidekt decks collected 7 Sept 2026; no author named): https://scrollvault.net/guides/commander-deck-ratios.html

### Archetypes

- EDHREC JSON for theme pages, commander pages and average decks, e.g. https://json.edhrec.com/pages/tags/aristocrats.json and https://json.edhrec.com/pages/average-decks/<commander>.json. Supports: all "own calc" archetype numbers.
- Cooper Gottfried, "EDHREC Guide to Aristocrats in Commander": https://edhrec.com/guides/edhrec-guide-to-aristocrats-in-commander
- Alex Ullman, "How to Play an Aristocrats Commander Deck", TCGplayer (page updated 13 Feb 2025): https://www.tcgplayer.com/content/article/How-to-Play-an-Aristocrats-Commander-Deck/61620389-aef6-4c14-93ae-2a3645173f6c/
- Nick Price, "EDHREC Guide to Spellslinger in Commander": https://edhrec.com/guides/edhrec-guide-to-spellslinger-in-commander
- Scott Cullen, "Spellslinger Commander Deck Building Guide", Card Kingdom, 4 May 2021: https://blog.cardkingdom.com/spellslinger-commander-deck-building-guide/
- Chase Carroll, "5 Things Every Voltron MTG Commander Deck Needs", TCGplayer (page updated 7 Feb 2023): https://www.tcgplayer.com/content/article/5-Things-Every-Voltron-MTG-Commander-Deck-Needs/a488b9fc-27a6-48fa-88a0-c772af966ea9/
- Mike Carrozza, "EDHREC Guide to Reanimator in Commander": https://edhrec.com/guides/edhrec-guide-to-reanimator-in-commander
- Cooper Gottfried, "EDHREC Guide to +1/+1 Counters in Commander": https://edhrec.com/guides/edhrec-guide-to-1-1-counters-in-commander
- Cooper Gottfried, "EDHREC Guide to Tokens in Commander": https://edhrec.com/guides/edhrec-guide-to-tokens-in-commander
- Ryan Sikora, "Vampires in Commander", EDHREC: https://edhrec.com/articles/vampires-in-commander-guide
- EDHREC, "Tribes" overview: https://edhrec.com/articles/tribes
- A.L. Walser, "How Many Creatures to Put in Your Commander Deck", Draftsim, updated 1 Sept 2026: https://draftsim.com/how-many-creatures-in-a-commander-deck/
- Tom Anderson, "Commander Archetype Inspection: Group Hug", Card Kingdom, 8 Mar 2024: https://blog.cardkingdom.com/commander-archetype-inspection-group-hug/

### Brackets, salt and budget

- Gavin Verhey, "Introducing Commander Brackets Beta", 11 Feb 2025: https://magic.wizards.com/en/news/announcements/introducing-commander-brackets-beta
- "Commander Brackets Beta Update", 22 Apr 2025: https://magic.wizards.com/en/news/announcements/commander-brackets-beta-update-april-22-2025
- "Commander Brackets Beta Update", 21 Oct 2025: https://magic.wizards.com/en/news/announcements/commander-brackets-beta-update-october-21-2025
- "Commander Brackets Beta Update", 9 Feb 2026: https://magic.wizards.com/en/news/announcements/commander-brackets-beta-update-february-9-2026
- Wizards, Commander format page: https://magic.wizards.com/en/formats/commander
- Wizards, Banned and Restricted Announcement, 12 Oct 2026 (no Commander content): https://magic.wizards.com/en/news/announcements/banned-and-restricted-october-12-2026
- Cooper Gottfried, "EDHREC Guide to Commander Brackets" (reflects Oct 2025): https://edhrec.com/guides/edhrec-guide-to-commander-brackets
- Commander Brackets changelog (third-party; used to cross-check the timeline): https://commanderbrackets.com/changelog
- Andy Zupke, "Salt 2025 Scores Are Here", EDHREC, 13 Oct 2025: https://edhrec.com/articles/salt-2025-scores-are-here
- Scott Cullen, "Even More Budget Equivalents to Commander Staples", Card Kingdom, 19 July 2022: https://blog.cardkingdom.com/even-more-budget-equivalents-to-commander-staples/

### Local

- This repo's Scryfall index (`data/cards.sqlite`, bulk data dated 2026-10-12): tag contents, the Game Changer flag, and all counts of the vampire deck draft.
