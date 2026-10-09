# ADR-0010: SO 33S16O X3Sigma- real MARVEL4.1 bootstrap empirical test

## Status

**ACCEPTED for merging.** Real `Marvel4.1.x` bootstrap runs (not a simplified fixed-
uncertainty pre-check) show 33S16O's three F-labeled sources (`22HeStLy`, `15DrHiMo`,
`96KlSaBe`) merge into a single 4508-level / 29182-transition component with **zero**
wrong or very-bad lines (`BadLines.txt`, the authoritative source per the runbook) —
under every technique tried (default bootstrap, 10x bootstrap depth) and at every stage
of an incremental one-source-at-a-time build. This is a genuinely different, better
outcome than 34S16O/36S16O's real-bootstrap results (ADR-0005/ADR-0006/ADR-0012, both
~55-60% wrong+very-bad dominated by `22HeStLy`'s own calibration) and does **not**
confirm `docs/adr/0004-nf-unification-literature-research-so.md`'s fixed-uncertainty
pre-check finding of RMS(resid/unc)=317, max=1358 for 33S16O — see Verdict for why.

`03SaMcTh` (22 transitions, N-labeled + real nuclear-hyperfine F) remains structurally
disconnected from the F-labeled network for this isotopologue, as it must — see
"The NQN=6 single-topology finding" below for why there is no alternative to test.

## Context

This is 33S16O's first real-`Marvel4.1.x` bootstrap treatment — until now it only had
the fixed-uncertainty script-level pre-check in ADR-0004 (`optionB_nf_validation_
22hestly.py`), which flagged a large conflict (RMS(resid/unc)=317.13, max=1357.85) but
was explicitly disclosed there as resting on a real, not-yet-fixed bug (upper-state
`ef_upper` omitted from the node key, spuriously merging ~44% of distinct upper levels)
and was never re-run clean. Per `docs/agents/marvel4-bootstrap-runbook.md` and the
34S16O/36S16O precedent (ADR-0005, ADR-0006, ADR-0008, ADR-0012), this task gives
33S16O the same real-binary treatment.

