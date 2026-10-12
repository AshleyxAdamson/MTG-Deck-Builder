---
name: commander-deck
description: Build, tune or review a Magic Commander (EDH) deck with the mtg-cards tools. Use when turning a deck brief into a decklist, choosing a commander, cutting or upgrading a list, or checking a deck against its budget and table rules.
---

# Commander deck

A deck is built from a **brief** (what the user wants), a **skeleton** (how many cards each role gets) and a **pool** (candidates for each role), then cut to 100 and checked. The mtg-cards MCP tools do the looking up and the checking: `search_cards`, `get_card`, `get_rulings`, `find_tags`, `commander_ideas`, `validate_deck`. In the MTG-Deck-Builder repo the same things are `uv run mtg search | card | rulings | tags | ideas | check`.

Every card fact comes from a tool call: text, cost, color identity, legality, price. Memory of Magic cards is where wrong color identities and stale prices come from.

## Steps

1. **Read the brief.** List its commander and colors, budget, table feel, hard rules and named cards. A brief that leaves the commander or another deck-defining choice open gets that question put to the user before any list is built. Done when every constraint in the brief is on your list as either *checkable* or *judgment*.

2. **Write the rules.** Copy [`rules-template.toml`](rules-template.toml) and turn every checkable constraint into a line: budget, card pairs that must not appear together, tag limits such as `board-wipe = 2`. Move the minimums to fit the archetype using [`baseline.md`](baseline.md). In the repo this is `decks/<name>.rules.toml` beside the decklist; elsewhere pass the same keys to `validate_deck` as `rules`. Done when each checkable constraint has a line.

3. **Set the skeleton.** From [`baseline.md`](baseline.md), write the target count for each role: lands, ramp, card advantage, removal, wipes, protection, and the plan cards left over. Adjust for the archetype and for the commander's mana value. Done when the targets sum to 100.

4. **Fill the pool.** Start with `commander_ideas` (and its `theme`) for what real decks of this commander run, then `search_cards` by tag, type and text inside the commander's `color_identity` for each role in the skeleton. Look up every card the brief names with `get_card`. Set `price_max` from the budget: a $150 deck is mostly cards under $3 with a few chosen splurges. Done when every role has more candidates than slots.

5. **Cut to 100.** Lands and ramp first, then card advantage and interaction, then the plan. Plan cards come in three kinds, and a deck short of one does not work: *enablers* start the engine, *payoffs* reward it, *enhancers* multiply it. Prefer a card that fills two roles. Match basic lands to the deck's colored mana symbols.

6. **Check.** Run `validate_deck` with the rules and fix until `valid` is true. Then read the rest of the report:
   - `stats.roles` are tag counts, and tags over-count (see the caveats in `baseline.md`). Confirm ramp and card advantage by naming the cards.
   - `combos.one_card_away` lists cards that would complete a known combo; keep them out of later suggestions when the brief forbids combos.
   - Every warning is either fixed or explained in your notes.

7. **Feel pass.** The checker cannot judge how a deck plays. Read the list against the brief's table feel; for a casual table, against the *telegraphed* test in `baseline.md`: opponents can see the win a turn ahead and answer it. Done when each card that restricts opponents, steals, taxes or loops has been either cut or defended in the notes.

8. **Hand over.** Write the decklist with one `1 Card Name` per line under `#` role headers, and notes covering: how it plays, how each brief constraint is met, what was cut for budget and at what price, and each decision you made that the brief did not cover. These are the user's to overrule, so list them plainly.

## Reviewing or tuning an existing list

Start at step 6 with the list as given, then walk back only as far as the problems require: a failed rule sends you to step 5, a skeleton far off the baseline to step 3. Suggest swaps as pairs (card out, card in, price change) so the count stays at 100.
