# The Vampire Plague (Elenda): notes

Decklist: `decks/vampire-plague-elenda.txt`. Brief: `decks/briefs/vampire-plague-elenda.md`. Rules: `decks/vampire-plague-elenda.rules.toml`.
The decklist pastes into Moxfield as is. Set the commander in Moxfield's commander slot.
A working list for review, not a locked one. Card facts and prices come from the local `mtg` tool (prices as of 2026-10-12, each card's cheapest paper printing).

Shape: 100 cards, $151.44. 37 lands, 11 ramp, 28 creatures (27 of them Vampires, counting Elenda), 3 planeswalkers. Average mana value of nonland cards is 3.02.

## How it plays

- **Go wide with lifelink bodies.** Mavren Fein, Legion's Landing, Sorin, Lord of Innistrad, March of the Canonized, Bloodline Keeper, Edgar's coffin and Elenda herself fill the board with Vampire tokens, most of them with lifelink. Teysa Karlov gives every token lifelink and vigilance.
- **Lords make the swarm a real clock.** Legion Lieutenant, Captivating Vampire, Edgar, Markov Baron, Bloodline Keeper (flipped), Etchings of the Chosen, Patchwork Banner, Vanquisher's Banner and Renewed Solidarity all reward Vampires.
- **Every death and every attack drains.** Blood Artist, Cruel Celebrant, Falkenrath Noble and Cordial Vampire trigger on deaths, and Teysa Karlov makes each of those trigger twice. Sanctum Seeker drains per attacking Vampire, and Vito turns all the lifelink into damage.
- **Elenda is the centrepiece.** She grows whenever any creature dies, then leaves behind that many lifelink Vampires. Viscera Seer, Bloodthrone Vampire, Bartolomé del Presidio and Yahenni are free sacrifice outlets to cash her in on your terms. Kaya, Geist Hunter's −2 doubles them for one turn.
- **Raise their dead.** Animate Dead, Rise from the Grave and Rise of the Dark Realms take creatures from any graveyard, as does Sorin, Lord of Innistrad's last ability.
- **Cards keep flowing** from Welcoming Vampire, Champion of Dusk, Clavileño, Twilight Prophet, Scheming Silvertongue, Skullclamp on 1/1 tokens, Vanquisher's Banner and Baron Bertram Graywater.

Opponents can see all of it coming: it is a creature board that loses to blockers, racing and a wrath. Unbreakable Formation, Clever Concealment and Duty Beyond Death save the board from a wrath, and Etchings of the Chosen protects one creature.

## Cards by role

- **Commander (1):** Elenda, the Dusk Rose
- **Ramp (11):** Sol Ring; Arcane Signet; Orzhov Signet; Talisman of Hierarchy; Mind Stone; Pillar of Origins; Patchwork Banner; Herald's Horn; Wayfarer's Bauble; Fellwar Stone; Charcoal Diamond
- **Card draw (7):** Welcoming Vampire; Champion of Dusk; Clavileño, First of the Blessed; Twilight Prophet; Scheming Silvertongue; Skullclamp; Vanquisher's Banner
- **Removal (7 spot removal + 2 board wipes):** Swords to Plowshares; Path to Exile; Anguished Unmaking; Vindicate; Mortify; Despark; Generous Gift
- **Protection (3):** Unbreakable Formation; Clever Concealment; Duty Beyond Death
- **Board wipes (2 of the 2 allowed):** Kindred Dominance; Olivia's Wrath
- **Raise-their-dead package (3, plus Sorin, Lord of Innistrad's last ability):** Animate Dead; Rise from the Grave; Rise of the Dark Realms
- **Lords and anthems (6):** Legion Lieutenant; Captivating Vampire; Edgar, Charmed Groom; Markov Baron; Bloodline Keeper; Etchings of the Chosen
- **Vampires: token makers, sacrifice outlets, lifelink (9):** Mavren Fein, Dusk Apostle; Elenda's Hierophant; Baron Bertram Graywater; Bartolomé del Presidio; Yahenni, Undying Partisan; Carmen, Cruel Skymarcher; Viscera Seer; Bloodthrone Vampire; Henrika Domnathi
- **Payoffs: drain and death triggers (8):** Blood Artist; Cruel Celebrant; Falkenrath Noble; Sanctum Seeker; Cordial Vampire; Vito, Thorn of the Dusk Rose; Malakir Bloodwitch; Teysa Karlov
- **Tokens and token multipliers (6):** Legion's Landing; Sorin, Lord of Innistrad; Sorin, Imperious Bloodlord; March of the Canonized; Kaya, Geist Hunter; Renewed Solidarity
- **Lands (37):** Command Tower; Godless Shrine; Vault of Champions; Bleachbone Verge; Brightclimb Pathway; Path of Ancestry; Exotic Orchard; Isolated Chapel; Caves of Koilos; Shattered Sanctum; Concealed Courtyard; Fetid Heath; Tainted Field; Shineshadow Snarl; Temple of Silence; Bojuka Bog; Orzhov Basilica; Unclaimed Territory; Voldaren Estate; Vault of the Archangel; 11 Swamp; 6 Plains

## Brief compliance

| Constraint | Status |
|---|---|
| Commander | Elenda, the Dusk Rose |
| White-black only | `mtg check` reports no off-identity cards. Stromkirk Captain (black-red) is out. |
| Commander-legal | `mtg check` reports no illegal cards and no game changers. |
| Budget ~$150 | $151.44. The spells cost $112.63; the other $38.81 is four dual lands (Godless Shrine, Vault of Champions, Bleachbone Verge, Brightclimb Pathway). The rules file's budget is still $185 from before Ojer Taq came out. |
| Board wipes: at most two | Exactly two, both one-sided for a Vampire board: Kindred Dominance and Olivia's Wrath. |
| Sanguine Bond / Exquisite Blood | Neither is in the deck. |
| No infinite combos | No known combo in the deck (Commander Spellbook data). See "One card away" below for what to keep out. |
| No stax or tax | None by reading. Left out: Drana and Linvala, Anowon, Charismatic Conqueror, Tergrid, Butcher of Malakir. |
| Baseline for a casual deck | Meets the minimums in the rules file: lands, ramp, card advantage, removal, protection, graveyard hate. |

## What changed from the first draft

- **From EDHREC's 610 Elenda vampire decks:** Bartolomé del Presidio, Yahenni, Teysa Karlov, Carmen, Clavileño, March of the Canonized and Etchings of the Chosen came in. All cost under $2.50.
- **From corrected prices:** the first draft was priced from each card's newest printing, which overstated it by about $30. That room went to Ojer Taq, the brief's token tripler (since cut, see below).
- **From the deck-building baseline:** a 37th land, Wayfarer's Bauble, Unbreakable Formation, Bojuka Bog for graveyard hate, and basics moved to 13 Swamp and 8 Plains because the deck has about twice as many black mana symbols as white.
- **From a scan against the baseline:** ramp was at 8 real cards against a target of 10 to 12, protection at 2 against about 4 for a go-wide deck, and 11 cards shared Elenda's cost of four. Fellwar Stone, Charcoal Diamond and Clever Concealment replaced Vampire Nocturnus, Wispdrinker Vampire and Beacon of Unrest.
- **For a little more protection:** Duty Beyond Death replaced Indulging Patrician. Its sacrifice also triggers Elenda and the death payoffs.
- **Better mana, over budget by choice:** Godless Shrine, Vault of Champions, Bleachbone Verge and Brightclimb Pathway replaced two Swamps and two Plains. All four enter untapped in a normal game. Land sources are now 30 black and 24 white.
- **Toned down:** Kaya, Geist Hunter replaced Ojer Taq, Deepest Foundation. Ojer Taq tripled every token for as long as it stayed out and came back as a land when it died, which was too strong for this table. Kaya doubles tokens for one turn at a cost of 2 loyalty, so opponents see it coming and can attack her down.
- **Out earlier:** Call to the Feast; Martyr of Dusk; Vampire Nighthawk; Dusk Legion Zealot; Sepulchral Primordial; Debtors' Knell; Preacher of the Schism; Thirsting Bloodlord; Crossway Troublemakers; Pact of the Serpent; Scoured Barrens.

## Left out for budget

| Card | Price | Note |
|---|---|---|
| Anointed Procession | $57.08 | Token doubler |
| Ojer Taq, Deepest Foundation | $32.09 | Token tripler. Cut for power, not price |
| Mondrak, Glory Dominus | $41.79 | Token doubler |
| Exquisite Blood | $39.31 | Also an infinite combo with Vito |
| Tergrid, God of Fright | $18.00 | Also a game changer and a feel-bad card |
| Coat of Arms | $12.44 | Helps opposing tribes too |
| Reanimate | $6.63 | The first card to add back if the budget moves |
| Sanguine Bond | $5.43 | Vito does the same job on a Vampire |

## One card away from an infinite combo

The checker lists these as completing a known combo with cards already in the deck. Keep them out while the brief forbids infinite combos: Exquisite Blood, Bloodthirsty Conqueror, Blood Tribute and Shard of the Nightbringer (each with Vito), and Abdel Adrian or Leonin Relic-Warder (each with Animate Dead).

## Decisions for the user

1. **Ojer Taq's $32 is unspent.** The deck is $151.44 against a $185 limit. Reanimate ($6.63) and Coat of Arms ($12.44) would both fit, or the limit can drop back to the brief's $150.
2. **Two wipes, not one.** If you would rather have one, cut Olivia's Wrath for another Vampire.
3. **Vito in, Sanguine Bond out.** Same effect, and Vito is a Vampire.
4. **Captivating Vampire is here as a lord.** It can also steal a creature by tapping five Vampires; the steal theme was dropped, so say if you want it gone.
5. **Vampire Nocturnus is out**, though the brief names it: it needs triple black on turn four, which this mana base gives unreliably, and its bonus is on under half the time.
6. **Bojuka Bog** exiles one player's graveyard, which works against the raise-their-dead package if aimed at the wrong player. Kaya's −6 is the only other graveyard hate.
7. **The raise-their-dead package is three spells** plus Sorin and Carmen. Beacon of Unrest made way for a second board-wide protection spell.
8. **Popular cards left out for table feel:** Butcher of Malakir (forces sacrifices), Blade of the Bloodchief with the Altars (combo with Elenda).
9. **Kaya's −6 exiles every graveyard**, including the ones the raise-their-dead package wants. It is optional and takes four turns to reach.
