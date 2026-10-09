# MARVEL Input Creation Pipeline

Extracts measured, quantum-number-assigned transitions from spectroscopy papers into MARVEL input
files. The papers come from `/mnt/c/Code/MARVEL_literature` (`<mol>/<mol>_handoff.tsv`).

- Workflow: the `marvel-pipeline` skill. Column schemes, paper/line IDs and output names:
  `.claude/skills/marvel-pipeline/format.md`. Extraction rules: `.claude/agents/extractor.md`.
- **Never fabricate a value.** A wrong number silently corrupts the spectroscopic network, and no
  downstream physical check catches it. An `UNREADABLE` or `REQUIRES MANUAL REVIEW` flag is always
  better than a guess.
- Commits run `.githooks/pre-commit` (compile check plus every self-test). Keep it passing.

## Operating Rules

### 1. Initialize
When the user says **"get up to speed"**, invoke the `get-up-to-speed` skill. It reads the Obsidian state file at:
`C:/Code/Obsidian/PhD/MARVEL scraping/MARVEL scraping_state.md` to reconstruct full context.

### 2. Log & Save
When reaching a milestone or when the user says **"save state"**, invoke the `save-state` skill. It overwrites the Obsidian state file (`C:/Code/Obsidian/PhD/MARVEL scraping/MARVEL scraping_state.md`) with a clean update (see Rule 4 format) and appends a summary of work done to the log file (`C:/Code/Obsidian/PhD/MARVEL scraping/MARVEL scraping Log.md`). Never change any other files within `C:/Code/Obsidian/`.

### 3. Never delete untracked files outside your own run
Never delete, move-as-cleanup, or overwrite an untracked file in this repo unless it was created by the current agent/session's own run (e.g. a temp file you just wrote to your own scratchpad). Untracked files (`git status`) are frequently in-progress user work, not junk — `git` gives no recovery path for them if deleted. This applies even to "obviously superfluous"-looking files (stray `.txt`/`.json` scratch files at the repo root, etc.) and even when doing routine cleanup. If a file looks like leftover clutter and you did not create it in this run, leave it alone or ask the user before touching it.

One exception: when resuming an extraction fan-out, move an unfinished paper's (no `csv/<paperID>.done`) `csv/<paperID>_batch*.csv` into `csv/partial/<YYYYMMDD_HHMMSS>/` before relaunching its extractor. Move, never delete (see `marvel-pipeline` skill, Fan-out).

### 4. Obsidian State File Format
When writing to `C:/Code/Obsidian/PhD/MARVEL scraping/MARVEL scraping_state.md`, always overwrite with:

```
# MARVEL scraping — Claude State

**Last Modified:** YYYY-MM-DD HH:MM

**Completed:**
- Molecule: 
- Isotopologues:
- Transitions: 

**Next Steps / Blockers:**
- Exactly what needs to be tackled next session or the papers required to be analysed by the user for potential further scraping.
```

## Agent skills

- Issues: markdown files under `.scratch/` (`docs/agents/issue-tracker.md`).
- Triage labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix` (`docs/agents/triage-labels.md`).
- Domain docs: one `CONTEXT.md` plus `docs/adr/` at the repo root (`docs/agents/domain.md`).
