# ADR-0011: SO 34S16O X3Sigma- N/F unification and incremental attribution — real MARVEL4.1 bootstrap rerun on corrected data

## Status

**Two-part finding, two different outcomes.**

1. **Merge test (supersedes `docs/adr/0005-so-34s16o-marvel4-bootstrap-empirical-test-past.md`): REJECTED for merging, unchanged verdict, dramatically better absolute numbers.** `03SaMcTh`'s N→F-converted connecting transition (`03SaMcTh.2`) still fails MARVEL4.1's own consistency check at essentially the same ratio as before (11.54, `VERY BAD` — ADR-0005 measured ≈11.5 on the buggy data), confirming this specific inconsistency is real and **not** an artifact of the now-fixed `22HeStLy` F-labeling bug. Worse, on corrected data, forcing `03SaMcTh` into the network actively **degrades** overall network quality by roughly 54x (55 → 2949 flagged lines) for **zero** connectivity gain (same 4906 levels merged or disconnected) — a much starker version of ADR-0005's "merging buys nothing" finding. **Final deliverable remains the disconnected/fallback network**, now promoted to `molecules/SO/reference_papers/34S-16O_MARVEL_states.txt` (4906 levels) / `34S-16O_MARVEL_trans.txt` (32678 transitions) — the prior (buggy-data) deliverable is archived as `_past.txt`.

2. **Incremental attribution (supersedes `docs/adr/0008-so-34s16o-22hestly-incremental-attribution-past.md` and `docs/adr/0009-so-34s16o-precision-ordered-attribution-past.md`): REVISED, not confirmed.** The ≈99.6%-attributed-to-`22HeStLy` finding **does not survive on corrected data**. `22HeStLy` is now **completely self-consistent** (0 flagged lines out of 32358 transitions, 0.00%) at every step of both incremental builds, including the final, fully-merged 12-source network. The entire ≈60%-badness / 99.6%-`22HeStLy`-attribution finding from ADR-0008/0009 was the F-labeling bug's own signature — spurious F1/F2/F3 mislabeling fabricated apparent combination-difference violations between physically distinct sublevels that were never actually the same energy level. On corrected data, the fully-merged 12-source (disconnected-`03SaMcTh`) network's tiny remaining badness (55 lines, 0.169% of 32618 main-component transitions) is attributable almost entirely to **`87BuLoHa`** (50 lines, 90.9% of the flagged set; 33.8% of its own 148 transitions) with small contributions from `74Ti` (4 lines, 40% of its own 10) and `82Ti` (1 line, 10% of its own 10) — sources ADR-0008 had already flagged as small, real, secondary concerns, now revealed as the *entire* remaining story rather than a 0.4% footnote to `22HeStLy`'s dominance.

## Context

This ADR follows `docs/agents/marvel4-bootstrap-runbook.md`. It reruns the exact prior study on 34S16O — ADR-0005's 3-attempt-plus-fallback merge test, ADR-0008's ascending-transaction-count 12-step incremental build, and ADR-0009's precision-ordered 12-step incremental build — on corrected input data, using `.scratch/so-34s16o-marvel_past/` (the prior run's working directory, read-only reference) as the template.

**Why this rerun was needed**: a bug was found and fixed in `molecules/SO/papers/parse_22hestly_lines.py` — it derived `F_upper`/`F_lower` from a wrong fixed Sigma→F formula instead of reading them directly from the source data file's own `branch` column digits (e.g. branch `P22ff` means F_upper=F2/F_lower=F2; the old code said F1/F1). The fix has been mechanically validated and reviewer-signed-off. Since F-label identity is exactly what MARVEL uses to group transitions onto a shared energy level, ADR-0008/0009's 99.6% finding was always a candidate artifact of this mislabeling rather than genuine `22HeStLy` measurement error — this rerun answers that question directly, and, separately, re-checks whether the (structurally unrelated) `03SaMcTh` N/F question still holds.

