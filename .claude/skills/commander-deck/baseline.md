# Baseline for a casual Commander deck

Numbers for a mid-power, casual deck (Wizards' Bracket 2, "Core") with a commander costing about four mana. A card may count toward more than one role. Evidence and sources for everything here are in this repo at [`docs/research/commander-deckbuilding.md`](../../../docs/research/commander-deckbuilding.md); when a number here surprises you, read it there.

## Skeleton

| Role | Target | Tag to search and count | Tag caveat |
|---|---|---|---|
| Lands | 37 to 38; never under 36 | type `Land` | Spell-faced double-faced lands count as spells |
| Ramp | 10; 12 if the commander costs 4+; up to 15 for big mana | `ramp` (`mana-rock`, `mana-dork`, `land-ramp`) | Over-counts by 1 to 3: includes Path to Exile, rituals, mana lands. Misses cost reducers (`cost-reducer`) |
| Card advantage | 10 to 12 | `card-advantage` (`draw-engine`, `burst-draw`) | Over-counts by 2 to 4: includes cantrips, Mind Stone, some lands |
| Targeted removal | 6 to 10, across creatures, artifacts and enchantments | `spot-removal` (+ `counterspell` in blue) | Includes incidental abilities on creatures and planeswalkers |
| Board wipes | 2 to 4, or the brief's cap | `sweeper` (alias `board-wipe`; `sweeper-one-sided`) | Reliable |
| Protection | 2 to 5; 4+ when the deck leans on its commander or a wide board | `protection` (`protects-all` for the whole board) | Includes flicker spells |
| Recursion | 2 to 3 | `recursion` (`reanimate`, `regrowth`) | Reliable |
| Graveyard hate | 1 to 2 | `hate-graveyard` | Reliable |
| Nonland tutors | 0 to 2 | none usable: `tutor` includes every land search | Count by hand |
| Plan cards | 25 to 30: enablers, payoffs, enhancers | theme tags, type line, text | Per deck |
| Finisher | at least 1 way to turn a board into a win | none | Judge by hand |

Average mana value of nonland cards: 2.8 to 3.3. Curve peaks at two; most cards at two and three; few at the commander's own cost, since the commander already fills that turn; six-mana cards should win games.

## Archetype adjustments

| Archetype | Move from the baseline | Needs beyond the baseline |
|---|---|---|
| Creature typal, go-wide tokens | 30+ creatures, about three quarters sharing the type. Fewer own wipes, one-sided where possible | Anthems or lords; board-wide protection or a way to rebuild; draw that scales with creatures; a doubler, sacrifice outlet or mass pump so small tokens matter |
| Aristocrats / sacrifice | Removal and wipes slightly up | Three legs: 7 to 12 `sacrifice-outlet` (some free), fodder, and `death-trigger` payoffs. Payoffs are the leg most often short |
| Voltron | About 19 creatures; protection triples to 11+ | Evasion, cheap auras and equipment, more draw. Hexproof over shroud |
| Spellslinger | 30 to 36 instants and sorceries, about 16 creatures | Cheap cantrips, a few payoff permanents, a real finisher |
| Graveyard / reanimator | Recursion 12 to 18; self-mill counts as card advantage | Three legs: fill the graveyard (`mill-self`), `reanimate`, targets worth returning |
| +1/+1 counters | Protection up to 6 | Counter sources, payoffs, a doubler, proliferate |
| Landfall, big mana, X spells | 39 to 42 lands; ramp 15+ | Extra land drops and payoffs. Printed mana value understates X spells |
| Control | Interaction doubles to about 20, counterspells about 8, creatures about 17 | Instant speed, card advantage to keep up with three opponents, a compact win |
| Group hug | Removal is usually cut too far; keep 6+ | A real win condition, or the deck only chooses who else wins |
| Top-heavy (average mana value 3.6+) | 38 to 40 lands and 12 ramp | Cheap selection spells as the low end of the curve |

## Mana

- **Land count from the curve** (Karsten): lands = 31.4 + 3.13 x average mana value - 0.28 x (ramp and draw costing 2 or less). At 3.0 with ten cheap pieces that is 38; at 3.3, 39; at 4.0, 41. Real decks run 35 to 37 and are short. Budget decks have more tapped lands, so lean high.
- **Colored sources.** Count the deck's mana symbols per color and split basics to match. A double symbol at two or three mana (`{B}{B}`, `{1}{B}{B}`) wants 28 to 30 sources of that color, which only the main color of a two-color deck reaches. In three colors aim for 18 to 20 sources each, more in the main color.
- **Tapped lands.** At most 6 to 8 always-tapped lands (`tapland`), fewer under a commander costing 3 or less. Prefer ones that do something.
- **Rocks or land ramp.** Green decks prefer land ramp, which survives wipes and fixes colors. Other decks use two-mana rocks. Ramp at the commander's own cost competes with the commander.
- At most 4 colorless utility lands in two colors.

## Table feel

Bracket 2 asks for wins that are *incremental, telegraphed and disruptable*. In checkable terms: no game changers, no mass land denial, no extra-turn cards, no two-card infinite combos. The rules template sets all four.

The *telegraphed* test for everything else: opponents can see the win a turn ahead, and a board wipe or a removal spell answers it.

What makes a deck miserable to sit across from, in order of how often players name it: stopping opponents from using their resources (stax, taxes, land destruction), "pay or I pull ahead" effects, mass discard and repeated theft, instant wins, and long solo turns that change little. Tags worth scanning a list for: `tax`, `rule-of-law`, `lockdown`, `hatebear`, `discard`, `theft`.

Price is a soft power control: fast mana and the strongest tutors are both expensive and game changers, so a $150 deck with no game changers lands in Bracket 2 almost by construction. `commander_ideas` reports popularity, which leans toward staples and stronger builds; treat it as a pool to filter through the brief, never as the list.
