# scraping-for-marvel

Turn spectroscopy research papers into **MARVEL** input files.

MARVEL (Measured Active Rotational-Vibrational Energy Levels) needs a tidy,
tab-separated list of measured transitions. This repo helps you pull those
numbers out of published papers (which are usually scanned PDFs with big
tables) and write them in the exact format MARVEL expects.

The hard part — reading messy tables correctly — is done for you by an
OCR service and by Claude Code. **You do not need any AI or programming
experience.** You run a couple of commands and answer questions when asked.

---

## What you need first (one-time setup)

1. **Python 3.12+** and **[uv](https://docs.astral.sh/uv/)** (a Python installer).
   Install uv, then in this folder run:
   ```bash
   uv sync
   ```
   That installs everything the scripts need.

2. **A MinerU account** (free) for the OCR step. Sign up at
   [mineru.net](https://mineru.net), then either:
   - install the MinerU desktop app and sign in (the scripts find your token
     automatically), **or**
   - copy your API token and set it once:
     ```bash
     setx MINERU_API_TOKEN "your-token-here"
     ```

3. **Claude Code** — the tool you're likely already reading this in. It runs
   the "check and extract" step with you, interactively.

That's it. No servers, no models to download.

---

## Start from the example

Every molecule uses the same four-folder layout. There's a ready-made template
at **`molecules/example_molecule/`** — open its
[README](molecules/example_molecule/README.md) to see what each folder is for.

**To start a new molecule, copy that folder and rename it.** Your copy stays on
your machine only (it's kept out of git), so your papers and data stay local.

## The workflow, one paper at a time

Say you're doing the molecule **CS2** and a paper called **74MaSa**.

### 1. Put the paper in place
Copy the template to a folder named for your molecule, then drop the PDF into
its `papers/`:
```bash
cp -r molecules/example_molecule molecules/CS2
```
Copy `74MaSa_CS2.pdf` into `molecules/CS2/papers/`.

### 2. Read the PDF with OCR
```bash
python scripts/mineru_cloud.py molecules/CS2/papers --out-dir molecules/CS2/markdown
```
This sends every PDF in `papers/` to MinerU, waits, and saves the results
into `markdown/`. Each paper gets its own folder containing:
- `full.md` — the paper's text and tables
- `<paperID>_content_list.json` — where each table sits on the page

### 3. Check and extract (with Claude)
Ask Claude Code to work through the paper. It reads `full.md`, double-checks
any table cell that looks wrong against the actual page image, and writes the
numbers into CSV files under `csv/`. If a value is genuinely unreadable, it
marks it **UNREADABLE** rather than guessing — a wrong number silently
corrupts the result, so it never invents one.

### 4. Merge the pieces
```bash
python scripts/csv_to_marvel.py merge CS2 74MaSa
```
Combines the CSV pieces into one file.

### 5. Review (safety gate)
Claude runs a reviewer that checks the merged data (valid quantum numbers,
sensible wavenumbers, no duplicates, missing rows, etc.) and writes a report
to `csv/74MaSa_review.md`. If the report says **REQUIRES MANUAL REVIEW**,
stop and look at the flagged rows before continuing.

### 6. Write the MARVEL file
```bash
python scripts/csv_to_marvel.py format CS2 74MaSa
```
Produces the final tab-separated `.txt` file(s) in `molecules/CS2/output/` —
one per isotopologue. **These are your results.**

---

## Where everything lives

```
molecules/<molecule>/
├── papers/     the source PDFs you put in
├── markdown/   OCR output (one folder per paper)
├── csv/        extracted numbers + review reports
└── output/     the finished MARVEL .txt files  ← the goal
```

---

## Good to know

- **Free tier limits:** MinerU allows 2000 pages/day and 10,000 files/day —
  plenty for normal use. These are published papers, so uploading them is fine.
- **Never trust a guessed number.** The whole point is accuracy. An
  `UNREADABLE` flag is always better than a wrong digit.
- **More detail** for each step lives in `CLAUDE.md`, which also tells Claude
  Code how to run the pipeline.