33S16O's 4 sources, confirmed via `molecules/SO/combined/SO_33S16O_combined.csv` id
prefixes and each source's own canonical `molecules/SO/output/SO_33S16O_<paperID>_
<timestamp>.txt` (all current, no stale files, no archive-dir shadowing):

| source | transitions | QN scheme |
|---|---|---|
| `22HeStLy` | 29137 | NQN=5: `state,v,J,F,ef` — F = electronic fine-structure F1/F2/F3, ef = real e/f |
| `15DrHiMo` | 21 | NQN=5: same scheme as `22HeStLy` |
| `96KlSaBe` | 24 | NQN=5: same scheme as `22HeStLy` |
| `03SaMcTh` | 22 | NQN=6: `state,v,N,J,F,ef` — N = real (Hund's case-b), F = real nuclear-hyperfine value (half-integer, 33S I=3/2), ef genuinely blank |

Step 0/1 spot-checks (quick sanity checks, not a re-extraction): `15DrHiMo`'s
723120.527/723773.541 MHz rows and `96KlSaBe`'s 595169.817/596221.884 MHz rows were
checked directly against `molecules/SO/markdown/{15DrHiMo_SO,96KlSaBe_SO}/full.md`.
Both match the source table exactly, including `96KlSaBe` Table 3's footnote (c)
("For unresolved hfs splitting the F'<-F'' values are omitted") — the extraction
correctly used only the high-N rows where the paper's own hyperfine F column is blank
(unresolved), converting N,J to the electronic F1/F2/F3 label via the same map already
verified correct in ADR-0005 for 34S16O, rather than the paper's real, resolved
low-N hyperfine-F rows (which belong to a different physical axis entirely — see
below). A real, useful overlap was also found directly: `15DrHiMo` and `96KlSaBe` both
report the v=0 J=20->19 F3 transition at 893280.267 vs 893280.556 MHz (and two
neighboring F1/F2 lines, agreeing to within 0.007-0.29 MHz against 0.06-0.3 MHz stated
uncertainties) — genuine independent redundant coverage between these two small
sources, not just via `22HeStLy`.

## The NQN=6 single-topology finding

Unlike 34S16O, where `03SaMcTh`'s F column was genuinely blank (34S has no nuclear
spin) and a separate, already-N-to-F-converted version of its data existed in
`molecules/SO/csv/03SaMcTh_SO_merged.csv`/`combined.txt` — giving ADR-0005 two
genuinely different topologies to compare (a riskier "merged" one vs. the safe
"fallback") — **33S16O has only one buildable topology.** `03SaMcTh`'s F column here
holds real, directly-measured **nuclear-hyperfine** F (33S, I=3/2: F = N+3/2, N+1/2,
..., |N-3/2|), a different physical quantity from the other three sources' **electronic
fine-structure** F1/F2/F3 label (CLAUDE.md's own MARVEL Input Format section documents
these as two distinct, never-combined schemes). No N-to-F-converted version of
`03SaMcTh`'s 33S16O data exists anywhere in this repo's corpus — converting it would
mean implementing new formula work (discarding real resolved hyperfine detail to
produce a synthetic, unresolved-equivalent electronic label), which is out of scope for
this run (the task specifies the dummy-padding convention, not new conversion work) and
is flagged below as a real, scoped future option, not attempted here.

Per the runbook's Step 3 (and `build_fallback.py`/`build_steps.py`, adapted directly
from the 34S16O precedent), this repo therefore unions both schemas into **NQN=6**
(`state,v,N,J,F,ef` per side) by padding the missing slot with the dummy token `-`:
- `03SaMcTh`: N populated (real), F populated (real hyperfine value), ef padded `-`
  (this source's table has no e/f parity column at all).
- `22HeStLy`/`15DrHiMo`/`96KlSaBe`: N padded `-`, F/ef populated (real F1/F2/F3, e/f).

Because every `03SaMcTh` row carries a real N and every other source's row carries `-`
in the N slot, `03SaMcTh`'s nodes can never share a label string with an F-labeled
node — structural disconnection is guaranteed by the N slot alone, regardless of
whatever string happens to sit in the F slot (hyperfine "1/2" vs. electronic "F1" never
collide anyway, since they're drawn from disjoint string sets). **This means the
"fallback" and any "merged/attempt" network are the identical file for 33S16O** — there
is no less-merged alternative to test against, unlike 34S16O/36S16O. `build_fallback.py`
and `incremental-source-study/build_steps.py` both produce this one NQN=6 topology;
`build_steps.py`'s step04 output is verified byte-identical (sorted) to
`build_fallback.py`'s output.

## Method and results

29204 total transitions (22+21+29137+24), NQN=6, `--minsize 200` (default, never 1)
throughout. All runs via a **private copy** of `Marvel4.1.x` (see "Environment gotcha"
below) — `.scratch/so-33s16o-marvel/bin/Marvel4.1.x`, batched into one `wsl`-less bash
invocation (`run_all.sh`) since this session's shell was already native WSL.

| run | technique | main component | wrong | very bad | `03SaMcTh` status | decomp warnings |
|---|---|---|---|---|---|---|
| fallback | default bootstrap (`-b`, 100 iter) | 4508 EL / 29182 TR | 0 | 0 | 9 isolated star components, 22 TR total, never merges | 0 |
| attempt 1 | default bootstrap (`-b`, 100 iter), identical input to fallback | 4508 EL / 29182 TR | 0 | 0 | same, 0 flagged | 19 |
| attempt 2 | `--bootiter 1000` (10x depth), identical input | 4508 EL / 29182 TR | 0 | 0 | same, 0 flagged | 499 |
| incr. step 1 | `22HeStLy` alone | 2262 EL/14603 TR + 2246 EL/14534 TR (**two** components) | 0 | 0 | n/a | 0 |
| incr. step 2 | + `15DrHiMo` | 4508 EL / 29158 TR (**merges into one**) | 0 | 0 | n/a | 0 |
| incr. step 3 | + `03SaMcTh` | 4508 EL / 29158 TR (unchanged) + 9 isolated stars (22 TR) | 0 | 0 | disconnected, confirmed | 0 |
| incr. step 4 | + `96KlSaBe` (= fallback) | 4508 EL / 29182 TR | 0 | 0 | disconnected, confirmed | 0 |

`Components.txt`, `BadLines.txt`, and `AVTable.txt` are byte-identical across
fallback/attempt1/attempt2 (verified with `cmp`) — only `EnergyLevels.txt` and
`CheckTransitions.txt` differ, at the ~1e-7 floating-point level expected from
run-to-run bootstrap-resampling variation, never affecting the wrong/very-bad
classification. `03SaMcTh`'s 22 transitions split into 9 small components (2-4 energy
levels, 1-3 transitions each, one per `v`) — confirmed exactly matching the
star-topology predicted from its data (2-3 hyperfine-F upper levels sharing one common
lower-state node per `v`), with zero internal redundancy to even check (a star has no
closed loop).

### Root cause of the `wrong decomp 1` / blank-main-component anomaly (both resolved, both benign)

1. **Blank "main component" line**: a bug in this session's own one-line log-summary
   extraction command (`sort -t= -k2 -n -r Components.txt`), not the solver.
   `Components.txt` lines have the form `N. component   nbEL= X  nbTR= Y` — **two** `=`
   characters per line — so `sort -t=` splits on both, and `-k2` does not isolate the
   `nbEL` value the way it did for a differently-formatted file in a prior session. The
   raw `Components.txt` file itself was correct and complete the whole time (confirmed:
   byte-identical between fallback/attempt1/attempt2, and its component sizes sum
   exactly to the expected per-source transition counts at every incremental step).
   **Fix**: don't rely on ad hoc single-line `sort`/`awk` against `Components.txt`'s
   two-`=`-per-line format; `grep "component" | grep -v "Transitions of"` and read the
   `nbEL=`/`nbTR=` values directly, as done above. No repo data or ADR conclusion was
   ever at risk from this — it was purely a bug in a throwaway shell one-liner in this
   session's own `run_all.sh`.
2. **`wrong decomp 1` warnings** (0 in fallback, 19 in attempt1, 499 in
   attempt2/`--bootiter 1000` — scaling with iteration count, on the *same* input file
   every time): genuine, reproducible **bootstrap-resampling stochastic instability**,
   not a bug in this session's tooling and not the `--minsize 1` crash mode ADR-0005
   documented (that one calls `exit(-1)` and halts the run; this one prints a warning
   and continues, `EXITCODE=0` every time). Root cause: on some fraction of bootstrap
   iterations, the random resample happens to isolate one of `03SaMcTh`'s tiny 2-4-node
   star components (1-3 edges) into a degenerate 1x1 or otherwise singular linear
   system for that iteration only — `Marvel4.1.x` catches this internally (evidently a
   caught exception around the per-iteration Cholesky decomposition, not the outer
   `exit(-1)` path `--minsize 1` triggers) and simply continues to the next iteration.
   Confirmed **benign**: `Components.txt`, `BadLines.txt`, and `AVTable.txt` are
   byte-identical regardless of how many (0, 19, or 499) warnings fired; only the
   bootstrap-fitted energy values in `EnergyLevels.txt`/`CheckTransitions.txt` show
   ~1e-7-level numerical noise across reruns, the ordinary run-to-run variation
   expected from any stochastic resampling procedure. **This is a real, disclosed,
   general finding for future runs on any network containing small (near-`--minsize`)
   disconnected components: expect intermittent, non-fatal `wrong decomp 1` console
   noise proportional to bootstrap iteration count, and verify via `cmp` (not just
   `EXITCODE`) that it doesn't change `Components.txt`/`BadLines.txt` before trusting a
   run — it didn't here, but this should not be assumed a priori.**

### On the manual-uncertainty-inflation technique (not attempted)

Per the runbook and this task's own instruction, uncertainty inflation is only valid
with a real, prior-derived (never invented) inflation factor. No such factor exists for
33S16O specifically: 34S16O's ADR-0005 12.5x factor came from 34S16O's own ADR-0003
combination-difference test on *34S16O's* `03SaMcTh` data (a different isotopologue's
different source-pair discrepancy); ADR-0004's own 33S16O pre-check RMS≈320 figure is
explicitly disclosed there as an unreliable upper bound (pre-dating the `ef_upper`
node-identity bug fix) and measures a different bridged network (mw sources bridged
into 22HeStLy via a full N-to-F conversion of the mw side) than what this run tested.
Reusing either would be inventing a transfer this repo's own anti-fabrication rule
forbids. This is also now moot substantively, not just procedurally: with 0 wrong/0
very-bad lines already, there is nothing in this network's real-bootstrap output that
uncertainty inflation would be fixing.

## Verdict

**Real `Marvel4.1.x` bootstrap validates the merged network — `22HeStLy` +
`15DrHiMo` + `96KlSaBe` genuinely and robustly self-consistent, `03SaMcTh` remains
safely disconnected.**

- **The merged network validates, not just the fallback**: 4508 levels / 29182
  transitions, 0 wrong, 0 very bad, reproducible across both a default bootstrap and a
  10x-deeper bootstrap. Unlike 34S16O/36S16O, there is no separate riskier "merged"
  topology being rejected in favor of a safer fallback — the one buildable topology for
  33S16O simply passes.
- **ADR-0004's pre-check conflict (RMS=317, max=1358) is NOT confirmed by the real
  solver — it is explained, not reproduced.** Two compounding reasons, both already
  partly flagged in ADR-0004 itself: (1) that pre-check's own script
  (`optionB_nf_validation_22hestly.py`) was run *pre-fix* for the `ef_upper`
  node-identity bug, which ADR-0004 explicitly disclosed spuriously merges ~44% of
  distinct upper levels and inflates residuals as "an upper bound, not a final result";
  (2) `22HeStLy`'s own blanket stated uncertainty (0.05 cm-1 ~= 1499 MHz) is enormous
  relative to `15DrHiMo`/`96KlSaBe`'s sub-MHz-to-few-hundred-kHz precision, so real
  discrepancies between them that would fail a tighter/differently-normalized
  fixed-uncertainty test (as the pre-check's own dense least-squares RMS statistic is)
  fall comfortably inside `22HeStLy`'s own uncertainty once evaluated the way
  `Marvel4.1.x`'s real bootstrap solver (using each source's own *stated* uncertainty
  as the pass/fail threshold, per `BadLines.txt`) actually evaluates it. This matches
  the same qualitative pattern ADR-0004 itself flagged for Brady et al. (2024)'s real
  32S16O network: a real MARVEL solve can validate what a simplified fixed-uncertainty
  script flags, without either result being "wrong" — they are different, and the real
  binary is the authoritative one for this pipeline's actual deliverable.
- **Incremental-attribution result: no source dominates badness, because there is no
  badness to attribute.** `22HeStLy` alone is not even a single connected component
  (splits into two, ~2250-level halves); `15DrHiMo`'s 21 transitions are what bridge
  them into one 4508-level network; `96KlSaBe`'s 24 transitions add pure redundant
  coverage on top (same level count, +24 transitions) — and the wrong/very-bad count
  stays at exactly 0 through every one of these additions. This is a materially
  different, cleaner result than 34S16O's ADR-0008 (99.6% of that network's badness
  traced to `22HeStLy`) and confirms this isotopologue's specific `22HeStLy` data
  (29137 transitions, same 0.05 cm-1 blanket uncertainty convention) is not exhibiting
  the same calibration problem here — plausibly because the redundant-loop density
  that exposes `22HeStLy`'s miscalibration for 34S16O (12 sources, 32678 transitions)
  simply isn't reached by 33S16O's much sparser 3-source, 29182-transition network; this
  is an observation worth flagging for whoever next works on `22HeStLy`'s overall
  cross-isotopologue calibration, not a contradiction of ADR-0005/ADR-0008's 34S16O
  finding.
- **`03SaMcTh` cannot be validated or invalidated by this run** — it never connects to
  anything, by construction (real N vs. dummy N slot). Its own internal structure (9
  small star components, no closed loops) has no redundancy to check either. This
  remains a genuine, disclosed, scoped-out limitation, not a finding.

## Consequences

- **Final deliverable**: the merged NQN=6 network (`22HeStLy`+`15DrHiMo`+`96KlSaBe`,
  4508 levels / 29182 transitions, `.scratch/so-33s16o-marvel/fallback/` — "fallback"
  and "attempt1" are the same file/result for this isotopologue, see above) is safe to
  use as 33S16O's MARVEL solve, including `03SaMcTh`'s 22 transitions kept structurally
  disconnected (N/hyperfine-labeled, NQN=6 dummy-`-`-padded, per
  `.scratch/so-33s16o-marvel/build_fallback.py`).
- **`03SaMcTh`'s eventual incorporation is a real, scoped-out future option, not
  attempted here**: implementing a genuine N-to-F conversion for its data (discarding
  its real resolved nuclear-hyperfine detail to produce a synthetic unresolved-electronic
  F1/F2/F3 label matching the other three sources' scheme, analogous to what 34S16O's
  now-superseded ADR-0002/0003 formula attempted) is the only path to ever merge it, and
  was out of scope for this dummy-padding-convention run.
- **ADR-0004's 33S16O pre-check numbers (RMS=317/max=1358) should not be cited as this
  isotopologue's current network-quality status going forward** — this ADR's real,
  bug-free, real-binary result (0 wrong, 0 very bad) supersedes it for that specific
  purpose; ADR-0004's own literature-research findings (formula rejection history,
  33S16O's now-complete higher-order constant set from `74Ti_SO_constants`) are
  untouched and remain valid.
- **Environment gotcha, worth carrying forward** (candidate for the runbook's "Known
  environment gotchas" section): a concurrent session was found actively running a
  36S16O bootstrap study in the shared `/mnt/c/Code/versions_MARVEL/Marvel4.1.x/`
  directory at the same time as this run (confirmed via `ps aux`). `Marvel4.1.x` is
  statically linked with no cwd-relative dependencies (`ldd` confirms "not a dynamic
  executable") but always writes its fixed-name outputs
  (`EnergyLevels.txt`/`Components.txt`/`CheckTransitions.txt`/`BadLines.txt`/
  `AVTable.txt`/`reviveTRs.txt`) to its own cwd — running two sessions' batch scripts in
  that same shared directory concurrently would have clobbered each other's outputs.
  This run worked around it by copying the binary into an isolated
  `.scratch/so-33s16o-marvel/bin/Marvel4.1.x` and running from there instead. Future
  concurrent isotopologue runs should do the same defensively rather than assuming
  exclusive access to the shared binary directory.
- Also worth carrying forward: this session's shell was already native WSL (no
  `wsl.exe` wrapper needed, confirmed via `uname`), so the runbook's ~10+-minute
  per-`wsl.exe`-invocation latency did not apply here — all 7 runs on this
  29204-transition network completed in well under a minute total. Future agents should
  check their own shell environment before assuming the `wsl.exe`-wrapper latency
  applies.
