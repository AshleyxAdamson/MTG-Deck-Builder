# Agent Guidelines

<!-- pebbl:begin -->
## Pebbl — Memory

Local CLI for project memory. Flag details: `pebbl <cmd> --help`. Concepts: `pebbl help <topic>` (categories, tiers, compaction, file-layout, entry-ids).

**Every session, before code:** `pebbl context` (read open handoff + recent decisions). An open handoff's `done` field is what the *previous* agent finished — don't claim it as your own. The `todo` field is what's left for you. Close the handoff with `pebbl handoff --close` when you complete the remaining work.

**Before any non-trivial decision:** `pebbl search "<area>"` — don't re-litigate prior choices.

**Log the moment a decision or failed approach lands.** Always include `--cat` and `--topic`. Always explain *why*, not just *what* — entries without rationale get auto-demoted.

```bash
pebbl log "chose bcrypt over argon2 because team already operates bcrypt in prod" --cat decision --topic auth
```

**End of session:** `pebbl handoff "<summary>" --done "a; b" --todo "c; d" --topic <area>`. Use `;` to split atomic items — one run-on becomes one unsearchable blob.

**A detail-heavy handoff needs a rendered doc.** When the end-of-session detail is large, write it to a readable file (e.g. `docs/handoffs/<topic>.md`) and link it with `--docs <path>` — the fields are for searchable one-liners, the doc is the readable detail. pebbl REFUSES a detail-heavy handoff that links neither `--docs` nor `--no-doc`, so the rendered doc reliably gets made instead of the detail being crammed into the fields or written somewhere and never linked. The linked doc resurfaces on `pebbl context`.

**Don't log:** routine code changes (the git hook captures commits), or anything obvious from reading the code.
<!-- pebbl:end -->