## Step 0/1 — confirm what actually changed, before any run

- `molecules/SO/output/SO_34S16O_22HeStLy_SO_20260918_132255.txt` (32358 data rows) replaces the buggy `archive_22HeStLy_sigmaF_bugfix/SO_34S16O_22HeStLy_SO_20260916_154325.txt` (also 32358 rows — same count, only F-digits differ). **All 32358 rows differ** between old and new (`diff` confirms 100% of rows changed F-label on at least one side) — this was not a localized fix. Old label distribution (upper/lower pairs) covered only 6 of 9 possible F1/F2/F3×F1/F2/F3 combinations (e.g. no F3–F3, F1–F3, F2–F3 at all); the corrected distribution covers all 9 combinations roughly evenly (~3100–4400 each) — consistent with the old code's fixed-formula derivation being structurally incapable of producing certain branch combinations at all.
- Every other 34S16O source's `molecules/SO/output/*.txt` file is unchanged (`ls -la` mtimes: Sep 16, vs. `22HeStLy`'s Sep 18) — confirmed by rebuilding the fallback network from current files and diffing every non-`22HeStLy` row (sorted) against ADR-0008's archived fallback input: byte-identical content (only line-ending convention differs, CRLF in the old archived file vs. LF here — immaterial to `Marvel4.1.x`, which tokenizes on whitespace including `\r`).
- `molecules/SO/combined/SO_34S16O_combined.csv` (32679 rows, current, mtime Sep 18) is the regenerated combined file reflecting the fix; row counts by source-tag prefix exactly match the 12 sources' known transition counts (`22HeStLy`: 32358, `87BuLoHa`: 148, `15DrHiMo`: 48, `96KlSaBe`: 32, `82BoDeDe`: 21, `93Ya`: 18, `03SaMcTh`: 12, `03KiYa`/`74Ti`/`82Ti`/`97KlBeWi`: 10 each, `92LoSuOg`: 1).
- `03SaMcTh`'s own canonical output file (`SO_34S16O_03SaMcTh_SO_20260916_162845.txt`) is unchanged and, as before, carries its real `N_upper`/`N_lower` values; the build scripts (adapted from `.scratch/so-34s16o-marvel_past/build_fallback.py`) force its `F_upper`/`F_lower` slots to the dummy token `-` regardless of whether the file happens to carry converted F values elsewhere in the pipeline, exactly reproducing the prior disconnection convention.

## Part 1: merge test (fallback vs. 03SaMcTh-merged)

Binary: `/mnt/c/Code/versions_MARVEL/Marvel4.1.x/Marvel4.1.x`, run natively (this session's Bash tool already executes inside WSL2 directly — confirmed via a timed single-run test, ~55s — so the runbook's `wsl.exe`-per-call-latency concern did not apply here; all runs still batched into as few shell invocations as practical as a matter of hygiene). `--minsize 200` (default) throughout, never `--minsize 1`. `BadLines.txt` used as authoritative for wrong/very-bad counts (not `CheckTransitions.txt`, which uses bootstrap-adjusted, not stated, uncertainty).

**Parser correction, verified against this rerun's own raw files before trusting any count**: the prior study's `extract_flagged.py` assumed each flagged transition spans two physical lines. That assumption held only because the old (buggy, CRLF-sourced) data had `\r`-terminated IDs, which Python's default universal-newline text-mode reading (`open(..., "rt")`) silently splits into an extra line — an incidental artifact of that run's specific input encoding, not the file's real structure. Confirmed directly on this rerun's data (clean LF, no embedded `\r`): the true format is **one line per record** (`<TAB><SPACES><TAG.ID><SPACES><orig_unc><SPACES><value>[<SPACES><CATEGORY>]`), category suffix present only when flagged. A corrected single-line parser (`.scratch/so-34s16o-marvel/extract_flagged_single.py` and updated `incremental-source-study{,-by-precision}/extract_flagged.py`) was written and validated: its per-source flagged counts sum exactly to each run's own `BadLines.txt` summary line (`wrong + very bad`) at every attempt and every step, with no exceptions.

