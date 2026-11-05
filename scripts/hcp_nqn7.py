#!/usr/bin/env python3
"""Re-format HCP output/ into the NQN 7 scheme (es v1 v2 K ef v3 J per side; ledger HQ2, HQ2c).

  python3 scripts/hcp_nqn7.py            # writes molecules/HCP/output/HCP_<iso>_<paper>_<now>.txt
  python3 scripts/hcp_nqn7.py --selftest

Linear X-state files: es = X on both sides, l2 renamed K, no value changed. 69JoShTy (batch1 + the UV
supplement), 99IsNaMib and 96IsChOh-CX come from csv/<paperID>_merged.csv: the upper es and K come from
the notes ("upper: A~ ... Ka=1", "upper: B~1Pi ... K=1"); v2 stays as printed. An unassigned upper level
(blank v1) keeps es and K blank. 93MaLe (hyperfine) is not formatted. Files already in NQN 7 are
skipped; old-scheme files are left in place for the caller to move to output/superseded/<date>/.
"""
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

MOL = Path(__file__).resolve().parent.parent / "molecules" / "HCP"
SIDE = ("v1", "v2", "l2", "ef", "v3", "J")
HEADER = (["transition_wavenumber", "uncertainty"]
          + [f"{q}_{s}" for s in ("upper", "lower") for q in ("es", "v1", "v2", "K", "ef", "v3", "J")] + ["id"])
FROM_CSV = {"69JoShTy": "69JoShTy", "99IsNaMib": "99IsNaMib", "96IsChOh-CX": "96IsChOh"}


def convert(r):
    """Old-scheme row dict (+ notes) -> NQN 7 row list."""
    es, k = "X", r["l2_upper"]
    m = re.search(r"upper: ([ABC])~[^;]*?\bKa?=(\d+)", r.get("notes", ""))
    if m:
        es, k = m.groups()
        if not r["v1_upper"]:
            es, k = "", ""
    up = [es, r["v1_upper"], r["v2_upper"], k, r["ef_upper"], r["v3_upper"], r["J_upper"]]
    lo = ["X"] + [r[f"{q}_lower"] for q in SIDE]
    return [r["transition_wavenumber"], r["uncertainty"]] + up + lo + [r["id"]]


def main():
    out = MOL / "output"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    done = []
    for f in sorted(out.glob("HCP_*.txt")) + sorted((out / "bent").glob("HCP_*.txt")):
        _, iso, paper, *_ = f.stem.split("_")
        if paper == "93MaLe":
            continue
        old = list(csv.DictReader(open(f), delimiter="\t"))
        if not old or "l2_upper" not in old[0]:   # already NQN 7
            continue
        if paper in FROM_CSV:
            ids = {r["id"] for r in old}
            src = [r for r in csv.DictReader(open(MOL / "csv" / f"{FROM_CSV[paper]}_merged.csv")) if r["iso"] == iso]
            rows = src if paper == "69JoShTy" else [r for r in src if r["id"] in ids]
            assert ids <= {r["id"] for r in rows}, f
        else:
            rows = old
        new = [convert(r) for r in rows]
        for r, n in zip(rows, new):   # every old column survives unchanged
            assert [r[c] for c in ("transition_wavenumber", "uncertainty", "id")] == [n[0], n[1], n[-1]]
            assert [r[f"{q}_lower"] for q in SIDE] == n[10:16]
        dest = out / f"HCP_{iso}_{paper}_{stamp}.txt"
        with open(dest, "w") as g:
            g.write("\t".join(HEADER) + "\n")
            g.writelines("\t".join(n) + "\n" for n in new)
        done.append((dest.name, len(new), f.relative_to(out)))
    for name, n, old in done:
        print(f"{name}\t{n}\t(from {old})")
    print(f"{len(done)} files, {sum(n for _, n, _ in done)} rows")


def selftest():
    base = dict(transition_wavenumber="1.5", uncertainty="0.1", v1_upper="0", v2_upper="1", l2_upper="1",
                ef_upper="f", v3_upper="0", J_upper="3", v1_lower="0", v2_lower="0", l2_lower="0",
                ef_lower="e", v3_lower="0", J_lower="3", id="P.1")
    assert convert(base) == ["1.5", "0.1", "X", "0", "1", "1", "f", "0", "3", "X", "0", "0", "0", "e", "0", "3", "P.1"]
    a = convert({**base, "l2_upper": "", "notes": "upper: A~1A'' v1v2^Kv3=01^10 Ka=2 (paper label); lower: X~"})
    assert a[2:5] + [a[5]] == ["A", "0", "1", "2"], a
    b = convert({**base, "l2_upper": "", "notes": "x; upper: B~1Pi 00^10, K=1 (Lambda"})
    assert b[2] == "B" and b[5] == "1", b
    c = convert({**base, "l2_upper": "", "notes": "upper: C~1A' (0,1,1)^0 Ka=0 J'=5 (PUMP P(6) from X"})
    assert c[2] == "C" and c[5] == "0", c
    u = convert({**base, "v1_upper": "", "v2_upper": "", "v3_upper": "", "l2_upper": "",
                 "notes": "upper: A~1A'' unassigned level Ka=1 e-symmetry"})
    assert u[2:6] == ["", "", "", ""], u
    print("hcp_nqn7 selftest ok")


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main()
