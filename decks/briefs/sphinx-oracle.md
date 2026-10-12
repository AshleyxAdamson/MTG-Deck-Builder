# Deck Build Brief: The Sphinx Oracle

## Task
Build a 100-card Commander deck (Magic: The Gathering) from the decisions below. **Resolve the commander issue with the user first** (see next section).

## ⚠️ Open issue: commander color identity
The plan was Esper (W/U/B) with **Unesh, Criosphinx Sovereign** as commander. Verified card text:

- Unesh is **mono-blue** ({4}{U}{U}, 4/4 flying). Its color identity is blue only, so a Unesh deck **cannot** run white or black cards.
- Ability: Sphinx spells cost {2} less. Whenever Unesh or another Sphinx **enters** under your control, reveal the top four cards; an opponent separates them into two piles; you put one in hand and the other in the graveyard. (It triggers on entering, not on combat damage.)

Ask the user to choose:
- **A. Keep Unesh, go mono-blue.** Keeps the "opponent splits the pile" gimmick. Loses Esper.
- **B. Stay Esper with an Esper sphinx commander.** Candidates to verify: Sharuum the Hegemon, Tivit, Seller of Secrets. Unesh can still go in the 99 only if the commander's identity includes blue (it does for Esper), but its cost reduction then only matters while it is on the battlefield.

Do not start the list until this is settled.

## Locked decisions
| Item | Decision |
|---|---|
| Archetype | Sphinx tribal, "fortune-teller" flavor |
| Colors | Esper (W/U/B) preferred, pending commander decision above |
| Budget | ~$150 total |
| Table | Casual, quirky, mysterious, not feel-bad |
| Infinite combos | None |

## Theme and vibe
The user is the mysterious oracle at the table, not the tyrant.

- **Engine:** self-focused card selection: scry, surveil, look at / play from the top of the library, card draw.
- **Payoff and finishers:** big evasive sphinxes.
- **Seasoning only:** occasional peeks at opponents' libraries (fateseal-style). Not the plan.
- **Social moments are a feature:** effects that hand opponents a choice (like Unesh's pile split) are on-brand.

## Feel-good guardrails (important)
- Light, **reactive** control only: a thin layer of counters and spot removal as a safety net. Do **not** optimize for control.
- No stax, tax effects, or "you can't play the game" pieces.
- Board wipes: one or two at most.
- No infinite combos.
- Prefer proactive, splashy plays.

## Notes
- Sphinxes are a small tribe. Expect "all the genuinely good sphinxes in the colors, plus a fortune-teller support shell." Do not pad with weak sphinxes just for count.
- Raffine, Scheming Seer was considered and **rejected** as too competitive.
- Yennett, Cryptic Sovereign was considered and **rejected** (user didn't find the odd-mana-value plan fun).

## Deliverables
1. Commander decision confirmed with the user.
2. Full 100-card list grouped by role: commander, ramp, card draw / selection, light interaction, sphinxes, top-of-library payoffs, lands.
3. Short explanation of the key synergies.
4. Legality and color-identity confirmation for every card.
5. Approximate total price, staying near $150.

## Tooling
Use Scryfall (bulk data or search API) rather than memory. Starting queries: `t:sphinx id:wub legal:commander` (Esper) or `t:sphinx id:u legal:commander` (mono-blue).
