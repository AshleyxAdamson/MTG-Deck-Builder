# Deck Build Brief: The Vampire Plague (Elenda)

## Task
Build a 100-card Commander deck (Magic: The Gathering) from the decisions below. Ask the user before locking in anything not covered here.

## Locked decisions
| Item | Decision |
|---|---|
| Commander | Elenda, the Dusk Rose |
| Colors | White-black (Orzhov) only |
| Budget | ~$150 total |
| Table | Casual, feel-good, not cutthroat |
| Infinite combos | None |

## Hard constraints
- **No red. No blue.** Do not splash either.
- **Do not include both Sanguine Bond and Exquisite Blood.** Individual drain payoffs are fine; the two-card infinite loop is not.
- **Board wipes: one or two at most.**
- Every card must be Commander-legal (check the current ban list) and within Elenda's W/B color identity.

## Theme and vibe
"The Vampire Plague," feel-good version. A vampire tribal swarm: go wide, lifelink, drain the table.

- The fun comes from **my board doing visible, splashy things**, not from stopping opponents from playing.
- Opponents should be able to see the threat building and respond (block, race, wrath). Fair counterplay is intended.
- "Plague" flavor = **raising opponents' dead** (a modest reanimation package that targets any graveyard) plus tokens and drain.
- The steal / mind-control theme was **dropped** (it depended on red).

## Priorities
1. Lots of vampires and real tribal synergy
2. Lords and anthems
3. Token makers and token doublers
4. Lifelink
5. Drain payoffs (on death, on vampire ETB)
6. Small "raise their dead" reanimation package
7. Clean, consistent two-color mana base

## Cards already discussed (W/B-legal candidates, verify each)
- **Tokens / multipliers:** Bloodline Keeper, Legion's Landing, Mavren Fein, Sorin, Lord of Innistrad, Sorin, Imperious Bloodlord, Ojer Taq, Deepest Foundation, Anointed Procession, Mondrak, Glory Dominus
- **Lords / anthems:** Stromkirk Captain (check color identity), Legion Lieutenant (check color identity), Vampire Nocturnus, Coat of Arms
- **Drain / death payoffs:** Sanctum Seeker, Cordial Vampire, Falkenrath Noble (check color identity), Blood Artist, Vito
- **Card draw:** Welcoming Vampire, Champion of Dusk
- **Sac outlets:** Viscera Seer, Bloodthrone Vampire (check color identity)
- **Raise their dead:** Animate Dead, Reanimate, Rise from the Grave, Rise of the Dark Realms
- **Steal-adjacent (W/B-legal):** Captivating Vampire, Tergrid, God of Fright
- **Other:** Henrika Domnathi (mono-black, flying; flips to flying/deathtouch/lifelink team pump)
- **Finisher:** Kindred Dominance (naming Vampire) counts as a wipe; stay within the 1–2 wipe limit.

Several earlier candidates were red. Drop any card whose color identity includes red or blue.

## Deliverables
1. Full 100-card list grouped by role: commander, ramp, card draw, removal, "raise their dead" package, vampires, payoffs, lands.
2. Short explanation of the key synergies.
3. Legality and color-identity confirmation for every card.
4. Approximate total price, staying near $150.

## Tooling
Use Scryfall (bulk data or search API) rather than memory. Starting query: `t:vampire id:wb legal:commander`.
