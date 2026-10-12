# The Vampire Plague (Elenda): draft notes

Draft for review, not a final list. Decklist: `decks/vampire-plague-elenda.txt`. Brief: `decks/briefs/vampire-plague-elenda.md`.
All card facts and prices come from the local `mtg` tool (price snapshot 2026-10-12).

Shape: 100 cards. 36 lands, 8 mana rocks, 33 creatures (32 of them Vampires, counting Elenda), 3 planeswalkers. Average mana value of nonland cards is 3.3.

## How it plays

- **Go wide with lifelink bodies.** Mavren Fein, Legion's Landing, Sorin, Lord of Innistrad, Call to the Feast, Bloodline Keeper, Edgar's coffin and Elenda herself fill the board with Vampire tokens, most of them with lifelink.
- **Lords make the swarm a real clock.** Legion Lieutenant, Captivating Vampire, Edgar, Markov Baron, Thirsting Bloodlord, Bloodline Keeper (flipped), Vampire Nocturnus, plus Patchwork Banner, Vanquisher's Banner and Renewed Solidarity all name or reward Vampires.
- **Every death and every attack drains.** Blood Artist, Cruel Celebrant, Falkenrath Noble and Cordial Vampire trigger on deaths. Sanctum Seeker drains per attacking Vampire. Wispdrinker Vampire drains for each small creature entering (every token). Vito turns all the lifelink into damage, and Malakir Bloodwitch drains for the Vampire count.
- **Elenda is the centrepiece.** She grows whenever any creature dies, then leaves behind that many lifelink Vampires. Viscera Seer and Bloodthrone Vampire are free sacrifice outlets to cash her in on your terms. Kaya, Geist Hunter (-2) doubles the tokens for a turn, and Renewed Solidarity copies every Vampire token that entered that turn.
- **Raise their dead.** Animate Dead, Rise from the Grave, Beacon of Unrest, Debtors' Knell, Sepulchral Primordial and Rise of the Dark Realms all take creatures from any graveyard. Sorin, Lord of Innistrad's -6 does it too.
- **Cards keep flowing** from Welcoming Vampire, Champion of Dusk, Twilight Prophet, Skullclamp on 1/1 tokens, Vanquisher's Banner, Pact of the Serpent (naming Vampire), Scheming Silvertongue, Herald's Horn and Crossway Troublemakers.

Opponents can see all of it coming: it is a creature board that loses to blockers, racing and a wrath.

## Brief compliance

| Constraint | Status |
|---|---|
| Commander | Elenda, the Dusk Rose |
| White-black only, no red or blue | `mtg check` reports no off-identity cards. Stromkirk Captain (black-red) is out. |
| Commander-legal | `mtg check` reports no illegal cards. None is flagged as a game changer by the tool. |
| Budget ~$150 | **$142.27** by the tool's prices. Three nonbasic cards have no price in the tool (see Decisions). |
| Board wipes: at most two | Exactly two: **Kindred Dominance** (naming Vampire) and **Olivia's Wrath**. Both leave my Vampires alone. No other mass removal is in the list. |
| Sanguine Bond / Exquisite Blood | **Neither is in the deck.** Vito, Thorn of the Dusk Rose is the only "gain life, opponent loses that much" effect, and nothing in the list gains life from opponents' life loss, so that loop can't be assembled. |
| No infinite combos | None that I can find from the card texts. Dusk Legion Sergeant was left out on purpose (see Decisions). |
| No stax or tax | None. Left out: Drana and Linvala, Anowon, the Ruin Sage, Charismatic Conqueror, Tergrid, Paladin Class. |
| 100 cards, singleton | Confirmed by `mtg check`. |

Brief priorities: 32 Vampires (1), 7 lords plus 3 kindred anthems (2), 11 token sources plus 2 budget multipliers (3), lifelink on most tokens and several creatures plus Crossway Troublemakers and Vault of the Archangel (4), 8 drain payoffs (5), 6-card raise-their-dead package (6), 16 nonbasic lands with 12 that make both colours (7).

## Cut for budget

From the brief:

| Card | Price | Note |
|---|---|---|
| Anointed Procession | $57.08 | Token doubler |
| Mondrak, Glory Dominus | $47.20 | Token doubler |
| Exquisite Blood | $40.65 | Also excluded by the loop rule while Vito is in |
| Ojer Taq, Deepest Foundation | $32.09 | Token tripler. The best splurge if you raise the budget |
| Tergrid, God of Fright | $19.88 | Also a feel-bad card for a casual table |
| Coat of Arms | $19.06 | Helps opposing tribes too |
| Reanimate | $10.05 | Rise from the Grave and Beacon of Unrest cover it at $0.23 and $0.30 |
| Sanguine Bond | $8.16 | Vito ($9.52) does the same job on a Vampire. Could replace or join Vito; never alongside Exquisite Blood |

