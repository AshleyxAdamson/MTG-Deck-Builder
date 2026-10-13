# The Walking Forest (Quickbeam): notes

Decklist: `decks/treefolk-quickbeam.txt`. Brief: `decks/briefs/treefolk-quickbeam.md`. Rules: `decks/treefolk-quickbeam.rules.toml`.
The decklist pastes into Moxfield as is. Set the commander in Moxfield's commander slot.
A beginner starter list for review, not a locked one. Card facts and prices come from the local `mtg` tool (prices as of 2026-10-12, each card's cheapest paper printing). The candidate pool started from `uv run mtg ideas "Quickbeam, Upstart Ent"` (EDHREC data), then every card was checked against the brief's beginner rules.

Shape: 100 cards, $72.25. 38 lands (all basic Forests, $3.42 of the total), 15 ramp (16 counting Llanowar Visionary), 33 creatures (24 of them Treefolk, counting Quickbeam), 0 planeswalkers. Average mana value of nonland cards is 3.6.

## How it plays

- **Turns 1 to 3: ramp.** Llanowar Elves, Elvish Mystic, Fyndhorn Elves, Wild Growth, Nature's Lore, Three Visits, Rampant Growth, Wood Elves and Sol Ring all come down early. The goal is six mana on turn four or five.
- **Turns 4 to 6: play big trees.** Quickbeam costs six. Quickbeam himself and every other Treefolk that enters after him (23 more creatures, plus the token from Kalonian Twingrove and Lignify) each give up to two creatures +2/+2 and trample until end of turn. Cast a Treefolk before combat, then attack.
- **Trample is the plan.** Forest-count trees (Dungrove Elder, Dauntless Dourbark, Kalonian Twingrove, Treefolk Seedlings) grow with each land. Five Treefolk already have trample (Timberland Ancient, Ghastbark Twins, Mossbeard Ancient, Oakgnarl Warrior, Shriekwood Devourer). Dauntless Dourbark is a sixth while you control another Treefolk, and Quickbeam hands trample out to the rest.
- **Finish with a team pump.** Overrun and Overwhelming Stampede give the whole team trample and a big bonus. Return of the Wildspeaker does the same at instant speed.
- **Cards keep coming.** Elemental Bond and Garruk's Packleader draw when a big creature enters. Beast Whisperer draws when you cast a creature spell. Colossal Majesty draws at your upkeep while you control a creature with power 4 or more. Shamanic Revelation and Collective Unconscious draw one per creature. Ulvenwald Observer and Warden of the Woods draw when big trees die or get targeted.
- **Simple answers.** The "bite" spells (Bite Down, Master's Rebuke, Rocky Rebuke, Rabid Bite, Ram Through) use your biggest creature as the weapon. Return to Nature, Rootgrapple and Reclamation Sage handle artifacts and enchantments.

Opponents can see it coming: it is a creature deck that loses to a board wipe and to chump blockers. Heroic Intervention saves the board from a wipe (hold two mana open and cast it in response), and Blossoming Defense saves one creature from removal.

## Cards by role

- **Commander (1):** Quickbeam, Upstart Ent
- **Ramp (15):** Sol Ring; Wood Elves; Llanowar Elves; Elvish Mystic; Fyndhorn Elves; Three Visits; Llanowar Tribe; Great Forest Druid; Bosk Banneret; Nature's Lore; Rampant Growth; Cultivate; Skyshroud Claim; Wild Growth; Overgrowth
- **Card draw (9):** Elemental Bond; Colossal Majesty; Garruk's Packleader; Beast Whisperer; Llanowar Visionary; Shamanic Revelation; Return of the Wildspeaker; Harmonize; Collective Unconscious
- **Removal (9):** Bite Down; Master's Rebuke; Rocky Rebuke; Rabid Bite; Ram Through; Return to Nature; Rootgrapple; Lignify; Reclamation Sage
- **Pump (7):** Giant Growth; Titanic Growth; Primal Bellow; Blossoming Defense; Heroic Intervention; Overrun; Overwhelming Stampede
- **Treefolk (21):** Dungrove Elder; Treefolk Seedlings; Battlewand Oak; Dauntless Dourbark; Magnigoth Sentry; Cloudcrown Oak; Crabapple Cohort; Timber Protector; Redwood Treefolk; Seedguide Ash; Blanchwood Treefolk; Rootless Yew; Kalonian Twingrove; Timberland Ancient; Ulvenwald Observer; Warden of the Woods; Orchard Warden; Ghastbark Twins; Mossbeard Ancient; Oakgnarl Warrior; Shriekwood Devourer
- **Other creatures (0):** none
- **Lands (38):** 38 Forest

## Brief compliance

| Constraint | Status |
|---|---|
| Commander | Quickbeam, Upstart Ent |
| Green only | `mtg check` reports no off-identity cards. |
| Commander-legal | `mtg check` reports no illegal cards. |
| Theme: Treefolk and Forests | 24 of 33 creatures are Treefolk. 38 of 38 lands are Forests. |
| Mostly Treefolk | The 9 non-Treefolk creatures are all ramp, draw or removal: Llanowar Elves, Elvish Mystic, Fyndhorn Elves, Wood Elves, Llanowar Tribe, Garruk's Packleader, Beast Whisperer, Llanowar Visionary, Reclamation Sage. |
| Budget ~$150 | $72.25. Timber Protector ($22.94), Heroic Intervention ($9.24) and Three Visits ($5.55) are the big spends. |
| Casual table | No stax, no theft, no wipes. See the feel pass in "How it plays". |
| No infinite combos | `mtg check` finds 0 known combos. See "One card away" below. |
| No game changers | 0, per `mtg check`. |
| No stax or tax | None by reading. The rules file limits `tax-attack`, `cast-tax` and `lockdown` to 0, and the broad `tax` tag to 1 (Warden of the Woods, which is a false positive). |
| No extra turns, no mass land destruction | None. The rules file limits `extra-turn` and `mass-land-denial` to 0. Rootgrapple can destroy a single land, which the brief allows as one-target removal. |
| Board wipes: one at most | Zero. Green has few, and the deck wants its board. |
| Beginner: keywords trample, reach, vigilance | Trample, reach (Magnigoth Sentry, Cloudcrown Oak, Timberland Ancient) and vigilance (Warden of the Woods, Oakgnarl Warrior) are the only combat keywords. Hexproof and indestructible also appear, on a few cards. |
| Beginner: "+X/+X until end of turn" pump | Giant Growth, Titanic Growth, Primal Bellow, Blossoming Defense (one creature); Overrun, Overwhelming Stampede, Return of the Wildspeaker (whole team). |
| Beginner: simple ramp | Mana creatures, Forest-fetching spells (Nature's Lore, Three Visits, Skyshroud Claim, Rampant Growth, Cultivate), Wood Elves, and two mana Auras (Wild Growth, Overgrowth). |
| Beginner: creatures that count Forests | Dungrove Elder, Dauntless Dourbark, Kalonian Twingrove, Treefolk Seedlings. Primal Bellow is the spell version. |
| Beginner: readable removal | Five bite spells, plus Return to Nature, Rootgrapple, Lignify and Reclamation Sage. |
| Beginner: draw that rewards big creatures | Elemental Bond (power 3+), Colossal Majesty (power 4+), Garruk's Packleader (power 3+), Shamanic Revelation, Collective Unconscious, Return of the Wildspeaker, Ulvenwald Observer. |
| Avoid: graveyard recursion | None. Return to Nature can exile a card from a graveyard, which is the opposite. |
| Avoid: +1/+1 counters | None. |
| Avoid: sacrifice | None. Seedguide Ash, Ulvenwald Observer and Rootless Yew have "when this dies" effects, which are not sacrifice. |
| Avoid: token swarms | One exception: Kalonian Twingrove makes one token. See below. |
| Avoid: double-faced, Adventures, morph, sagas, planeswalkers | None. |
| Avoid: three or more abilities, or timing-judgment abilities | One exception: Timberland Ancient. See below. |
| Avoid: changelings as filler | None. |
| Priority: Treefolk with 5+ power, or trample | 9 Treefolk have printed power 5 or more (Quickbeam, Warden of the Woods, Ulvenwald Observer, Timberland Ancient, Ghastbark Twins, Mossbeard Ancient, Oakgnarl Warrior, Shriekwood Devourer, Rootless Yew). 5 have trample, and Dauntless Dourbark has it while you control another Treefolk. |
| Priority: Forest-count Treefolk | Four, listed above. |
| Priority: more ramp than baseline | 15 ramp, against the baseline's 12 for a 4+ cost commander. |
| Priority: ramp that puts Forests onto the battlefield | Six: Nature's Lore, Three Visits, Skyshroud Claim (two Forests), Wood Elves, Rampant Growth, Cultivate. |
| Priority: mana base nearly all basic Forests | 38 Forests, nothing else. No tapped lands. |
| Cards already discussed | In: Dungrove Elder, Kalonian Twingrove, Dauntless Dourbark, Giant Growth, Overrun, Wild Growth. Out: Fangorn and Verdeloth (see "Cut and why"). |

### Avoid-list exceptions that stayed

- **Timberland Ancient** has three abilities: reach, trample and forestcycling. It stayed because all three are one-word keywords, it is a 6/5 trampler, and it is the deck's only creature that fetches a Forest from your hand. That helps the Forest-count trees.
- **Kalonian Twingrove** makes one Treefolk token. It stayed because the brief names it, the token is a Treefolk, and so one card gives two Quickbeam triggers. It is one token, not a swarm.

## Ramp and card advantage, confirmed by name

The tag counts are 16 ramp and 12 card advantage. They over-count, so here are the real cards.

- **Ramp (15):** Sol Ring, Llanowar Elves, Elvish Mystic, Fyndhorn Elves, Llanowar Tribe, Great Forest Druid, Bosk Banneret (cost reducer), Nature's Lore, Three Visits, Rampant Growth, Cultivate, Skyshroud Claim, Wood Elves, Wild Growth, Overgrowth. The tag does not count Bosk Banneret (it tags it as a cost reducer). Its 16 is the other 14, plus Llanowar Visionary (taps for G, a real ramp piece) and Seedguide Ash (only ramps when it dies).
- **Card advantage, reliable (9):** Elemental Bond, Colossal Majesty, Garruk's Packleader, Beast Whisperer, Llanowar Visionary, Shamanic Revelation, Return of the Wildspeaker, Harmonize, Collective Unconscious.
- **Card advantage, conditional (3):** Ulvenwald Observer (needs a toughness 4+ creature to die), Warden of the Woods (needs an opponent to target it), Rootgrapple (needs a Treefolk).

## Mechanics in this deck

Cheat sheet. Each line is one thing a new player may meet.

- **Trample:** if this creature is blocked, it assigns lethal damage to the blocker and the rest goes to the player. Dauntless Dourbark only has it while you control another Treefolk.
- **Reach:** this creature can block creatures with flying.
- **Vigilance:** attacking does not tap this creature, so it can still block next turn.
- **Hexproof:** opponents' spells and abilities can't target it. Dungrove Elder has it always; Blossoming Defense and Heroic Intervention give it until end of turn (Heroic Intervention is an instant, so hold {1}{G} open).
- **Indestructible:** damage and "destroy" effects don't kill it. Heroic Intervention gives it for a turn; Timber Protector gives it to your other Treefolk and your Forests.
- **Forestcycling {2}:** pay two and discard this card from your hand to search your library for a Forest card. Timberland Ancient only.
- **Quickbeam's trigger:** each time a Treefolk enters under your control, up to two target creatures get +2/+2 and trample until end of turn.
- **Number of Forests you control:** counts every Forest on your side, so the trees grow with each land drop.
- **Pump, "until end of turn":** a temporary size boost that wears off at end of turn. The creature keeps damage already dealt. Overwhelming Stampede gives +X/+X, where X is the biggest power among your creatures, so check the board first.
- **Mana creature:** a creature with "{T}: Add mana". It can't tap the turn it arrives (summoning sickness), so cast it a turn early.
- **Aura (Wild Growth, Overgrowth, Lignify):** an enchantment you attach to something when it enters. If the thing leaves, the Aura goes too. The two mana Auras go on a land and add extra mana when that land is tapped.
- **Fetch spells (Nature's Lore, Three Visits, Skyshroud Claim, Rampant Growth, Cultivate):** search your library for land cards, put them where it says, then shuffle. Rampant Growth and Cultivate put the land onto the battlefield tapped. The others put it in untapped. Wood Elves does the same thing when it enters.
- **Bite ("deals damage equal to its power"):** your creature hits the other creature and takes no damage back. Ram Through also sends extra damage to the player if your creature has trample.
- **Anthem or lord (Timber Protector):** a permanent that gives other creatures +1/+1 for as long as it stays in play. Crabapple Cohort is different: it only boosts itself, +1/+1 while you control another green creature.
- **Draw triggers:** Elemental Bond and Garruk's Packleader draw when a creature with power 3 or more enters under your control. Beast Whisperer draws when you cast a creature spell. Colossal Majesty draws at the start of your upkeep if you control a creature with power 4 or more. Each one repeats for as long as the permanent stays in play.
- **Ferocious (Shamanic Revelation):** a bonus that turns on if you control a creature with power 4 or greater.
- **Untap (Shriekwood Devourer):** when you attack, it untaps up to X lands, where X is the biggest power among your attackers, so you can spend mana after combat. It is fine to ignore it.
- **Cost reduction (Bosk Banneret):** your Treefolk spells cost {1} less. It does not go below the colored mana in the cost.
- **Kindred:** a card type that gives a non-creature card a creature type. Rootgrapple and Lignify are Kindred Treefolk. Lignify stays on the battlefield, so it is a Treefolk you control: it triggers Quickbeam when it enters and counts for Dauntless Dourbark. Rootgrapple is an instant that never enters, so it does not trigger Quickbeam. This comes from reading the card text and the Kindred rule, since the tool has no ruling on Quickbeam.
- **"When this dies":** a trigger that happens when the creature goes to the graveyard from play. Seedguide Ash fetches Forests; Ulvenwald Observer draws a card when a toughness 4+ creature dies; Rootless Yew searches for a creature with power or toughness 6 or more and puts it in your hand (you show it to the table first).
- **Token:** a permanent that is not a card. Kalonian Twingrove makes one Treefolk token that grows with your Forests. If it leaves play it is gone for good.
- **"Choose one":** when you cast the spell, pick one of the listed modes. Only that one happens (Return of the Wildspeaker, Return to Nature).
- **You gain life:** your life total goes up (Orchard Warden, Mossbeard Ancient, Shamanic Revelation). It is not damage prevention.
- **"Whenever you cast" against "enters":** casting is putting a spell on the stack, before it resolves. Entering is arriving on the battlefield. Beast Whisperer and Battlewand Oak trigger on casting, so they fire even if the spell is countered. Quickbeam and Orchard Warden trigger on entering. Rootgrapple and Lignify both count as cast Treefolk spells for Battlewand Oak.
- **"Can block an additional creature":** Ghastbark Twins can block two attackers in one combat instead of one.

## Cut and why

Nothing was cut for price. The first list came in at $66.50 and the reviewed list is $72.25, so the cap never bit. Three Visits ($5.55) was first left out for its price, then brought in because it puts a Forest on the battlefield and the deck sits far under the cap. The review swaps are the last five rows.

| Card | Price | Why it is out |
|---|---|---|
| Fangorn, Tree Shepherd | $0.36 | Three abilities, and mana that stays after phases end. Brief said "if it passes". It doesn't. |
| Verdeloth the Ancient | $0.21 | Kicker plus Saproling tokens plus a lord effect. Brief said "if it passes". It doesn't. |
| Generous Ent, Orchard Strider | $1.19, $0.13 | Forest or land cycling plus Food tokens. Timberland Ancient fills that slot with fewer words. |
| Gnarled Professor | $0.08 | 5/4 trample for four, but Learn is a new mechanic. |
| Cradle Guard | $0.17 | Echo is a new mechanic and a cost to pay every time. |
| Yavimaya Scion | $0.20 | Protection from artifacts needs a definition for little gain. Redwood Treefolk took the slot. |
| Wickerbough Elder | $0.13 | A counter and an activated ability to destroy an artifact or enchantment. Return to Nature and Reclamation Sage do the job. |
| Weatherseed Treefolk, Reach of Branches | $1.38, $0.34 | Both return from the dead, which is on the Avoid list. |
| Unstoppable Ash, Sheltering Ancient | $1.13, $1.76 | Champion and cumulative upkeep both punish you or help opponents. |
| Garruk's Uprising | $0.39 | Three abilities. Elemental Bond and Colossal Majesty draw cleanly. |
| Naturalize | $0.06 | Swapped for Return to Nature, which also covers the baseline's one graveyard hate card. |
| Utopia Sprawl | $1.33 | Same job as Wild Growth, with an extra color choice. |
| Arbor Elf | $0.39 | Review swap. Says "Untap target Forest" instead of "Add {G}", a second kind of mana creature. Three Visits took the slot. |
| Arcane Signet | $0.38 | Review swap. Mana rocks are not on the brief's Wanted ramp list. Wood Elves fetches a Forest instead. |
| Rowan Treefolk | $0.12 | Review swap. A blank 3/4. It became the 38th Forest. |
| Overcome | $0.07 | Review swap. A weaker Overrun (+2/+2 against +3/+3). Overwhelming Stampede ends games better. |
| Ironroot Treefolk | $0.17 | Review swap. A blank 3/5. Rootless Yew is a 5/4 for the same cost that fetches a big creature when it dies. |

Left out by the brief and banned in the rules file: Six, Yedora, Kurbis, Ferrafor, Harold and Bob.

## One card away from an infinite combo

The check lists one: **Umbral Mantle** with **Llanowar Tribe** (Equip {0}, and tapping the Tribe for {G}{G}{G} pays the Mantle's {3} and untaps it, so each loop nets zero mana and gives the Tribe +2/+2, which is infinite power). Umbral Mantle is not in the deck. Keep it out while the brief forbids infinite combos.

The check shows no warnings. One rule is worth knowing: the broad `tax` tag flags Warden of the Woods, which only draws when an opponent targets it. It is not a tax, so the rules file allows that one card (`tax = 1`) and limits `tax-attack`, `cast-tax` and `lockdown` to 0.

## Decisions the brief did not cover

- **38 basic Forests and no utility land at all.** The brief said "nearly all". No utility land I found was both simple and useful enough to replace a Forest, and lands like Command Tower do nothing in one color.
- **38 lands, not 39 or 40.** The deck averages 3.6 mana value, above the baseline's 2.8 to 3.3, and the land formula suggests about 39. Rowan Treefolk became the 38th Forest, and 15 ramp cards (12 is the baseline) cover the rest of the gap.
- **Zero board wipes**, though the brief allowed one.
- **"Other creatures" is empty.** Every non-Treefolk creature is ramp, draw or removal and sits under its role in "Cards by role".
- **Heroic Intervention ($9.24) stayed** as the only answer to a board wipe. It is an instant, so keep {1}{G} open and cast it in response to the wipe. Timber Protector ($22.94) stayed as the one Treefolk lord. Both fit easily under the cap.
- **Lignify is in as removal.** It turns an opposing creature into a 0/4 with no abilities. Lignify itself is a Kindred Treefolk Aura that you control, so it triggers Quickbeam when it enters and counts as a Treefolk for Dauntless Dourbark. This comes from reading the card text and the Kindred rule, since the tool has no ruling on Quickbeam. The enchanted creature becomes a Treefolk too, but not one you control, so it does nothing for you.
- **Rootgrapple can destroy a single land and stays.** The brief bans mass land destruction only, so one-target removal that can hit any noncreature permanent is fine.
- **Return of the Wildspeaker and Return to Nature are "choose one" cards.** They are readable and sit outside the Avoid list.
- **Overrun and Overwhelming Stampede overlap** (both team pump with trample). Two sorcery finishers means a second one is there if the first is stuck at the bottom of the library.
- **Ram Through is a little wordier** than Bite Down. It stayed because Quickbeam gives trample often enough to use the extra text.
- **Two vanilla 5-drops** (Blanchwood and Redwood Treefolk) are in only as Quickbeam triggers and blockers. Swap them for better Treefolk if the brief changes.
- **Mana Auras are a risk.** If the land they enchant is destroyed, the Aura goes too. The list has only two.
- **Shriekwood Devourer** is a 7/5 trampler for seven. Its untap trigger is optional help: untap lands after attackers are declared and spend the mana after combat. If that sounds like too much, ignore it and attack.
- **Rootless Yew's death trigger** is a search to hand, not recursion. It fetches a creature with power or toughness 6 or more, such as Mossbeard Ancient or Ghastbark Twins.
- **Rules file additions:** a banned list for the brief's left-out cards, `tax` at 1 (Warden of the Woods only) and limits on `tax-attack`, `cast-tax` and `lockdown`, `tapland` at 0, a lands minimum of 37 (the deck has 38) and ramp at 15. Each departure has a comment in the file.