| attempt | technique | main component | wrong | very bad | total flagged | % of main network | `03SaMcTh` outcome |
|---|---|---|---|---|---|---|---|
| 1 | merged network, `-b` (100 iter, default) | 4906 EL / 32620 TR | 2495 | 454 | 2949 | 9.04% | `03SaMcTh.2` (its 1/12 connecting transition) flagged **VERY BAD**, ratio=11.542 |
| 2 | + `03SaMcTh` uncertainty inflated 12.5x (0.002→0.025, same factor ADR-0005 used, reused not invented) | 4906 / 32620 | 2495 | 454 | 2949 (identical breakdown) | 9.04% | same connection, flagged **VERY BAD_100**, ratio=144.278 (*worse*, same mechanism ADR-0005 diagnosed — see below) |
| 3 | + `--bootiter 1000` (10x default) | 4906 / 32620 | 2495 | 454 | 2949 (identical breakdown) | 9.04% | unchanged from attempt 1, byte-identical `03SaMcTh.2` record |
| fallback | canonical, unconverted, `03SaMcTh` fully disconnected (NQN=6 dummy padding) | 4906 EL / 32618 TR | 54 | 1 | 55 | **0.169%** | not applicable (0 flagged occurrences — genuinely disconnected) |

By-source breakdown, merged network (attempts 1–3, identical across all three):

| source | flagged | % of 2949 | % of source's own lines |
|---|---:|---:|---:|
| `22HeStLy` | 2870 | 97.3% | 2870/32358 = 8.87% |
| `87BuLoHa` | 58 | 2.0% | 58/148 = 39.2% |
| `82BoDeDe` | 8 | 0.3% | 8/21 = 38.1% |
| `74Ti` | 6 | 0.2% | 6/10 = 60.0% |
| `82Ti` | 5 | 0.2% | 5/10 = 50.0% |
| `03SaMcTh` | 1 | 0.03% | 1/12 = 8.3% (`03SaMcTh.2`, the one connecting transition) |
| `92LoSuOg` | 1 | 0.03% | 1/1 = 100% |

By-source breakdown, fallback (disconnected `03SaMcTh`):

| source | flagged | % of 55 | % of source's own lines |
|---|---:|---:|---:|
| `87BuLoHa` | 50 (49 WRONG, 1 VERY BAD) | 90.9% | 50/148 = 33.8% |
| `74Ti` | 4 (WRONG) | 7.3% | 4/10 = 40.0% |
| `82Ti` | 1 (WRONG) | 1.8% | 1/10 = 10.0% |
| `22HeStLy` | 0 | 0.00% | 0/32358 = 0.00% |
| all others | 0 | — | — |

Full raw outputs for every attempt: `.scratch/so-34s16o-marvel/{attempt1,attempt2,attempt3,fallback}/`.

### Why merging `03SaMcTh` reveals `22HeStLy` badness that the fallback never sees

The fallback network (all 11 F-labeled sources merged, `03SaMcTh` disconnected) shows **zero** `22HeStLy` flags. Adding `03SaMcTh`'s single, ultra-precise (kHz-derived, ~6.67e-8 cm-1 stated uncertainty) connecting transition — without adding any new energy level, same 4906-level main component either way — is enough to flip 2870 `22HeStLy` transitions from consistent to flagged. This reproduces ADR-0009's core mechanism (a sufficiently tight-precision edge exposes the full magnitude of an otherwise-masked inconsistency in a weighted least-squares network) but, on corrected data, the effect is now concentrated entirely in this one disputed, already-flagged edge rather than being a general property of "whichever source closes a loop" as ADR-0008/0009 found on the buggy data. This is a genuine, disclosed finding in its own right, not just a repeat of ADR-0005's inflation-makes-it-worse result (attempt 2, below) — it shows `03SaMcTh`'s specific connection is doing real, outsized damage to network quality, independent of what technique is used to try to reconcile it.

