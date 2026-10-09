#!/usr/bin/env python3
"""Catch a source whose segment unit is off by 1000 (kHz declared as MHz, etc.) before a MARVEL4 run.

    python3 scripts/unit_check.py <trans_marvel4.txt> <segment.txt> [--levels EnergyLevels.txt] [--ok SRC,...]

Each source's lines are converted to cm-1 by its segment unit and compared with (1) other sources
on the transitions they share (same upper and lower quantum numbers) and (2), with --levels, the
level difference E(upper) - E(lower) from an earlier MARVEL run. A source whose median ratio is
within x3 of 1000 or 1/1000 is flagged, and the exit code is 1 unless it is listed in --ok.
A source with no shared transition and no reference levels goes unchecked: --levels is what catches
a lone microwave source (78ReMeDy, kHz declared MHz, shared nothing). A molecule's first run has no
reference levels, so only (1) applies there.
marvel_steps.py runs this on every load with the network's final/EnergyLevels.txt; an
`unit-ok <SRC> <reason>` line in overrides.tsv is its --ok.
"""
import statistics
import sys
from collections import defaultdict

TO_CM = {"cm-1": 1.0, "Hz": 1 / 2.99792458e10, "kHz": 1e3 / 2.99792458e10,
         "MHz": 1e6 / 2.99792458e10, "GHz": 1e9 / 2.99792458e10, "THz": 1e12 / 2.99792458e10}


def load_levels(path, nqn):
    """{QN string: energy in cm-1} from a MARVEL EnergyLevels.txt."""
    E = {}
    for l in open(path):
        t = l.split()
        if len(t) > nqn:
            E[" ".join(t[:nqn])] = float(t[nqn])
    return E


def suspicious(lines, seg, levels=None):
    """{source: median ratio} for sources off by about 1000 either way, against other sources on shared
    transitions and against reference level differences (levels: {QN string: cm-1}).
    lines: token lists (wavenumber, uncorig, unc, QNs..., id); seg: {source: unit}."""
    by_qn = defaultdict(lambda: defaultdict(list))  # QNs -> source -> values in cm-1
    for t in lines:
        s, v = t[-1].split(".")[0], abs(float(t[0]))
        if v:
            by_qn[tuple(t[3:-1])][s].append(v * TO_CM[seg.get(s, "cm-1")])
    ratios = defaultdict(list)
    for per in by_qn.values():
        for s, vs in per.items():
            others = [v for o, ws in per.items() if o != s for v in ws]
            if others:
                ratios[s].append(statistics.median(vs) / statistics.median(others))
    for t in lines if levels else []:
        n = (len(t) - 4) // 2
        u, lo = " ".join(t[3:3 + n]), " ".join(t[3 + n:3 + 2 * n])
        if u in levels and lo in levels and abs(levels[u] - levels[lo]) > 1e-9 and float(t[0]):
            s = t[-1].split(".")[0]
            ratios[s].append(abs(float(t[0])) * TO_CM[seg.get(s, "cm-1")] / abs(levels[u] - levels[lo]))
    med = {s: statistics.median(r) for s, r in ratios.items()}
    return {s: r for s, r in med.items() if 1000 / 3 <= r <= 3000 or 1 / 3000 <= r <= 3 / 1000}


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        mk = lambda wn, u, l, i: [wn, "1", "1"] + u.split() + l.split() + [i]
        L = [mk("3.33564", "1", "0", "A.1"), mk("100000", "1", "0", "B.1"),
             mk("100", "1", "0", "C.1"), mk("6.7", "2", "1", "A.2")]
        bad = suspicious(L, {"A": "cm-1", "B": "MHz", "C": "MHz"})  # C really kHz, declared MHz
        assert set(bad) == {"C"} and abs(bad["C"] - 1e-3) < 1e-4, bad
        assert suspicious(L[:2], {"A": "cm-1", "B": "MHz"}) == {}
        D = [mk("46882.4", "1 f", "1 e", "D.1")]  # lone l-doubling line in kHz, shares nothing
        E = {"1 f": 0.0015638, "1 e": 0.0}
        assert suspicious(D, {"D": "MHz"}) == {} and set(suspicious(D, {"D": "MHz"}, E)) == {"D"}
        assert suspicious(D, {"D": "kHz"}, E) == {}
        print("selftest ok")
        sys.exit()
    trans, segf = sys.argv[1], sys.argv[2]
    ok = set(sys.argv[sys.argv.index("--ok") + 1].split(",")) if "--ok" in sys.argv else set()
    lines = [l.split() for l in open(trans) if l.strip()]
    seg = dict(l.split() for l in open(segf) if l.strip())
    E = load_levels(sys.argv[sys.argv.index("--levels") + 1], (len(lines[0]) - 4) // 2) if "--levels" in sys.argv else None
    bad = {s: r for s, r in suspicious(lines, seg, E).items() if s not in ok}
    for s, r in sorted(bad.items()):
        print(f"UNIT? {s}: declared {seg.get(s, 'cm-1')}, values are {r:.3g}x other sources or reference levels")
    sys.exit(1 if bad else 0)
