# Upscale spike: Upscayl models on Scryfall scans

**Recommendation: default `ultrasharp-4x`.** It is the only model that makes the rules text and the copyright line crisper than the source without painting over the card, and its halftone amplification is mild at 800 dpi. `high-fidelity-4x` is the safer per-card override for grainy 2003-frame scans, since it invents the least but leaves text greyer and softer.

## Images

| Image | Card | Frame | Scryfall status | PNG size |
|---|---|---|---|---|
| c21-187 | Cultivate, Commander 2021 | 2015 | highres_scan | 745x1040 |
| m11-168 | Cultivate, Magic 2011 | 2003 | highres_scan | 745x1040 |
| tdc-253 | Cultivate, Tarkir: Dragonstorm Commander | 2015 | lowres | 745x1040 |

Scryfall serves the `lowres` card at the same 745x1040, so the flag cannot be read from the pixel size. The tdc-253 text is smooth and digital-looking, with no halftone.

## Numbers

Rules-text region (bottom 40% of the trimmed card). Sharpness is the variance of the FIND_EDGES grayscale image; the 800 dpi crop is shrunk to the original crop size first, so before and after compare like with like. Colour shift is mean diff (0..255) / PSNR dB for the whole card, against the filled original. Native 4x output was 2980x4160 for every run. Seconds is the whole `prepare()` call on the M5 Max, which includes encoding the 2176x2960 PNG.

| Image | Model | Seconds | Colour shift | ok | Sharpness before | after |
|---|---|---|---|---|---|---|
| c21-187 | Lanczos baseline | 2.4 | 0.01 / 43.0 | yes | 4520 | 4483 |
| c21-187 | ultrasharp-4x | 15.6 first, 10.8 second | 1.02 / 32.2 | yes | 4520 | 4866 |
| c21-187 | digital-art-4x | 8.0 | 2.04 / 28.1 | yes | 4520 | 4997 |
| c21-187 | high-fidelity-4x | 10.9 | 0.76 / 30.4 | yes | 4520 | 4112 |
| m11-168 | Lanczos baseline | 2.1 | 0.02 / 38.7 | yes | 5123 | 4985 |
| m11-168 | ultrasharp-4x | 10.6 | 1.86 / 32.2 | yes | 5123 | 5224 |
| m11-168 | digital-art-4x | 7.8 | 1.90 / 25.2 | no | 5123 | 5049 |
| m11-168 | high-fidelity-4x | 10.7 | 1.16 / 26.0 | no | 5123 | 3719 |
| tdc-253 | Lanczos baseline | 2.4 | 0.03 / 49.8 | yes | 4380 | 4483 |
| tdc-253 | ultrasharp-4x | 10.1 | 0.51 / 27.8 | no | 4380 | 5177 |
| tdc-253 | digital-art-4x | 7.4 | 1.55 / 27.0 | no | 4380 | 5321 |
| tdc-253 | high-fidelity-4x | 11.4 | 0.51 / 29.6 | yes | 4380 | 4241 |

Speed: the first ever run took 15.6 s and a rerun of the same input 10.8 s, so shader compile costs about 5 s once. A deck of 20 upscales is about 3.5 minutes. Nothing came near the 5-minute cut-off.

Colour: mean diff stays under 2.1 on every run, so no model shifts the overall colour. The six PSNR failures come from edge sharpening and grain smoothing, which PSNR counts as error. For models that sharpen, the PSNR floor of 28 is too strict. Use mean diff as the gate and a PSNR floor near 24 as a catch for wrecked output.

## Visual notes (full 800 dpi crops, `data/spike/`)

- **ultrasharp-4x.** Text is crisp and a little bolder and darker than the source. Letterforms are right, with no invented strokes and no mutated words, in the rules, the italic flavour text and the copyright line ("1993-2010 Wizards of the Coast LLC 168/249" stays legible, as does the collector line on the modern frames). It leaves a faint embossed edge around letters and amplifies the halftone grain in the m11-168 frame and rules box (visibly speckled), and adds stipple to the frame on c21-187. No ringing worth the name.
- **digital-art-4x.** Smoothest and cleanest at first glance, but it puts a light halo or glow around every letter (clearest on tdc-253), erases the card's texture, and on m11-168 repaints the frame and art area into smooth, slightly invented shapes. The copyright line is readable. The worst colour shift (2.04) and two PSNR failures.
- **high-fidelity-4x.** Most faithful: texture is kept, grain is smoothed rather than amplified, and there are no halos. Text is greyer and thinner than the source, which is why sharpness drops below the original (3719 vs 5123 on m11-168). Legible everywhere, including the copyright line, but soft.
- **Lanczos baseline.** Soft but honest, with halftone and text edges exactly as scanned.

No model hallucinated text or changed a word on these three cards. Small print on other frames (planeswalker loyalty, tiny reminder text, foreign text) was not tested.

## Why ultrasharp

Print at 800 dpi is judged on text edges. ultrasharp is the only model that raises sharpness on all three cards without a halo, and its grain amplification is milder than the paint-over of digital-art. On a grainy scan like m11-168, `high-fidelity-4x` is the better choice; the model is already a per-card print-file setting. Not tested: the text-safe composite, 1x descreen models and `RealESRGAN_MtG`.

## Commands

```bash
cd /Users/gxa/work/MTG-Deck-Builder/.worktrees/print-suite-spec
# Scryfall PNGs, 1 request per second, User-Agent "mtg-deck-builder/0.1 (+https://github.com/AshleyxAdamson/MTG-Deck-Builder)", Accept */*:
#   https://api.scryfall.com/cards/{c21/187,m11/168,tdc/253}?format=image&version=png
uv run python -c "
from pathlib import Path
from mtg_deck_builder.printing.prepare import prepare
for model in ['ultrasharp-4x', 'digital-art-4x', 'high-fidelity-4x']:
    print(prepare(Path('m11-168.png'), 'scryfall', model=model, force=True))
print(prepare(Path('m11-168.png'), 'scryfall', engine='none', force=True))  # Lanczos baseline
"
```

Outputs land in `data/art/prepared/`. Crops and full images are `data/spike/<image>-<model>-text.png` and `-full.png`.

**How this was checked:** three Scryfall PNGs run through `prepare()` with the real `upscayl-bin` (from `data/upscayl/`) on the M5 Max, 2026-10-18; sharpness, colour shift and timings come from the code; all nine model crops and the three baseline crops were viewed at full size.