Obvious includes that were not in the brief:

| Card | Price | Note |
|---|---|---|
| Cavern of Souls | $51.60 | |
| Elspeth, Storm Slayer | $44.70 | Token doubler |
| Bloodthirsty Conqueror | $37.79 | Also loops with Vito, so leave it out regardless |
| Bloodletter of Aclazotz | $36.26 | |
| Charismatic Conqueror | $23.86 | Also tax-like |
| Exalted Sunborn | $20.44 | Token doubler |
| Vault of Champions | $16.71 | Dual land |
| Night's Whisper | $6.37 | Tool price looks high for this card |
| Wayfarer's Bauble | $5.79 | Tool price looks high for this card |
| Brightclimb Pathway | $4.87 | Dual land |
| Castle Locthwain | $4.31 | |
| Godless Shrine | no price in tool | Left out because its cost can't be counted |

## Decisions for the user

1. **Two wipes, not one.** I used both slots (Kindred Dominance, Olivia's Wrath). If you'd rather have one, cut Olivia's Wrath for another Vampire.
2. **Vito in, Sanguine Bond out.** Same effect, Vito is a Vampire. Say if you want both.
3. **Token multipliers are budget ones.** Kaya, Geist Hunter ($0.35) and Renewed Solidarity ($4.61) stand in for the $32 to $57 doublers. I chose more Vampires and lords (priorities 1 and 2) over one big doubler (priority 3).
4. **Dusk Legion Sergeant left out.** It gives nontoken Vampires persist; with Cordial Vampire's +1/+1 counters and a free sacrifice outlet that looks like an infinite loop. This is my reading of the card texts; the tool can't check combos.
5. **Nothing that exiles opponents' dead creatures.** Kalitas, Traitor of Ghet, Patron of the Vein and Bojuka Bog all fight the raise-their-dead package, so they're out.
6. **Wipe-like creatures left out** so the wipe count stays honest: Bringer of the Last Gift, Amalia Benavides Aguirre, Butcher of Malakir.
7. **Captivating Vampire is here as a lord.** It can also steal a creature by tapping five Vampires. The steal theme was dropped, so tell me if you want it gone (Death-Priest of Myrkul, $0.27, is a non-Vampire lord that could replace it).
8. **Vampire Nocturnus is a gamble.** 44 of the 99 library cards are black, so its bonus is on a bit under half the time. It's $5.95; it's in because the brief named it.
9. **Unpriced cards.** Mind Stone, Path of Ancestry and Exotic Orchard have no price in the tool and count as $0 in the total, as do the basics. There is $7.73 of headroom to absorb them. The tool can't tell me what they cost.
10. **Mana base.** 36 lands (11 Swamp, 9 Plains, 16 nonbasic) plus Legion's Landing and 8 rocks. Black is weighted heavier because of BB and BBB costs. Go to 37 lands by cutting Pillar of Origins if you prefer.
11. **Reanimation package is 6 cards.** The brief said small. Ghouls' Night Out ($0.42) and Necromantic Summons ($0.20) are easy adds if you want more.
12. **Removal is on the light side:** 7 spot removal spells plus the 2 wipes, with Sorin, Imperious Bloodlord and Henrika's one-time sacrifice as extras. Utter End ($0.30) and Go for the Throat ($0.63) are the next in.

## Checker output

```
$ uv run mtg check decks/vampire-plague-elenda.txt --commander "Elenda, the Dusk Rose"
Elenda, the Dusk Rose  [WB]  100 cards
  Deck is valid.
  Total $142.27 (prices as of 2026-10-12)
    $   9.52  Vito, Thorn of the Dusk Rose
    $   9.23  Bloodline Keeper // Lord of Lineage
    $   7.46  Animate Dead
    $   6.16  Rise of the Dark Realms
    $   5.98  Sorin, Imperious Bloodlord
    $   5.95  Vampire Nocturnus
    $   5.54  Elenda, the Dusk Rose
    $   5.42  Herald's Horn
    $   5.00  Skullclamp
    $   4.86  Vanquisher's Banner
  No price for: Mind Stone, Path of Ancestry, Exotic Orchard, Swamp, Plains
```
