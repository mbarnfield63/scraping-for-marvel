# ADR-0007: SO 32S18O X3Sigma- N/F conflict check — no coexisting-pair conflict found

## Status

**RESOLVED — no conflict to test.** Checked directly against this repo's current corpus
(all 7 canonical `molecules/SO/output/SO_32S18O_*.txt` files plus
`molecules/SO/combined/SO_32S18O_combined.txt`): every X3Sigma- source for 32S18O already
uses the F1/F2/F3 fine-structure label uniformly. No file retains N (rotational angular
momentum) as a QN column. There is therefore no coexisting N-labeled/F-labeled source pair
for 32S18O's X3Sigma- state, and consequently nothing for the
`docs/agents/marvel4-bootstrap-runbook.md` real-bootstrap procedure (ADR-0005's method) to
test. **ADR-0004's "five of five" tally (32S16O, 34S16O, 33S16O, 36S16O tested;
32S17O out of scope, no F source) is confirmed correct as written — 32S18O is correctly
not a sixth.** No Marvel4.1.x run was performed; per the task's own instruction, running
one against data with no genuine conflict would fabricate an attempt table against a
non-problem.

## Context

This ADR was chartered to check whether 32S18O has the same X3Sigma- N-vs-F
quantum-number-labeling conflict as 32S16O/33S16O/34S16O/36S16O (ADR-0002/0003/0004/0005),
since ADR-0004's sweep never explicitly tested 32S18O. Per the task's own framing: verify
independently before assuming a conflict exists, and don't invent a bootstrap test where
none is needed.

## Method

Checked every 32S18O X3Sigma- source directly (not by citation):

| source | tag | rows (32S18O) | canonical output QN scheme | native paper convention |
|---|---|---|---|---|
| Tiemann 1974 | `74Ti` | 5 | `state,v,J,F,ef` (F-only, no N) | **N-native** — CSV notes cite CDMS raw codes in `J'N'` form |
| Bogey, Demuynck & Destombes 1982 | `82BoDeDe` | 12 | `state,v,J,F,ef` | **N-native** — CSV notes: "header label J,N-J',N'" |
| Tiemann 1982 | `82Ti` | 6 | `state,v,J,F,ef` | **N-native** — paper text itself (full.md line 92): *"we succeeded in observing the weak transition J, N = 1, 1–1, 0"* |
| Burkholder et al. 1987 | `87BuLoHa` | 230 | `state,v,J,F,ef` | **F-native** — paper reports F1/F2/F3 directly (same IR source used as the F-labeled reference in ADR-0002/0003 for other isotopologues) |
| Lovas et al. 1992 | `92LoSuOg` | 1 | `state,v,J,F,ef` | **N-native** — CSV note: "label format N'_J'<-N''_J'' per paper header" |
| Klaus et al. 1996 | `96KlSaBe` | 23 | `state,v,J,F,ef` | **N-native** — CSV note: "label format N'J'<-N''J''" |
| Klaus, Belov & Winnewisser 1997 | `97KlBeWi` | 20 | `state,v,J,F,ef` (a1Delta, not X3Sigma-) | singlet state, F1 assigned trivially (no N concept) |

