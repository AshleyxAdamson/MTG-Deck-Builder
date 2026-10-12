# MTG Deck Builder

## Data

Card and rules data is downloaded on demand, not committed. Fetch it with:

```bash
python3 scripts/fetch_data.py
```

It needs Python 3.9+ and nothing else. Files land in `data/`, which is gitignored:

| Path | What it is | Source |
|---|---|---|
| `data/scryfall/oracle-cards.jsonl.gz` | One card object per line, one per unique card (Oracle ID) | Scryfall bulk data |
| `data/scryfall/rulings.jsonl.gz` | One ruling per line, joined to cards by `oracle_id` | Scryfall bulk data |
| `data/scryfall/catalogs/*.json` | Card names, keyword abilities, keyword actions, ability words, supertypes, card types, every subtype list, powers, toughnesses, loyalties | Scryfall `/catalog/*` |
| `data/scryfall/sets.json`, `symbology.json` | All sets; all mana and card symbols | Scryfall `/sets`, `/symbology` |
| `data/rules/comprehensive-rules.txt` | The Comprehensive Rules, byte for byte as published (UTF-8) | magic.wizards.com/en/rules |
| `data/manifest.json` | Source URL, version, fetch time, size and record count for each file | written by the script |

The bulk files stay gzipped. Read them a line at a time:

```python
import gzip, json

with gzip.open("data/scryfall/oracle-cards.jsonl.gz", "rt", encoding="utf-8") as cards:
    for line in cards:
        card = json.loads(line)
```

### Re-running

A second run only downloads what changed:

- Bulk files are skipped while Scryfall's `updated_at` matches the manifest (Scryfall rebuilds them about once a day).
- The Comprehensive Rules are skipped while the published file name, which carries the date, is unchanged.
- Catalogs, sets and symbology have no version stamp, so they are re-fetched once the local copy is over 24 hours old.

`--force` fetches regardless. `--only cards rulings catalogs rules` limits the run to the groups named.

### Network access

The script talks to `api.scryfall.com`, `data.scryfall.io`, `magic.wizards.com` and `media.wizards.com`. In a sandboxed environment all four need to be allowed.