### Why uncertainty inflation (attempt 2) made `03SaMcTh` worse again, near-identically to ADR-0005

Inflating `03SaMcTh.2`'s uncertainty 12.5x reproduces ADR-0005's finding almost exactly in both direction and magnitude: ratio went from 11.542 (`VERY BAD`) to 144.278 (`VERY BAD_100`) — ADR-0005 measured 11.5→144 on the buggy data. Since `03SaMcTh`'s own file, and the two energy levels its transition touches, were never affected by the `22HeStLy` F-label bug, this specific outcome being essentially unchanged is expected and is a useful independent cross-check that this particular finding was never an artifact of the bug in the first place.

## Part 2: incremental attribution, both orderings

Same 12-step cumulative build as ADR-0008 (ascending own-transaction-count) and ADR-0009 (ascending own-stated-precision), same NQN=6 dummy-padded schema throughout (`03SaMcTh` kept structurally disconnected at every step), same source order and per-source unit table reused verbatim from the archived scripts (unchanged — no source's transaction count or measurement precision changed, only `22HeStLy`'s F-labels). Full raw outputs: `.scratch/so-34s16o-marvel/incremental-source-study{,-by-precision}/step<NN>_<source>/`.

### Transaction-count order (reproduces ADR-0008's method)

| step | added | cum. main levels | cum. main transitions | wrong | very bad | total flagged | % of main network | newly flagged (by source) |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | `22HeStLy` alone | 2452 | 16111 | 0 | 0 | 0 | 0.00% | — |
| 2 | `92LoSuOg` | 4904 | 32359 | 0 | 0 | 0 | 0.00% | — |
| 3 | `03KiYa` | 4904 | 32359 | 0 | 0 | 0 | 0.00% | — |
| 4 | `74Ti` | 4905 | 32369 | 1 | 0 | 1 | 0.003% | `74Ti`: 1 |
| 5 | `82Ti` | 4905 | 32379 | 5 | 0 | 5 | 0.015% | `74Ti`: 3, `82Ti`: 1 |
| 6 | `97KlBeWi` | 4905 | 32379 | 5 | 0 | 5 | 0.015% | — |
| 7 | `03SaMcTh` (disconnected) | 4905 | 32379 | 5 | 0 | 5 | 0.015% | — |
| 8 | `93Ya` | 4905 | 32379 | 5 | 0 | 5 | 0.015% | — |
| 9 | `82BoDeDe` | 4905 | 32396 | 0 | 0 | 0 | 0.00% | (all 5 prior `74Ti`/`82Ti` flags un-flag) |
| 10 | `96KlSaBe` | 4905 | 32422 | 5 | 0 | 5 | 0.015% | `74Ti`: 4, `82Ti`: 1 (re-flagged) |
| 11 | `15DrHiMo` | 4905 | 32470 | 5 | 0 | 5 | 0.015% | — |
| 12 | `87BuLoHa` (final, all 12) | 4906 | 32618 | 54 | 1 | 55 | **0.169%** | `87BuLoHa`: 50 |

`22HeStLy` is flagged **zero times at every one of the 12 steps**, including the final all-12-source network.

### Precision order (reproduces ADR-0009's method)

