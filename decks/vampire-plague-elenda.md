# The Vampire Plague (Elenda): notes

Decklist: `decks/vampire-plague-elenda.txt`. Brief: `decks/briefs/vampire-plague-elenda.md`. Rules: `decks/vampire-plague-elenda.rules.toml`.
A working list for review, not a locked one. Card facts and prices come from the local `mtg` tool (prices as of 2026-10-12, each card's cheapest paper printing).

Shape: 100 cards, $146.66. 37 lands, 9 ramp, 32 creatures (30 of them Vampires, counting Elenda), 2 planeswalkers. Average mana value of nonland cards is 3.16.

## How it plays

- **Go wide with lifelink bodies.** Mavren Fein, Legion's Landing, Sorin, Lord of Innistrad, March of the Canonized, Bloodline Keeper, Edgar's coffin and Elenda herself fill the board with Vampire tokens, most of them with lifelink. Teysa Karlov gives every token lifelink and vigilance.
- **Lords make the swarm a real clock.** Legion Lieutenant, Captivating Vampire, Edgar, Markov Baron, Bloodline Keeper (flipped), Vampire Nocturnus, Etchings of the Chosen, Patchwork Banner, Vanquisher's Banner and Renewed Solidarity all reward Vampires.
- **Every death and every attack drains.** Blood Artist, Cruel Celebrant, Falkenrath Noble and Cordial Vampire trigger on deaths, and Teysa Karlov makes each of those trigger twice. Sanctum Seeker drains per attacking Vampire, Wispdrinker Vampire per small creature entering, and Vito turns all the lifelink into damage.
- **Elenda is the centrepiece.** She grows whenever any creature dies, then leaves behind that many lifelink Vampires. Viscera Seer, Bloodthrone Vampire, Bartolomé del Presidio and Yahenni are free sacrifice outlets to cash her in on your terms. With Ojer Taq out, she leaves three times as many.
- **Raise their dead.** Animate Dead, Rise from the Grave, Beacon of Unrest and Rise of the Dark Realms take creatures from any graveyard, as does Sorin, Lord of Innistrad's last ability.
- **Cards keep flowing** from Welcoming Vampire, Champion of Dusk, Clavileño, Twilight Prophet, Scheming Silvertongue, Skullclamp on 1/1 tokens, Vanquisher's Banner and Baron Bertram Graywater.

Opponents can see all of it coming: it is a creature board that loses to blockers, racing and a wrath. Unbreakable Formation and Etchings of the Chosen are the only protection.

## Brief compliance

| Constraint | Status |
|---|---|
| Commander | Elenda, the Dusk Rose |
| White-black only | `mtg check` reports no off-identity cards. Stromkirk Captain (black-red) is out. |
| Commander-legal | `mtg check` reports no illegal cards and no game changers. |
| Budget ~$150 | $146.66. |
| Board wipes: at most two | Exactly two, both one-sided for a Vampire board: Kindred Dominance and Olivia's Wrath. |
| Sanguine Bond / Exquisite Blood | Neither is in the deck. |
| No infinite combos | No known combo in the deck (Commander Spellbook data). See "One card away" below for what to keep out. |
| No stax or tax | None by reading. Left out: Drana and Linvala, Anowon, Charismatic Conqueror, Tergrid, Butcher of Malakir. |
| Baseline for a casual deck | Meets the minimums in the rules file: lands, ramp, card advantage, removal, protection, graveyard hate. |

## What changed from the first draft

- **From EDHREC's 610 Elenda vampire decks:** Bartolomé del Presidio, Yahenni, Teysa Karlov, Carmen, Clavileño, March of the Canonized and Etchings of the Chosen came in. All cost under $2.50.
- **From corrected prices:** the first draft was priced from each card's newest printing, which overstated it by about $30. That room went to Ojer Taq, the brief's token tripler.
- **From the deck-building baseline:** a 37th land, Wayfarer's Bauble, Unbreakable Formation, Bojuka Bog for graveyard hate, and basics moved to 13 Swamp and 8 Plains because the deck has about twice as many black mana symbols as white.
- **Out:** Kaya, Geist Hunter; Call to the Feast; Martyr of Dusk; Vampire Nighthawk; Dusk Legion Zealot; Sepulchral Primordial; Debtors' Knell; Preacher of the Schism; Thirsting Bloodlord; Crossway Troublemakers; Pact of the Serpent; Scoured Barrens.

## Left out for budget

| Card | Price | Note |
|---|---|---|
| Anointed Procession | $57.08 | Token doubler |
| Mondrak, Glory Dominus | $41.79 | Token doubler |
| Exquisite Blood | $39.31 | Also an infinite combo with Vito |
| Tergrid, God of Fright | $18.00 | Also a game changer and a feel-bad card |
| Coat of Arms | $12.44 | Helps opposing tribes too |
| Godless Shrine | $8.41 | The best land upgrade |
| Reanimate | $6.63 | Beacon of Unrest covers it at $0.30 |
| Sanguine Bond | $5.43 | Vito does the same job on a Vampire |

## One card away from an infinite combo

The checker lists these as completing a known combo with cards already in the deck. Keep them out while the brief forbids infinite combos: Exquisite Blood, Bloodthirsty Conqueror, Blood Tribute and Shard of the Nightbringer (each with Vito), and Abdel Adrian or Leonin Relic-Warder (each with Animate Dead).

## Decisions for the user

1. **Ojer Taq is a fifth of the budget** ($32.09). Without it there is room for Reanimate, Godless Shrine and Coat of Arms together.
2. **Two wipes, not one.** If you would rather have one, cut Olivia's Wrath for another Vampire.
3. **Vito in, Sanguine Bond out.** Same effect, and Vito is a Vampire.
4. **Captivating Vampire is here as a lord.** It can also steal a creature by tapping five Vampires; the steal theme was dropped, so say if you want it gone.
5. **Vampire Nocturnus is a gamble**: its bonus is on only while the top card of the library is black, a little under half the time.
6. **Bojuka Bog** exiles one player's graveyard, which works against the raise-their-dead package if aimed at the wrong player. It is the deck's only graveyard hate.
7. **Protection is at the minimum** (two cards). A go-wide deck would usually want about four.
8. **Popular cards left out for table feel:** Butcher of Malakir (forces sacrifices), Blade of the Bloodchief with the Altars (combo with Elenda).
