"""
to_marvel4_input.py — Insert the missing `uncorig` column MARVEL4.1.x requires.

Background (verified 2026-09, see docs/adr and the SO 34S16O process write-up):
MARVEL4.1.x (C:\\Code\\versions_MARVEL\\Marvel4.1.x) parses each transitions-file
line positionally (Source_Code_CPP/MARVEL4.1.cpp, ~line 340-372):

    tokens[0]          -> wavenumber
    tokens[1]          -> uncorig   (the ORIGINAL, as-published uncertainty)
    tokens[2]          -> unc       (the uncertainty MARVEL's bootstrap reweights)
    tokens[3 .. NQN+2]        -> upper-state QN block (NQN tokens)
    tokens[NQN+3 .. 2NQN+2]   -> lower-state QN block (NQN tokens)
    tokens[2*NQN+3]           -> Ref/ID

i.e. it wants **2*NQN + 4** whitespace-delimited columns. This pipeline's own
canonical format (CLAUDE.md "MARVEL Input Format", csv_to_marvel.py `format`,
and every real file under molecules/<mol>/output/*.txt) only ever produces
**2*NQN + 3** columns: a single `uncertainty` column, no separate `uncorig`.
Confirmed against molecules/SO/reference_papers/32S-16O_MARVEL_trans.txt (Brady et al. 2024's
real, working MARVEL4.1 input for 32S16O) which has the full 14 columns for
their NQN=5 electronic-transition schema.

Without the 14th (here: Nth+1) column, MARVEL4.1 reads `Ref = tokens[2*NQN+3]`
out of bounds -> empty ID -> a later `basic_string::erase` out_of_range crash,
or silent corruption. This gap is systemic (every molecule/schema this pipeline
ever formats for MARVEL4.1.x), not specific to SO or any one isotopologue.

Fix: this pipeline has never tracked two independently-sourced uncertainty
values for any transition, so there is no real second number to put in
`uncorig`. Per the anti-fabrication rule, the only non-fabricated choice is to
duplicate the existing `uncertainty` column: `uncorig := uncertainty`. This
gives MARVEL4.1 a real starting point for its own bootstrap reweighting of
`unc` (tokens[2]) while leaving `uncorig` (tokens[1], never touched again by
MARVEL4.1's re-weighting -- see MARVEL4.1.cpp line ~484) equal to the one real
number this pipeline ever had for that line.

Usage:
    python scripts/to_marvel4_input.py <input.txt> [-o OUTPUT] [--nqn NQN]

    <input.txt> may be:
      - a canonical per-source file from molecules/<mol>/output/*.txt
        (tab-separated, header row: transition_wavenumber, uncertainty, ...,
        id/ID -- header is detected and dropped)
      - a header-less, already-assembled combined/segment-ready file like
        molecules/SO/combined/SO_34S16O_combined.txt (whitespace-separated,
        no header)

    Output is always header-less, single-space-delimited, one file MARVEL4.1
    can be pointed at directly with `-t`.

    --nqn is optional and only used to sanity-check column count (2*NQN+3 in,
    2*NQN+4 out); if omitted the script infers NQN from the input column count
    (must be odd: wavenumber + uncertainty + 2*NQN + id = 2*NQN+3).

Examples:
    python scripts/to_marvel4_input.py molecules/SO/combined/SO_34S16O_combined.txt \\
        -o .scratch/so-34s16o-marvel/attempt1/SO_34S16O_trans_marvel4.txt

    python scripts/to_marvel4_input.py molecules/SO/output/SO_32S16O_03KiYa_SO_*.txt \\
        -o /tmp/03KiYa_marvel4.txt
"""

import argparse
import sys
from pathlib import Path


def _split(line: str) -> list[str]:
    return line.strip().split()


def _looks_like_header(fields: list[str]) -> bool:
    # Column 0 (wavenumber) must be numeric on a real data row.
    try:
        float(fields[0])
        return False
    except (ValueError, IndexError):
        return True


def convert(in_path: Path, out_path: Path, nqn: int | None) -> tuple[int, int]:
    raw_lines = in_path.read_text(encoding="utf-8").splitlines()

    data_lines = []
    for line in raw_lines:
        if not line.strip():
            continue
        fields = _split(line)
        if _looks_like_header(fields):
            continue
        data_lines.append(fields)

    if not data_lines:
        raise SystemExit(f"No data rows found in {in_path}")

    ncols_in = len(data_lines[0])
    for i, fields in enumerate(data_lines, 1):
        if len(fields) != ncols_in:
            raise SystemExit(
                f"{in_path}: row {i} has {len(fields)} columns, expected {ncols_in} "
                f"(ragged input -- fix the source file before converting)"
            )

    inferred_nqn = (ncols_in - 3) // 2
    if (ncols_in - 3) % 2 != 0:
        raise SystemExit(
            f"{in_path}: {ncols_in} columns is not of the form 2*NQN+3 "
            f"(wavenumber, uncertainty, <NQN upper>, <NQN lower>, id) -- "
            f"is this already a 14+-column MARVEL4-ready file?"
        )
    if nqn is not None and nqn != inferred_nqn:
        raise SystemExit(
            f"{in_path}: --nqn {nqn} given but column count ({ncols_in}) implies "
            f"NQN={inferred_nqn}"
        )

    out_lines = []
    for fields in data_lines:
        wavenumber, uncertainty, *rest = fields
        # Insert the duplicated uncorig column immediately after wavenumber.
        out_lines.append(" ".join([wavenumber, uncertainty, uncertainty, *rest]))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return len(data_lines), ncols_in + 1


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("input", type=Path, help="canonical MARVEL transitions file")
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="output path (default: <input stem>_marvel4.txt next to input)",
    )
    p.add_argument(
        "--nqn",
        type=int,
        default=None,
        help="expected quantum-number count per side, for a sanity check only",
    )
    args = p.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input not found: {args.input}")

    out_path = args.output or args.input.with_name(
        args.input.stem + "_marvel4" + args.input.suffix
    )

    n_rows, n_cols_out = convert(args.input, out_path, args.nqn)
    print(
        f"{args.input.name}: {n_rows} rows, {n_cols_out - 1} -> {n_cols_out} columns "
        f"(inserted uncorig = uncertainty)\n-> {out_path}"
    )


if __name__ == "__main__":
    main()
