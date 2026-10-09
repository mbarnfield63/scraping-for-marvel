# ADR-0002 (REJECTED — SO only): Derive e/f parity from selection rules where a paper leaves it unresolved

## Status

REJECTED (downgraded from DRAFT 2026-09-16). CLAUDE.md's existing Parity rule ("never
derive e/f from J-value parity or branch type") governs all extraction and all
combiner work, permanently for SO absent new evidence. Downgraded on the strength of a
third, independent failure of the same underlying F1/F2/F3<->N correlation — see
`docs/adr/0003-nf-conversion-validation-so.md`, which found the same formula produces
200-4000x-uncertainty residuals in a real network cross-check against 32S16O's
microwave data (a different isotopologue and a different test method than either
attempt below). Three independent angles, zero successes beyond the trivially-
unambiguous Sigma=0/F2 case. Don't retry without a new primary source resolving the
intermediate-coupling mixing directly.

## Context

CLAUDE.md's blanket Parity rule exists because e/f-from-branch/N-parity is Hund's-case-
and molecule-dependent — a wrong sign convention silently mislabels real measured
levels with no downstream check. That's a correct default for a pipeline spanning
arbitrary molecules and states.

For SO specifically, three electronic transition systems are in scope
(`molecules/SO/csv/22HeStLy_SO_merged.csv`: `C3Pi-X3Sigma-`, `B3Sigma--X3Sigma-`;
`87BuLoHa`/`97KlBeWi`: `a1Delta` rotational bands): X3Sigma- and b1Sigma+ (Σ states,
no Λ-doubling — parity is a fixed function of N, not a genuine two-way ambiguity) vs.
C3Pi and a1Delta (Λ≠0, real Λ-doubling — two physically distinct near-degenerate
sublevels per N, which is where the e/f label carries actual information and where a
paper can leave it unresolved).

The disconnected e/f components combiner reports for 33S16O/36S16O (and partially
34S16O) are *not* rows with blank/unresolved parity — 22HeStLy already states e/f for
essentially every row. They're two real, separately-measured E1-allowed sub-networks;
no relabeling recovers transitions that were never observed between them. That
question (bridging via an independent forbidden/magnetic-dipole line) stays a
literature-search problem, out of scope for this ADR.

This ADR instead targets the *other* case: rows where a paper doesn't resolve parity
at all (`87BuLoHa` a1Delta, tagged `parity: unresolved`, mechanically expanded into a
same-wavenumber e/f pair by `split-parity`) or a future SO source with the same gap.
If the real target sublevel is derivable from the branch (P/Q/R) and N/J via the
electronic states' known Hund's-case coupling, that's information the paper's own
branch assignment already encodes — not a guess — and the split-parity duplicate-pair
workaround is strictly worse (it fabricates a fake degeneracy where the paper actually
observed only one specific sublevel).

## Proposed rule (SO-scoped)

1. Do not hardcode a parity formula from memory. Source the actual sign/assignment
   convention from Brown, Hougen, Huber, King, Merer, Ramsay, Rostas & Zare, *J. Mol.
   Spectrosc.* **55**, 500 (1975) ("Labelling of parity doublet levels in linear
   molecules") — the standard reference every SO paper in this collection itself
   follows — applied per electronic state (C3Pi, a1Delta) using that state's own Λ, S
   and the specific Hund's case coupling regime at the N/J range in question (SO's
   low-N X3Sigma- state is case (b); some excited-state ranges may run case (a)/(b)
   intermediate — check per paper, don't assume).
2. **Validation gate, mandatory before trusting it on any blank/unresolved row**:
   apply the derived rule to every row a paper *already* resolves explicitly (22HeStLy
   is >99% resolved; some 97KlBeWi/87BuLoHa a1Delta rows are resolved outside the
   unresolved-tagged subset) and require an exact match, zero mismatches, across all
   of them. Any mismatch falsifies the candidate rule (wrong sign convention, wrong
   coupling case assumption, etc.) — fix and re-validate, or abandon it for that state.
3. Only once a state's rule clears step 2 with zero mismatches may it be applied to
   that same state's unresolved rows — and only to assign the parity label, never to
   collapse or discard the paper's own `parity: unresolved` / split-pair data; the
   derived label replaces the guess, the underlying measured wavenumber is untouched.
4. Record the validated formula, its source-page citation, and the validation
   mismatch count (must be 0) in this ADR before flipping Status to ADOPTED.

## Validation run (2026-09-14) — gate NOT cleared, partial signal

Tested the standard Hund's-case (b) Σ-state parity rule against `22HeStLy`'s own
already-resolved `ef_lower` labels (X3Sigma-, 97163 rows), using:

- parity(N) = -(-1)^N  (Σ- sign)
- N derived from F_lower + J_lower via the textbook triplet-Σ convention
  F1: J=N+1, F2: J=N, F3: J=N-1 (F_lower has no F3 rows in this dataset)
- e-label rule (Brown et al. 1975): e if parity = +(-1)^(J-S), S=1

Result, split by branch:

| F_lower | rows | mismatches | verdict |
|---|---|---|---|
| F2 (N=J) | 32,856 | **0** | exact match — real, falsifiable, passed |
| F1 (N=J±1, both signs tested — identical result since they share parity) | 64,307 | ~32,164 (≈50%) | no correlation — formula wrong for F1 |

F2's zero-mismatch result across 32,856 independently-labeled rows is a strong
positive signal that the underlying selection-rule logic is real and mechanically
derivable, not coincidence. F1 failing at ~50% (uncorrelated with J-parity and only
weakly dependent on v_lower parity, 47-53% split) means the assumed F1↔N mapping is
wrong — most likely SO's X3Sigma- state has enough spin-rotation/case (a)-(b) mixing
at these v,J ranges that the simple "F1 is always the N=J-1 branch" textbook rule
doesn't hold uniformly across this dataset's full v/J range, or this paper's own F1/F2
numbering convention isn't the standard energy-ordered one assumed here.

**Verdict: gate not cleared.** Do not use this to derive e/f for any row. F2's clean
pass is worth keeping as evidence the approach is sound in principle; F1's failure
needs the real F1↔N assignment nailed down from a primary source (the paper's own
stated convention, or a case (a)/(b) treatment specific to this v/N range) before
retrying — not another guessed sign flip. C3Pi (the Λ-doubled upper state, where the
real ambiguity lives) wasn't tested yet since the lower-state check needed to pass
first as a prerequisite.

## Follow-up (2026-09-14) — checked the paper's actual convention; two dead ends found

**F1/F2/F3 is defined by Σ (spin projection), not a J=N±1 offset.** Sourced directly
from `molecules/SO/papers/parse_22hestly_lines.py`'s header comment, which quotes the
file's own column documentation (Heays, Stark, Lyons, de Oliveira, Lewis & Gibson
2022, Zenodo 7423903): `Σ=+1/0/-1 -> F1/F2/F3`. My original J=N±1 assumption above was
an unsourced textbook guess — exactly the mistake this ADR's own rule 1 says not to
make.

