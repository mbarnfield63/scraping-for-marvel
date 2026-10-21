#!/usr/bin/env python3
"""Build a molecule's student hand-off: one shared papers/ folder plus one CSV folder per isotopologue.

  python3 scripts/student_handoff.py molecules/<mol> [--extra <paperID> ...]   # writes molecules/<mol>/student_handoff/
  python3 scripts/student_handoff.py --selftest

Takes every finished paper (csv/<paperID>.done plus csv/<paperID>_batch*.csv). Each batch file goes to
<iso>/ by its `iso` column, split line for line when a paper covers several isotopologues, so no row is
re-serialised. papers/ gets the PDF(s), the supplements (`<paperID>_supp*`, converted `markdown/<paperID>/supp/*.tsv`)
and, for text-native papers (no MinerU `full.md`), the publisher `.xml`/`.txt`. `--extra` adds the sources
of a paper with no rows (one that corrects another paper, say). README.md is the caller's to write.
Prints a per-paper row/isotopologue table and the papers still missing a PDF, with DOI links.
"""
import argparse
import csv
import glob
import shutil
import sys
import tempfile
from pathlib import Path

LIT = Path("/mnt/c/Code/MARVEL_literature")


def sources(mol, pid):
    """(source files to copy, has_pdf) for one paper ID."""
    files = [f for f in (mol / "papers").glob("*/*")
             if f.name.startswith((pid + ".", pid + "_")) and f.parent.name != "superseded"]
    pdfs = [f for f in files if f.suffix.lower() == ".pdf"]
    supp = [f for f in files if f.name.lower().startswith(pid.lower() + "_supp")]
    supp += [Path(f) for f in glob.glob(str(mol / "markdown" / pid / "supp" / "*.tsv"))]
    ocr = glob.glob(str(mol / "markdown" / pid / "full.md")) + glob.glob(str(mol / "markdown" / f"{pid}_*" / "full.md"))
    text = [] if ocr else [f for f in files if f.suffix.lower() in (".xml", ".txt") and f.stem == pid]
    return pdfs + supp + text, bool(pdfs)


def dois(mol):
    out = {}
    for tsv in (LIT / mol.name / f"{mol.name}_handoff.tsv", mol / "papers" / "manifest.tsv"):
        if tsv.exists():
            for r in csv.DictReader(open(tsv, encoding="utf-8"), delimiter="\t"):
                out.setdefault(r["key"], r.get("doi", ""))
    return out


def build(mol, extra=()):
    mol = Path(mol)
    out = mol / "student_handoff"
    clash = [p.name for p in out.glob("*") if p.name != "README.md"]
    if clash:
        sys.exit(f"{out} already holds {clash}: move them aside first (never overwrite a hand-off)")
    csvdir = mol / "csv"
    batches = sorted(csvdir.glob("*_batch*.csv"))
    done = {p.stem for p in csvdir.glob("*.done")}
    skipped = sorted({b.name.split("_batch")[0] for b in batches} - done)
    if skipped:
        print(f"skipped, no .done marker: {', '.join(skipped)}")
    batches = [b for b in batches if b.name.split("_batch")[0] in done]
    (out / "papers").mkdir(parents=True, exist_ok=True)

    rows, total, expected = {}, 0, 0
    for b in batches:
        lines = open(b, encoding="utf-8", newline="").read().splitlines(keepends=True)
        parsed = list(csv.reader(lines))
        assert len(parsed) == len(lines), f"{b}: a field spans lines, split by hand"
        col = parsed[0].index("iso")
        split = {}
        for raw, row in zip(lines[1:], parsed[1:]):
            split.setdefault(row[col], []).append(raw)
        for iso, part in split.items():
            (out / iso).mkdir(exist_ok=True)
            (out / iso / b.name).write_text(lines[0] + "".join(part), encoding="utf-8", newline="")
            rows.setdefault(b.name.split("_batch")[0], {}).setdefault(iso, 0)
            rows[b.name.split("_batch")[0]][iso] += len(part)
            total += len(part)
        expected += len(lines) - 1
    assert total == expected, (total, expected)

    no_pdf = []
    for pid in sorted(rows) + list(extra):
        files, has_pdf = sources(mol, pid)
        for f in files:
            shutil.copy2(f, out / "papers" / f.name)
        if not has_pdf:
            no_pdf.append(pid)

    print(f"{total} rows from {len(rows)} papers")
    for pid, isos in sorted(rows.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"  {pid}\t{sum(isos.values())}\t{', '.join(isos)}")
    if no_pdf:
        doi = dois(mol)
        print("no PDF in papers/ (add <paperID>.pdf to student_handoff/papers/ and molecules/<mol>/papers/<folder>/):")
        for pid in no_pdf:
            print(f"  {pid}\thttps://doi.org/{doi[pid]}" if doi.get(pid) else f"  {pid}\tDOI not found")
    return out


