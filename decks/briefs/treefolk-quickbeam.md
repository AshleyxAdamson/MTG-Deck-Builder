# Deck Build Brief: The Walking Forest (Quickbeam)

## Task
Build a 100-card Commander deck (Magic: The Gathering) from the decisions below. This is a **beginner-friendly starter deck**: a new player should be able to pilot it by reading the cards, without learning extra mechanics.

## Locked decisions
| Item | Decision |
|---|---|
| Commander | Quickbeam, Upstart Ent |
| Colors | Green only |
| Theme | Trees: Treefolk creatures and Forests |
| Table | Casual, feel-good, not cutthroat |
| Infinite combos | None |

## Confirmed by the user on 2026-10-12
| Item | Decision | Why |
|---|---|---|
| Budget | Up to ~$150, cheaper is fine | Same as the other decks. Most green Treefolk are under $1, so the deck should land well below this. |
| Theme strictness | Mostly Treefolk | Creatures are Treefolk wherever a good one exists. Non-tree cards are fine for ramp, card draw and removal. |

## The plan
1. **Ramp** in the first few turns.
2. **Play big trees** with that mana. Each Treefolk that enters triggers Quickbeam: up to two creatures get +2/+2 and trample for the turn.
3. **Trample over** blockers, with a team-wide pump to end the game.

## Hard constraints
- Green color identity only. Every card Commander-legal.
- No infinite combos, no game changers, no stax or tax effects, no extra turns, no mass land destruction. (A removal spell that can hit one permanent of any kind, a land included, is fine.)
- Board wipes: one at most.

## Beginner rules (the heart of this brief)
Keep the deck to a small set of mechanics.

**Wanted**
- Keywords: trample, reach, vigilance.
- "+X/+X until end of turn" pump, on one creature or the whole team.
- Simple ramp: spells that fetch Forests, creatures that tap for mana, Auras that make a land produce extra mana.
- Creatures whose size counts your Forests.
- Removal a beginner can read: "destroy target artifact or enchantment", and "your creature deals damage equal to its power to target creature".
- Card draw that rewards big creatures.

**Avoid as themes** (one incidental card is acceptable if it is clearly the best simple option for its role, and gets a line in the notes)
- Graveyard recursion, +1/+1 counters, sacrifice, token swarms.
- Double-faced cards, Adventures, morph, sagas, planeswalkers.
- Cards with three or more separate abilities, or with activated abilities that need timing judgment.
- Changelings as filler Treefolk.

## Priorities
1. Treefolk with 5 or more power, and Treefolk with trample
2. Forest-count Treefolk
3. Ramp, more than the baseline, because the commander costs 6. Prefer ramp that puts Forests onto the battlefield, since it also grows the Forest-count trees
4. Team-wide pump finishers
5. A few single-target pump instants for fun
6. Simple card draw and removal
7. A mana base that is nearly all basic Forests. Few utility lands, none that enter tapped without a clear payoff

## Cards already discussed (looked up on 2026-10-12, verify each again)
- **Commander:** Quickbeam, Upstart Ent
- **Forest-count trees:** Dungrove Elder, Kalonian Twingrove, Dauntless Dourbark
- **Pump:** Giant Growth (single target), Overrun (team)
- **Ramp:** Wild Growth
- **Other Treefolk legends for the 99, if they pass the beginner rules:** Fangorn, Tree Shepherd; Verdeloth the Ancient

Left out on purpose as too complex for this deck: Six, Yedora, Grave Gardener, Kurbis, Harvest Celebrant, Ferrafor, Young Yew, Harold and Bob, First Numens.

## Deliverables
1. Full 100-card list grouped by role: commander, ramp, card draw, removal, pump, Treefolk, other creatures, lands.
2. Notes: how it plays, how each constraint is met, what was cut and why, and every decision the brief did not cover.
3. A "mechanics in this deck" list in the notes: every keyword and recurring effect, each with a one-line plain-language definition, so a new player has a cheat sheet.
4. Legality, color identity and total price from `mtg check`.

## Tooling
Card facts come from the local `mtg` tool, not memory. Starting query: `uv run mtg search --type Treefolk --identity G`.
