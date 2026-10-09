# MARVEL4.1.x real-bootstrap validation runbook

Generic method for testing whether a source's QN-scheme conversion (e.g. N↔F relabeling)
or any other cross-source reconciliation survives a real `Marvel4.1.x` bootstrap run,
rather than just a fixed-uncertainty pre-check. Distilled from the 34S16O N/F test
(ADR-0005, `.scratch/so-34s16o-marvel/PROCESS.md`) — that write-up is 34S16O-specific data;
this one is the reusable skeleton. Re-derive every number below per isotopologue/molecule;
nothing here is a result, only a procedure.

## 0. Preconditions

- A fixed-uncertainty pre-check (script-level, not the real binary) has already flagged a
  specific conflict worth testing with the real solver — don't reach for this runbook as
  step 1.
- Canonical per-source `molecules/<mol>/output/*.txt` files are current for every source in
  the network (check mtimes / re-run `csv_to_marvel.py format` if stale).
- `scripts/to_marvel4_input.py` run on every file before feeding `Marvel4.1.x` — the
  pipeline's native 2·NQN+3 column format is missing `Marvel4.1.x`'s required `uncorig`
  column (2·NQN+4). This is permanent/systemic, not isotopologue-specific — always needed.

## 1. Re-verify the formula/logic first, before any run

Check the conversion function itself (e.g. `SO_algorithm.py`'s `N_to_F`) against the
source paper's own equation, by hand, on paper. Cross-check a few already-converted rows
in the CSV against the formula directly. Log whether the formula is correct — a real bug
here means stop, fix, and this whole runbook is moot.

## 2. Set an attempt budget up front

Agree (with user, or from a prior ADR) how many genuinely distinct techniques to try
before falling back to the safe default. 3 is a reasonable default. "Distinct" means a
different technique, not the same run repeated:
- default bootstrap merge (`-b`, 100 iterations)
- manual uncertainty inflation on the disputed source (Brady-footnote-(a)-style),
  inflation factor sourced from a prior CD-test result if one exists — never invented
- increased bootstrap depth (`--bootiter <N>`, e.g. 10x default)
- (if available) other techniques from a relevant methodology paper — check before
  declaring the budget exhausted

## 3. Prepare the fallback regardless

Build the disconnected/canonical/unconverted network in parallel, before or alongside the
attempts — don't leave it for after all attempts fail. It's the safe-default deliverable
if nothing validates.

For a source with a QN scheme other sources don't share (e.g. N-only vs F-only), keep it
structurally disconnected by padding the missing QN slot with a fixed dummy token (e.g.
`-`) that can never collide with a real value — never merge by leaving a slot blank/zero.

## 4. Running Marvel4.1.x

- Reachable via `wsl.exe -e bash -lc "..."` if not on native Linux/WSL interactive shell.
- **Batch every planned invocation into as few `wsl.exe` calls as possible** — some
  sandboxed environments pay large (many-minute), seemingly constant per-invocation
  latency, not a one-time cold start. Don't assume an early slow command is hung.
- Flags (`Source_Code_CPP/MARVEL4.1.cpp` `main()`): `--nqn/-n <int>`, `--trans/-t <path>`,
  `--segment/-s <path>`, `--bootstrap/-b`, `--bootiter <int>` (implies `-b`), `--minsize
  <int>` (default 200).
- **Never use `--minsize 1`** — crashes with `wrong decomp 1` (Eigen Cholesky failure on a
  degenerate 1x1 component). Use the default 200, or ≥2 if you need small components
  visible.
- Outputs (`EnergyLevels.txt`, `Components.txt`, `CheckTransitions.txt`, `BadLines.txt`,
  `AVTable.txt`, `reviveTRs.txt`) land in the binary's cwd and get overwritten each run —
  copy out to a per-attempt subfolder immediately after each run.
- `BadLines.txt` severity (`getCategory()`, `MARVEL4.1.cpp` ~line 66): `wrong` at
  `|residual|/uncertainty > 1`, escalating to `VERY BAD` (>10), `VERY BAD_100` (>100),
  `VERY BAD_1000` (>1000).

## 5. What to compare, per attempt

For each attempt (including fallback), record:
- main component size (levels / transitions)
- total wrong-line and very-bad-line counts (and % of network)
- the disputed source's own flagged status specifically — does its transition(s) connect
  to the rest of the network at all? (check `Components.txt` — an isolated 2-node
  component means it can never be checked for consistency, converted or not)

Compare merged vs fallback: same main component + statistically similar bad-line rate ⇒
merging bought no connectivity, not worth the unresolved inconsistency it might introduce.
Bigger main component or resolved inconsistency ⇒ merging genuinely helped.

## 6. Separate finding-and-scope discipline

If a large fraction of network badness (check `CheckTransitions.txt` broken down by
source tag) traces to some other source entirely, unrelated to the thing you set out to
test — log it as its own separate open issue. Don't let it block or blur the verdict on
the specific question this run was chartered to answer.

## 7. Write the ADR

Standard ADR shape: Status (accept/reject + the *specific* reason, not just "rejected
again"), Context, Method/results table (one row per attempt + fallback), Verdict with
justification, Consequences (what's the final deliverable, what's flagged out-of-scope,
what should a future agent not re-attempt without first addressing X).

## Known environment gotchas (carry forward, don't rediscover)

- Missing `uncorig` column (§0) — fixed permanently by `to_marvel4_input.py`, always run it.
- `--minsize 1` crash (§4) — artifact of the flag, not the data.
- `wsl.exe` per-call latency in sandboxed sessions (§4) — batch calls.
- `Marvel4.1.x --help` hangs rather than erroring — don't rely on it; flags above are
  sourced from the C++ directly.
