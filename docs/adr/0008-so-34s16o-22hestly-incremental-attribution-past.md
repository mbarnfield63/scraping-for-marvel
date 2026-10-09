# ADR-0008: SO 34S16O — incremental-build source attribution of the ≈60% bad-line rate

## Status

**Empirical finding, not a decision to accept/reject anything.** Confirms, sharpens, and
partially corrects the methodology behind ADR-0005's "finding 1" (that `22HeStLy`
dominates 34S16O's network badness): real, incremental `Marvel4.1.x` bootstrap runs (12
steps, one source added at a time) show `22HeStLy` alone is **completely self-consistent**
(0% wrong/very-bad) and that the ≈60% final bad-line rate appears only once other sources'
transitions close enough redundant loops through `22HeStLy`'s own network to make a
self-consistency check possible — at which point it is **99.6% attributable to `22HeStLy`
specifically** (not the ≈97.7-97.8% ADR-0005 reported, which used a file,
`CheckTransitions.txt`, that turns out not to be restricted to flagged lines — see below).

## Context

ADR-0005's finding 1 was inferred by breaking `CheckTransitions.txt` down by source tag on
the **already-fully-merged** 12-source 34S16O network — a single data point on the final
network, not an incremental build, and (discovered in this study) not even drawn from the
file that actually carries MARVEL4.1's WRONG/VERY BAD flags. This task rebuilds the
network one source at a time with real `Marvel4.1.x` bootstrap runs (not simplified
pre-checks) to test: (a) is `22HeStLy` really self-consistent alone, as its own paper's
≤1.1% invalidation rate would suggest, and (b) precisely which addition(s) introduce the
final ≈60% badness, rather than assuming it's spread proportionally or attributable in one
lump sum to the final network's tag composition.

Full method, per-step table, and raw outputs:
`.scratch/so-34s16o-marvel/incremental-source-study/PROCESS.md` and its sibling
`step<NN>_<source>/` directories (Components.txt, CheckTransitions.txt,
BadLines_summary.txt + gzipped BadLines.txt, run.log, per step).

## Method summary

12 cumulative `Marvel4.1.x` runs (`-b` default 100-iteration bootstrap, default
`--minsize 200`), all via the real binary, batched into a single `wsl.exe` call. Addition
order: `22HeStLy` alone (32358 of 32678 34S16O transitions), then the other 11 sources
ascending by their own transition count (cheapest first, so each jump is attributable to
one addition). `03SaMcTh` (12 transitions, step 7) is kept structurally disconnected via
the same NQN=6 dummy-padding scheme as ADR-0005's fallback network — its N/F labeling
conflict is a separate, already-litigated question (ADR-0002/0003/0004/0005), out of scope
here. Step 12 (all 12 sources) reproduces ADR-0005's fallback network exactly: 5028
levels, 32618 main-component transitions, 4562 wrong, 14965 very bad (59.87% ≈ 59.9%) —
the transitions file itself is byte-identical (sorted) to ADR-0005's own `build_fallback.py`
output.

## Two findings

**1. `22HeStLy` alone genuinely is self-consistent, verifying the task's stated
hypothesis rather than assuming it.** 0 wrong, 0 very-bad lines across every part of
`22HeStLy`'s own 32358-transition network dense enough to check for internal consistency
(steps 1-3, through two more additions that don't yet touch it). This matches the
expectation that a single source's own combination-differences are usually already clean,
since that's typically what let it pass its own paper's fit (`22HeStLy`/Heays et al. 2022
stated ≈1.1%-or-better invalidation, consistent with `24BrYuTe`'s own analogous
`22HeStLy`-adjacent figures).

**2. The badness doesn't appear gradually or proportionally — it appears in discrete
jumps the moment another source's transitions close enough loops to make a check
possible, and it is essentially always `22HeStLy`'s own transitions that fail that check,
not the source that closed the loop.** The first jump (step 4, +`74Ti`, only 10
transitions) roughly doubles the main component's size and immediately flags 1134 lines —
100% of them `22HeStLy`. Every subsequent jump (steps 5, 9, 10, 11) shows the same
pattern: small newly-added sources (`82Ti`, `82BoDeDe`, `96KlSaBe`, `15DrHiMo`) each
trigger large increases in flagged `22HeStLy` lines, while contributing at most a handful
of flags of their own. Three additions (`97KlBeWi`, `03SaMcTh` disconnected, `93Ya`)
produce **zero new flagged lines at all** — a genuine negative result, not a null one to
skip: their transitions simply don't land in the checkable redundant part of the network
at that stage. Only the very last addition, `87BuLoHa` (step 12), meaningfully flags a
share of its own lines (78 of its 148, 53%) alongside the usual large `22HeStLy` movement
— the only source, other than `22HeStLy` itself, whose own calibration this study finds
any real evidence against, and even then only 78 of the network's 19527 total flagged
lines (0.4%).

At the final, all-12-source network: **19442 of 19527 distinct flagged transitions
(99.6%) are `22HeStLy`'s own transitions** — a more concentrated, more precisely measured
attribution than ADR-0005's ≈97.7-97.8%, not a contradiction of it. The difference traces
to a real methodological gap this study closes: `CheckTransitions.txt`'s last-column ratio
is computed against MARVEL4's *bootstrap-adjusted* uncertainty, not the original stated
one, so it stays under 1 for the great majority of lines regardless of flag status —
confirmed directly (step 1, `22HeStLy` alone, 0 wrong/0 very-bad per `BadLines.txt`, yet
every `22HeStLy` transition still appears in `CheckTransitions.txt` at ratio < 1, max
0.972). The correct source for a flagged-lines-by-source breakdown is `BadLines.txt`
itself (each flagged transition's `TAG.ID` + category, WRONG/VERY BAD/VERY BAD_100/VERY
BAD_1000) — the count of distinct flagged IDs there exactly matches the file's own
`wrong + very bad` summary line at every one of the 12 steps, which `CheckTransitions.txt`
occurrence counts do not.

## Consequences

- ADR-0005's finding 1 (`22HeStLy` dominates 34S16O's network badness) is **confirmed and
  sharpened**, not overturned: the real number is 99.6%, not ≈97.7-97.8%, and the
  incremental build additionally shows the effect is a genuine, load-bearing property of
  `22HeStLy`'s own transitions (revealed by, not caused by, whichever other source closes
  a loop) rather than an artifact of how the final merged network happens to be composed.
- `03SaMcTh`'s disconnected treatment is reconfirmed clean in an incremental setting too:
  zero flagged lines at every step, before or after its own addition (step 7) — it neither
  hides nor contributes to any part of this attribution.
- `87BuLoHa` (53% of its own 148 lines flagged at the step it's added) is a small, real,
  previously-undiscussed secondary calibration concern — worth a mention for whoever next
  works on this network's overall quality, but two orders of magnitude smaller than
  `22HeStLy`'s share and not a reason to revisit this study's headline finding.
- Future work recalibrating `22HeStLy`'s stated blanket uncertainty (ADR-0005's own
  flagged follow-up) should use `BadLines.txt`'s WRONG/VERY BAD tags directly, not
  `CheckTransitions.txt` occurrence counts, for any further by-source breakdown — the
  latter measures redundant-path check coverage, not actual flag status.
- No change to ADR-0005's verdict (fallback/disconnected network remains the final
  deliverable) or to ADR-0002/0003/0004's status.