All six X3Sigma- sources' **canonical output files** use the identical `state, v, J, F,
ef` column schema — none carries an `N` column. Spot-checked the N→F conversion arithmetic
directly against `SO_algorithm.py`'s formula (`N==J`->F2, `N==J-1`->F1, `N==J+1`->F3,
algebraically identical to Brady et al. 2024 Eq. 1) for several rows with numeric N values
recoverable from the extraction notes — e.g. `82Ti.1`: paper's own "J,N=1,1-1,0" ->
upper N=1,J=1 (N=J -> F2, matches recorded `F2`); lower N=0,J=1 (N=J-1 -> F1, matches
recorded `F1`). `74Ti.1`: CDMS raw code `21-10` (J'=2,N'=1 <- J''=1,N''=0) -> upper N=1,J=2
(N=J-1 -> F1, matches); lower N=0,J=1 (N=J-1 -> F1, matches). Conversion is arithmetically
consistent everywhere checked — **not a formula bug**.

Also checked 24BrYuTe (Brady et al. 2024) directly, since the task flagged it as possibly
already covering 32S18O cleanly. Correction to the task's framing: **24BrYuTe's own Table
2 and its MARVELized network (§3.4, full.md line 111) cover only 32S16O** ("The
$^{32}S^{16}O$ spectroscopic network was built through input of 50 106 rovibronic
transitions into MARVEL from the 29 data sources outlined in Table 2"). 32S18O is
mentioned only in prose (full.md line 87, isotopologue literature survey) listing which
papers have measured it (Tiemann 1974, Bogey et al. 1982, Tiemann 1982, Burkholder et al.
1987, Klaus et al. 1996, Klaus/Belov/Winnewisser 1997 — matches this repo's own 6-source
X3Sigma- corpus exactly) — Brady et al. never ran 32S18O through their own MARVEL/N-to-F
pipeline at all. The task's citation of "ADR-0004 line ~219-221" for this claim was
checked and refers to a different paper (82BoDeDe's own Table 2, in ADR-0004 Section 5),
not to 24BrYuTe's Table 2 — a misattribution in the task framing, corrected here.

## A separate, previously-undocumented finding (flagged, not acted on)

**The reason no N/F conflict is visible is that an N-to-F conversion has already been
silently applied, uniformly, to every N-native 32S18O source's *canonical output file*
during extraction** — unlike 34S16O, where ADR-0005 found the canonical `03SaMcTh` output
correctly stayed N-labeled (only a separate downstream CSV artifact had been
pre-converted, an "unlogged process" per PROCESS.md Appendix item 1). For 32S18O, the
conversion is baked directly into `molecules/SO/output/SO_32S18O_{74Ti,82Ti,82BoDeDe,
92LoSuOg,96KlSaBe}_*.txt` themselves, with no note in any row disclosing that a conversion
happened (the extraction notes describe the paper's native N-based table format, then
record an F value with no stated derivation step).

This is not itself the conflict this ADR was chartered to check for (there is no
coexisting N-labeled counterpart file to reconcile against — nothing for a MARVEL
bootstrap run to test), and it is not evidence of a wrong formula application (the
arithmetic checked out everywhere sampled above). But it does mean:

- 32S18O's F1/F3-labeled rows from these five sources carry the same unvalidated-formula
  risk ADR-0002 found the naive Brady Eq. 1 formula has for F1/F3 assignments specifically
  (≈50% mismatch rate against real resolved labels for other isotopologues, attributed to
  intermediate-coupling mixing at higher J that the asymptotic N<->F map does not capture)
  — F2 rows (N=J exactly) are unaffected, per ADR-0002's own finding that the F2 case is
  unambiguous in any coupling regime.
- There is currently no way to cross-check this for 32S18O specifically, since the native
  N values were not preserved in the canonical output — a real, disclosed data-provenance
  gap, not a fabrication (the extraction notes do preserve enough information, e.g. CDMS
  raw codes, paper table headers, to reconstruct the original N values if ever needed).
- This was evidently a deliberate extraction-time choice (to present all X3Sigma- sources
  in one uniform F-labeled schema, matching Brady et al.'s own published convention) made
  before ADR-0002/0003/0004 diagnosed that this exact formula fails validation elsewhere —
  it predates, and was not informed by, that later finding.

**Recommendation for a future agent** (not performed here — out of scope for this ADR,
which is specifically chartered to check for a conflict, not to re-litigate 32S18O's
extraction policy): decide whether 32S18O's `74Ti`/`82Ti`/`82BoDeDe`/`92LoSuOg`/`96KlSaBe`
canonical output files should be re-extracted to restore native N-labeling (consistent
with how 34S16O's `03SaMcTh` is currently handled), which would surface this same N/F
question for 32S18O the way it now exists for the other four isotopologues — rather than
leaving an unvalidated conversion silently baked in with no way to check it. Do not treat
the current uniform-F state as validated; it simply was never tested, because it was never
visible as a conflict.

## Consequences

- No change to any pipeline file, no Marvel4.1.x run performed, no new `.scratch/`
  working directory created — nothing to test.
- ADR-0004's "five of five" isotopologue tally stands unchanged and is now independently
  confirmed correct with respect to 32S18O specifically.
- The silent N->F conversion finding above is a new, disclosed, scoped-out issue for
  32S18O's extraction provenance — flagged here so a future agent doesn't have to
  re-discover it, but not actioned in this session per this ADR's own narrow charter.