| step | added | cum. main levels | cum. main transitions | wrong | very bad | total flagged | % of main network | newly flagged (by source) |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | `22HeStLy` alone | 2452 | 16111 | 0 | 0 | 0 | 0.00% | — |
| 2 | `03SaMcTh` (disconnected) | 2452 | 16111 | 0 | 0 | 0 | 0.00% | — |
| 3 | `03KiYa` | 2452 | 16111 | 0 | 0 | 0 | 0.00% | — |
| 4 | `92LoSuOg` | 4904 | 32359 | 0 | 0 | 0 | 0.00% | — |
| 5 | `15DrHiMo` | 4904 | 32407 | 0 | 0 | 0 | 0.00% | — |
| 6 | `93Ya` | 4904 | 32407 | 0 | 0 | 0 | 0.00% | — |
| 7 | `82Ti` | 4904 | 32417 | 0 | 0 | 0 | 0.00% | — |
| 8 | `96KlSaBe` | 4904 | 32443 | 0 | 0 | 0 | 0.00% | — |
| 9 | `82BoDeDe` | 4904 | 32460 | 0 | 0 | 0 | 0.00% | — |
| 10 | `97KlBeWi` | 4904 | 32460 | 0 | 0 | 0 | 0.00% | — |
| 11 | `74Ti` | 4905 | 32470 | 5 | 0 | 5 | 0.015% | `74Ti`: 4, `82Ti`: 1 |
| 12 | `87BuLoHa` (final, all 12) | 4906 | 32618 | 54 | 1 | 55 | **0.169%** | `87BuLoHa`: 50 |

Endpoint is **identical** to the transaction-count order in every figure (4906/32618, 54 wrong + 1 very bad = 55, same by-source breakdown) — expected for a fully-merged graph (order of assembly cannot change the converged solution). `22HeStLy` is again flagged zero times at every step.

### The precision-dependent-masking effect (ADR-0009's core finding) is gone

