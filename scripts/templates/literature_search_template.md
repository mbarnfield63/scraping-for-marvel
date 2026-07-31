# MARVEL Literature Search Prompt Template

For use with a research LLM (e.g. web-search-capable model) to survey the
literature for a molecule before starting the pipeline in CLAUDE.md. Copy the
prompt below into the research LLM, replacing only `[MOLECULE]` with the
target molecular formula (e.g. `SiS`, `CO2`, `H2O`). Nothing else should change.

---

MOLECULE = [MOLECULE]

Act as an expert molecular spectroscopist and data compiler for the ExoMol project. Your task is to conduct a comprehensive literature search to identify data required to construct a MARVEL (Measured Active Rotational-Vibrational Energy Levels) spectroscopic network for [MOLECULE].

### MARVEL Literature Search Rules & Constraints:
1. **Assigned experimental transitions only.** Include only studies reporting high-resolution, experimentally measured transition frequencies or wavenumbers with *explicit quantum-number assignments*.
2. **Exclude pure theory.** Strictly exclude purely theoretical/ab initio line lists, unassigned broad cross-sections, and raw unassigned spectra. A theoretical paper is only relevant if it supplies new quantum-number assignments for pre-existing experimental data.
3. **Full isotopologue coverage.** Proactively search for and include data on the parent isotopologue and all minor stable isotopologues of [MOLECULE].
4. **Full transition-type coverage.** Search across all relevant regions and mechanisms for [MOLECULE] — pure rotational (microwave/THz), rovibrational (IR fundamental and overtone/hot bands), and electronic (UV/Vis/near-IR band systems) — whichever apply to this molecule. If a category has no known measurements, state that explicitly rather than omitting it silently.

### Output Requirements:
1. **Condensed per-paper summaries.** For each qualifying paper, state:
   - The specific isotopologue(s) measured.
   - The spectral region and transition type(s) (e.g. pure rotational, fundamental/overtone rovibrational, or the specific electronic band/state pair).
   - The exact or estimated number of assigned lines available for the MARVEL network.
2. **Summary table.** A single Markdown table with exactly these columns, one row per paper (or per isotopologue within a paper if the counts differ):
   - Isotopologue
   - Study (First Author & Year)
   - Transition Type / Band
   - Number of Assigned Lines
   - DOI Link
3. **Coverage note.** After the table, one short line flagging any obvious gaps (e.g. an isotopologue or transition type with no located data) so follow-up searches can target them.
