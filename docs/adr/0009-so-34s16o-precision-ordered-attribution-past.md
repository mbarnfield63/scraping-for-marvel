# ADR-0009: SO 34S16O — precision-ordered rerun refines ADR-0008: revealed inconsistency is precision-dependent, not uniform

## Status

**Empirical finding, refining (not overturning) ADR-0008.** Rerunning ADR-0008's 12-step
incremental `Marvel4.1.x` build with the 11 non-`22HeStLy` sources ordered by their own
stated measurement precision (tightest first) instead of by transition count reproduces
ADR-0008's endpoint exactly (same final network, same 99.6% `22HeStLy` attribution), but
shows the *path* to that endpoint is not order-independent in the way a purely structural
"redundant loops reveal a pre-existing inconsistency" story would suggest: the same
network-connectivity milestone reveals roughly an order of magnitude worse badness (by both
count and residual/uncertainty ratio) when reached via a high-precision source than via a
low-precision one.

## Context

ADR-0008 built the 34S16O X3Sigma- network one source at a time, ascending by each source's
own transition count, and found `22HeStLy` alone self-consistent (0% wrong/very-bad) with
the eventual ~60% badness appearing only once other sources' transitions closed enough
redundant loops through `22HeStLy`'s network — and, once revealed, that badness was 99.6%
attributable to `22HeStLy` regardless of which source did the revealing. This follow-up
tests whether that "regardless of which source" claim holds up when the addition order is
chosen specifically to probe it: order by each source's own precision instead, tightest
first, to see whether the revealed inconsistency's *magnitude* depends on the precision of
whatever source closes a given loop.

Full method, per-source uncertainty values/citations, step-by-step results table, and raw
outputs: `.scratch/so-34s16o-marvel/incremental-source-study-by-precision/PROCESS.md` and
its sibling `step<NN>_<source>/` directories.

## Method summary

Same 12 sources, same NQN=6 dummy-padded schema, same `03SaMcTh` structurally-disconnected
treatment as ADR-0008, same real `Marvel4.1.x` bootstrap runs (`-b`, default 100-iteration
bootstrap, default `--minsize 200`), batched into a single `wsl.exe` call. Only the addition
order changed: `22HeStLy` alone (step 1), then the 11 others ascending by their own stated
34S16O measurement uncertainty converted to a common cm-1 scale (the same conversion
Marvel4.1.x performs internally per source via `segment.txt`) — `03SaMcTh` (6.7e-8 cm-1,
kept disconnected regardless), `03KiYa` (9.7e-8), `92LoSuOg` (1.3e-7), `15DrHiMo` (4.8e-7),
`93Ya` (1.4e-6), `82Ti` (1.7e-6), `96KlSaBe`/`82BoDeDe`/`97KlBeWi` (tied at 3.3e-6, tiebreak
by mean), `74Ti` (5.8e-6), `87BuLoHa` (2.2e-4, loosest of the 11 — an IR/FTIR line position,
genuinely harder to pin down in absolute cm-1 terms than a microwave frequency, not an
error). See PROCESS.md Section 1 for full per-source derivation and citations.

## Findings

**1. The endpoint is reproduced exactly — order does not change where the fully-merged
network lands.** Step 12 (all 12 sources): 5028 levels, 32618 main-component transitions,
4562 wrong, 14965 very bad, 59.87%, 19527 distinct flagged transitions, 19442 (99.6%) of
them `22HeStLy`'s own — identical to ADR-0008 in every figure, including a by-source detail
(`82Ti`: 1 flagged line) ADR-0008's prose didn't spell out but its data must have carried.
This is exactly what should happen for a fully-merged graph: order of assembly cannot
change the converged solution, only the intermediate path to it.