ADR-0009's headline was that the same structural milestone (the moment `22HeStLy`'s small disconnected pieces merge into one large redundant network, at step 4/5 in both orderings) reveals roughly an order of magnitude worse badness when reached via a high-precision source (`15DrHiMo`, step 5 here) than a low-precision one (`74Ti`, ADR-0008's step 4). On corrected data, **that milestone reveals zero badness either way** — both the precision-ordered step 5 (`15DrHiMo`, tightest-tier trigger) and the transaction-count-ordered step 4 (`74Ti`, loosest-tier trigger) show 0 flagged lines. There is no longer anything for precision to differentially "expose," because the underlying `22HeStLy` data has nothing wrong with it once correctly labeled. ADR-0009's mechanism (tight sources expose more of a real weighted-fit disagreement) is not disputed as a general MARVEL4 property — it simply has no `22HeStLy` inconsistency left to act on in this corrected network.

## Attempt-budget accounting

3 genuinely distinct techniques tried on the merge test via the real `Marvel4.1.x` binary (default bootstrap merge; manual uncertainty inflation, factor reused from ADR-0005's own prior derivation; 10x bootstrap depth) — same budget ADR-0005 used, all reproducing the same "does not validate" verdict with much better absolute network quality. Both incremental-attribution orderings from ADR-0008/0009 were also redone in full (not partially), since the task's own instruction and the value of the order-comparison justified it and the runs were cheap (~15–35s each natively).

## Verdict

**Merge test: REJECTED for merging — CONFIRMED, not revised.** `03SaMcTh`'s N→F-converted connecting transition still fails at essentially the same magnitude (ratio 11.54, vs. ADR-0005's ≈11.5) regardless of the now-fixed `22HeStLy` bug, and forcing it into the network now costs far more (55→2949 flagged lines, a 54x degradation) for the same zero connectivity gain, since it exposes real inconsistency in `22HeStLy` transitions that the disconnected treatment never touches. This question was never about `22HeStLy`'s F-labels — it is about `03SaMcTh`'s own N→F conversion and its disputed compatibility with the rest of the X3Sigma- network — and the corrected data does not change that answer, it sharpens it: merging is now demonstrably worse in relative terms (54x vs. ADR-0005's "statistically indistinguishable, but merging still added an unresolved 11.5σ inconsistency").

**Incremental attribution: REVISED.** The ≈99.6%-attributed-to-`22HeStLy` finding (ADR-0008, refined further in ADR-0009) does **not** survive on corrected data and is **not confirmed**. `22HeStLy` is completely self-consistent (0/32358 flagged, 0.00%) throughout the entire 12-source build, both orderings, including the fully-merged endpoint. The prior finding was the F-labeling bug's own signature: spurious F1/F2/F3 assignment fabricated combination-difference violations between energy sublevels that were never actually the same physical level, inflating apparent inconsistency to ≈60% of the network. On corrected data, the network's real (much smaller) badness — 55 lines, 0.169% of 32618 main-component transitions — is attributable to `87BuLoHa` (90.9%), `74Ti` (7.3%), and `82Ti` (1.8%): the same three sources ADR-0008 had already flagged as small, real, secondary concerns (`87BuLoHa`'s 53%-of-own-148-lines finding on the buggy data; here, 33.8%-of-own-148 on corrected data — still real, still worth a follow-up, now simply the *entire* remaining story instead of a footnote).

## Consequences

- **Final deliverable is promoted**: `molecules/SO/reference_papers/34S-16O_MARVEL_states.txt` (4906 levels) and `molecules/SO/reference_papers/34S-16O_MARVEL_trans.txt` (32678 transitions, `03SaMcTh` kept structurally disconnected via NQN=6 dummy padding), built from the **fallback** run — same structural choice as ADR-0005, dramatically better absolute quality (0.169% vs. 59.87% badness). The prior (buggy-data) deliverable is archived as `molecules/SO/reference_papers/34S-16O_MARVEL_states_past.txt` / `34S-16O_MARVEL_trans_past.txt`.
- **`22HeStLy`'s uncertainty calibration is no longer an open follow-up.** ADR-0005/0008 both flagged "recalibrate `22HeStLy`'s blanket 0.05 cm-1 uncertainty" as real, separate, worthwhile future work. That follow-up is now **closed as moot**: `22HeStLy` was never miscalibrated: the apparent problem was entirely the F-labeling bug. No recalibration work is needed or should be attempted based on the prior ADRs' framing.
- **New, smaller follow-up**: `87BuLoHa` (33.8% of its own 148 transitions flagged, 90.9% of the network's total remaining badness) and, much more marginally, `74Ti` (40% of its own 10) and `82Ti` (10% of its own 10) are now the network's only real remaining quality concerns — worth a future case-by-case look (Brady-footnote-(a)-style manual uncertainty review, or a check of whether `87BuLoHa`'s IR line positions have a genuine systematic offset against the microwave sources), but two orders of magnitude smaller in absolute impact than what ADR-0005/0008 were originally worried about.
- **`03SaMcTh`'s disconnected treatment remains correct and unchanged.** Its N/F conflict (ADR-0002/0003/0004/0005) is confirmed, again, to be a real, separate issue, not entangled with and not resolved by today's `22HeStLy` bugfix.
- **A parsing gotcha is now documented for any future `BadLines.txt` consumer**: the file's true record format is one physical line per transition (`TAG.ID orig_unc value [CATEGORY]`), not the two-physical-line structure ADR-0008/0009's `extract_flagged.py` assumed — that assumption only ever held because the buggy-era source data had CRLF-embedded IDs, which Python's default universal-newline text-mode reading incidentally split into two lines. Any future reuse of `.scratch/so-34s16o-marvel_past/incremental-source-study{,-by-precision}/extract_flagged.py` against clean (LF-only) data will silently find 0 flagged lines — this was caught and fixed in this rerun's own `extract_flagged.py`/`extract_flagged_single.py` (verified: per-source sums exactly match each run's own `BadLines.txt` summary line at every attempt and step) and should be reused instead of the archived version.
- No change to ADR-0002/0003/0004/0006/0007's status. This ADR supersedes ADR-0005 (confirms its verdict, sharpens its numbers) and ADR-0008/0009 (reverses their headline attribution finding) as the operative decisions for 34S16O.