def selftest():
    mol = Path(tempfile.mkdtemp()) / "XY"
    for d in ("csv", "papers/12XY", "papers/13XY", "markdown/01Ab", "markdown/02Cd_main", "markdown/03Ef/supp"):
        (mol / d).mkdir(parents=True)
    head = "transition_wavenumber,id,iso,notes\r\n"
    (mol / "csv/01Ab_batch1.csv").write_text(head + '1.0,01Ab.1,12XY,"a, b"\r\n2.0,01Ab.2,13XY,\r\n', newline="")
    (mol / "csv/02Cd_batch1.csv").write_text(head + "3.0,02Cd.1,12XY,\r\n", newline="")
    (mol / "csv/03Ef_batch1.csv").write_text(head + "4.0,03Ef.1,13XY,\r\n", newline="")
    (mol / "csv/04Gh_batch1.csv").write_text(head + "5.0,04Gh.1,13XY,\r\n", newline="")  # unfinished
    for pid in ("01Ab", "02Cd", "03Ef"):
        (mol / f"csv/{pid}.done").touch()
    for f in ("12XY/01Ab.pdf", "12XY/01Ab.xml", "12XY/01Abc.pdf", "12XY/02Cd_main.pdf", "12XY/02Cd_tables.pdf",
              "13XY/03Ef.xml", "13XY/03Ef.txt", "13XY/03Ef_Supp_mmc1.doc", "12XY/05Ij.pdf"):
        (mol / "papers" / f).touch()
    for f in ("01Ab/full.md", "02Cd_main/full.md", "03Ef/supp/03Ef_Supp_mmc1.tsv"):
        (mol / "markdown" / f).touch()
    out = build(mol, extra=["05Ij"])
    got = sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file())
    assert got == ["12XY/01Ab_batch1.csv", "12XY/02Cd_batch1.csv", "13XY/01Ab_batch1.csv", "13XY/03Ef_batch1.csv",
                   "papers/01Ab.pdf", "papers/02Cd_main.pdf", "papers/02Cd_tables.pdf", "papers/03Ef.txt",
                   "papers/03Ef.xml", "papers/03Ef_Supp_mmc1.doc", "papers/03Ef_Supp_mmc1.tsv", "papers/05Ij.pdf"], got
    assert (out / "12XY/01Ab_batch1.csv").read_bytes() == (head + '1.0,01Ab.1,12XY,"a, b"\r\n').encode()
    try:
        build(mol)
    except SystemExit:
        pass
    else:
        raise AssertionError("rebuild over an existing hand-off must refuse")
    print("student_handoff selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        sys.exit()
    ap = argparse.ArgumentParser()
    ap.add_argument("mol_dir")
    ap.add_argument("--extra", nargs="*", default=[], help="paper IDs with no rows whose sources go in papers/")
    a = ap.parse_args()
    build(a.mol_dir, a.extra)