**2. The intermediate path is very much order-dependent, and the effect is precision-linked,
not random.** Both this study and ADR-0008 cross the same structural milestone — `22HeStLy`'s
small disconnected pieces suddenly merging into one ~4900-level/~32370-transition redundant
network — at a single step, via a different source: `15DrHiMo` here (tightest-connecting
source, 2015 THz-comb, uncertainty 4.8e-7 cm-1) vs `74Ti` in ADR-0008 (loosest-connecting
of the ties at that stage, 1974 microwave, 5.8e-6 cm-1 — an order of magnitude looser).
Re-parsing ADR-0008's own `step04_74Ti/BadLines.txt.gz` for a direct, matched comparison
(read-only; ADR-0008's files untouched):

| triggering source | precision rank (of 11, tightest=1) | newly-flagged `22HeStLy` lines | ratio min/median/mean/max |
|---|---:|---:|---|
| `74Ti` (ADR-0008, its step 4) | 10/11 | 1134 | 1.313 / 6.330 / 9.738 / 37.880 |
| `15DrHiMo` (this study, step 5) | 4/11 | 11760 | 1.048 / 28.200 / 28.157 / 85.680 |

At essentially the same network-completeness milestone: ~10x more lines revealed, and a
~4.5x higher median (~2.9x higher mean) residual/uncertainty ratio, when the loop is closed
by the higher-precision source. Aggregating all "tight-tier" (steps 2-6) vs "loose-tier"
(steps 7-12) newly-flagged `22HeStLy` ratios gives the same direction: median 28.2 vs 2.6,
mean 28.2 vs 9.0 (dominated by the single `15DrHiMo` event on the tight side — see
PROCESS.md §5 for the caveat that this is inherently a few-large-events comparison, not a
many-vs-many one, an unavoidable property of the incremental-build method).

**3. A parsing correction along the way, worth flagging for any future reader of
`BadLines.txt`.** The second numeric field on a flagged line's value line is *not* already
the residual/uncertainty ratio — it's a raw residual-equivalent value in the transition's
native uncertainty unit. The real ratio (the one the WRONG/VERY BAD/VERY BAD_100/VERY
BAD_1000 thresholds are computed from) is that field divided by the line's own stated
uncertainty (the first field) — verified empirically by checking that this quotient, and
not the raw field alone, cleanly respects the four category boundaries (1/10/100/1000)
across the entire step-12 `BadLines.txt`. `extract_flagged.py` in both study directories
should be read with this in mind if reused again.

## Interpretation: precision-dependent masking, most likely a weighting artifact rather than a genuinely different `22HeStLy` error against modern sources

MARVEL4's fit is a weighted least-squares combination where each source's leverage scales
as `1/uncertainty^2`. `15DrHiMo`'s uncertainty outweighs `22HeStLy`'s stated 0.05 cm-1 by
roughly ten orders of magnitude, so the fit snaps almost entirely to what `15DrHiMo`
implies, exposing close to the *full* magnitude of wherever `22HeStLy` disagrees. A loose
source like `74Ti` (only ~100x tighter than `22HeStLy`, not ~1e10x) produces more of a
compromise fit, splitting the disagreement and understating it in the reported ratio. Read
this way, the finding is **not** "`22HeStLy` is more wrong specifically against modern
instruments" — its underlying absolute miscalibration is plausibly uniform — but that **the
network's ability to reveal that miscalibration's true size is itself precision-dependent**:
tight sources expose close to the full inconsistency; loose sources structurally mask or
dilute it in the reported ratio. This is exactly the mechanism the task's stated hypothesis
anticipated. It is not a perfectly clean single-variable relationship — `96KlSaBe` and
`82BoDeDe` sit at the same nominal precision tier yet reveal different median ratios (3.3
vs 8.1), so network topology (which specific levels/transitions each source happens to
touch) modulates the effect too — but the precision effect itself is large, real, and
directionally consistent across every comparison run in this study.

## Consequences

- ADR-0008's headline (99.6% of final badness traces to `22HeStLy`, revealed rather than
  caused by whichever source closes a loop) is **confirmed at the endpoint** and not
  overturned — this ADR only concerns the *intermediate path*.
- Anyone recalibrating `22HeStLy`'s blanket uncertainty (ADR-0005's flagged follow-up)
  should be aware that a single-source or small-subnetwork self-check against loose,
  older sources will systematically *understate* how badly miscalibrated `22HeStLy` is —
  the true magnitude is best probed by checking against the tightest available independent
  source(s), not the historically-first-available ones.
- `03SaMcTh`'s disconnected treatment remains reconfirmed clean regardless of ordering
  scheme: zero flagged lines at every step in this study too, exactly as in ADR-0008.
- No change to ADR-0002/0003/0004/0005/0006/0007/0008's status. This ADR adds a precision
  dimension to ADR-0008's finding, it does not replace it.