Re-ran the validation conditioning on the correct index (Σ, J-parity):

- Σ=0 (F2): still 0/32,856 mismatches — trivial in any coupling case, since Σ=0 means
  N=J with no ambiguity regardless of how mixed the coupling is.
- Σ=+1 (F1): still ~51/49 split (16,324e/15,776f and 16,340e/15,867f across the two
  J-parities), no better than before. This rules out "wrong offset sign" as the
  explanation. N is genuinely not a fixed function of (Σ,J) for these levels — SO's
  X3Σ⁻ is intermediate-coupled enough at this v/J range that the authors' own `efpp`
  values come from their effective-Hamiltonian eigenvector fit, not a closed formula.
  Reproducing it would mean re-deriving their fit, not deriving a rule.

**Separately, and more decisive: there is no ground truth to validate an a1Delta rule
against anyway.** Checked both a1Delta datasets in the SO corpus —
`molecules/SO/csv/87BuLoHa_merged.csv` (116 rows) and `97KlBeWi_SO_merged.csv` (64
rows) — both are 100% tagged `parity: unresolved`, meaning every row is already a
`split-parity`-manufactured identical-wavenumber e/f duplicate pair, not a
paper-resolved label. Nowhere in this molecule's corpus does a paper state a real,
independently-verified a1Delta e/f assignment. The mandatory validation gate (§2 above)
cannot be cleared for the one state that actually motivated this ADR (87BuLoHa's
unresolved rows) — there's nothing to check any candidate formula against, correct or
not.

**Conclusion: close this route for SO.** X3Σ⁻'s F1/F3 sublevels aren't hand-derivable
without redoing the source paper's own fit, and a1Delta has no resolved data to
validate against even in principle. Don't retry without either (a) an independent
paper that resolves a1Delta parity directly, or (b) the source code/fit outputs behind
22HeStLy's effective-Hamiltonian analysis (out of scope — that's their unpublished
model, not raw data). Status stays DRAFT; recommend downgrading to REJECTED unless a
new a1Delta source surfaces.

## Consequences (if promoted)

- Recovers real connectivity currently lost to the `split-parity` duplicate-pair
  workaround for any SO source with unresolved a1Delta (or similar Λ≠0 state) parity.
- Does not touch the genuine multi-component disconnects (33S16O/36S16O e/f-ladder
  split) — those are separately-measured networks, not a labeling gap; see Context.
- If step 2's validation ever fails for a given state, this ADR stays DRAFT for that
  state indefinitely — don't retry the same formula without new evidence, same
  precedent as ADR-0001's OCR decision.

---

## Draft global rule (do not adopt yet — placeholder for CLAUDE.md's Parity rule section)

Only promote this if SO's validation (above) clears with 0 mismatches on a real state,
and only generalize the *procedure*, not SO's specific formula — every molecule/state
needs its own sourced convention and its own validation gate re-run from scratch.

> **Selection-rule parity derivation (opt-in per molecule/state, validated)**: a
> molecule's `docs/agents/reference.md` (or its own ADR) may document a sourced e/f
> derivation for a specific electronic state, cited to a standard reference (e.g.
> Brown et al. 1975) and confirmed against that state's own already-resolved rows with
> zero mismatches. Only then may `parity: unresolved` rows for that exact state use
> the derived label instead of the duplicate-pair split. Extraction still records
> `parity: unresolved` as today — this is a later, mechanical, validated step, same
> "extraction records, a later mechanical step transforms" pattern as the Unit rule's
> `reconcile` step. Never apply a derivation that hasn't cleared its own molecule's
> validation gate; the blanket "never derive e/f from branch/J-parity" default stays
> in force for every molecule/state without one.
