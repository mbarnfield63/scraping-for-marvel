"""Marvel4.1.x runs for one N2O isotopologue: incremental build, full runs, final run.

Usage: python scripts/marvel_steps.py <iso> [--mode steps|full|final] [--tag NAME]
                                        [--first SRC,...] [--last SRC,...]

Input:  molecules/N2O/marvel4_input/N2O_<iso>_trans_marvel4.txt + _segment.txt (frozen),
        plus <dir>/overrides.tsv and the files it references (<dir>: --dir, default network/<iso>,
        the official network layer; agents' work folders are marvel_runs/<iso>).
Output: <dir>/<run dir>/ with trans.txt, segment.txt, Marvel outputs, flagged.tsv;
        full/final also write revive.tsv, ames_check.tsv, summary.txt; final writes <iso>_states.txt.

Modes:
  steps  Phase 1: each source with loops alone -> single_<src>/
         Phase 2: backbone (largest source), then tightest median uncertainty first
         (cm-1 scale, ties: larger first), then held/extra sources -> step<NN>_<src>/
         Writes summary.tsv.
  full   One run of everything -> full[_<tag>]/ (no bootstrap; deterministic).
  final  Like full but with -b -> final[_<tag>]/. --minsize is raised until no bootstrap
         decomposition fails, so only components with loops are solved. If a failure remains
         (tree branches inside the ground component), final/core/ bootstraps only the looped core
         (degree-1 levels pruned) and final/nob/ is a no -b run: states take core uncertainties for
         core levels, nob uncertainties for the rest.
         <iso>_states.txt gets a last column `validation`: validated (on a loop of measured lines;
         a repeated measurement counts), tree (measured, but on a dangling chain), model-anchored
         (joined to (0 0 1 e 0) only through virtual lines, source tags VGS_/VNU2_/VLR_).

overrides.tsv (tab-separated, header: action target value reason; '#' lines ignored):
  negate      <ID>   -                  line kept, wavenumber negated
  relabel     <ID>   upper=P l N ef J   and/or lower=...; several separated by ';'
  scale       <SRC>  <factor>           multiply both uncertainty columns of the source
  wn_scale    <SRC>  <factor>           multiply the wavenumbers of the source (recalibration, _RC)
  double      <ID>   -                  double both uncertainty columns of one line
  assume_unc  <SRC>  <value>            include the source's blank-uncertainty rows from csv_polyad/
                                        with this uncertainty (source native unit)
  extra       <file> <unit>             add marvel4-format lines from <dir>/<file>;
                                        <unit> is the segment unit of their source tags
  unit        <SRC>  <unit>             segment unit for a source not in the segment file
  exclude     <SRC>  -                  leave the source out
  unit-ok     <SRC>  -                  the source passes the unit check (scripts/unit_check.py),
                                        which otherwise stops a run on a ~1000x unit mismatch

Bootstrap (-b) is used only in final mode: in Marvel4.1.x a failed bootstrap decomposition
(tiny tree components) leaves line uncertainties randomly inflated 1-10x, so flags become random.
"""
import argparse, csv, re, statistics, subprocess, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from n2o_apply import AmesTracker, ROOT  # noqa: E402
from unit_check import TO_CM, load_levels, suspicious  # noqa: E402

BIN = "/mnt/c/Code/versions_MARVEL/Marvel4.1.x/Marvel4.1.x"
NQN = 5
OUTPUTS = ["EnergyLevels.txt", "Components.txt", "CheckTransitions.txt", "BadLines.txt", "AVTable.txt", "reviveTRs.txt"]
GROUND = "0 0 1 e 0"


def src(t):
    return t[-1].split(".")[0]


def up(t):
    return " ".join(t[3:3 + NQN])


def lo(t):
    return " ".join(t[3 + NQN:3 + 2 * NQN])


def components(lines):
    """Union-find over positive lines -> {level: root}."""
    par = {}

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    for t in lines:
        if float(t[0]) < 0:
            continue
        for x in (up(t), lo(t)):
            par.setdefault(x, x)
        a, b = find(up(t)), find(lo(t))
        if a != b:
            par[a] = b
    return {x: find(x) for x in par}


VIRTUAL = ("VGS_", "VNU2_", "VLR_")


def prune(lines):
    """Positive lines left after iteratively removing levels of degree 1 (except the ground).
    Parallel lines count separately, so a repeated measurement is a loop."""
    L = [t for t in lines if float(t[0]) >= 0]
    while True:
        deg = defaultdict(int)
        for t in L:
            deg[up(t)] += 1
            deg[lo(t)] += 1
        keep = [t for t in L if all(deg[x] > 1 or x == GROUND for x in (up(t), lo(t)))]
        if len(keep) == len(L):
            return L
        L = keep


def validation(lines):
    """{level: validated|tree} for levels joined to the ground by measured lines; others absent
    (model-anchored if they are in the ground component at all)."""
    meas = [t for t in lines if not src(t).startswith(VIRTUAL)]
    comp = components(meas)
    g = comp.get(GROUND)
    core = {x for t in prune(meas) for x in (up(t), lo(t))}
    return {x: "validated" if x in core else "tree" for x, r in comp.items() if r == g}


def cycle_rank(lines):
    comp = components(lines)
    return sum(float(t[0]) >= 0 for t in lines) - len(comp) + len(set(comp.values()))


def load(iso, ov=None, xdir=None):
    """Base lines + segment, with overrides applied. Returns (lines as token lists, seg, held sources)."""
    base = ROOT / "marvel4_input" / f"N2O_{iso}_trans_marvel4.txt"
    segf = ROOT / "marvel4_input" / f"N2O_{iso}_segment.txt"
    lines = [l.split() for l in open(base) if l.strip()] if base.exists() else []
    seg = dict(l.split() for l in open(segf) if l.strip()) if segf.exists() else {}
    ov = Path(ov) if ov else ROOT / "network" / iso / "overrides.tsv"
    xdir = Path(xdir) if xdir else ov.parent  # folder of the extra files
    rules = []
    if ov.exists():
        rows = [l.rstrip("\n").split("\t") for l in open(ov) if l.strip() and not l.startswith("#")]
        rules = [r + [""] * (4 - len(r)) for r in rows[1:]]
    held = []
    for act, tgt, val, _ in rules:
        if act == "unit":
            seg[tgt] = val
        elif act == "assume_unc":
            held.append(tgt)
            f = ROOT / "csv_polyad" / f"{tgt}_{iso}.csv"
            for r in csv.DictReader(open(f)):
                if r["unc"].strip() or r["flag"] == "DROP":
                    continue
                m = re.search(r"unit:\s*(\S+?)[;,)\s]", r["notes"] + " ")
                seg.setdefault(tgt, m.group(1) if m else "cm-1")
                lines.append([r["wn"], val, val] + [r[k] for k in
                             ("Pu", "lu", "Nu", "efu", "Ju", "Pl", "ll", "Nl", "efl", "Jl", "id")])
        elif act == "extra":
            for l in open(xdir / tgt):
                if l.strip() and not l.startswith("#"):
                    t = l.split()
                    lines.append(t)
                    seg.setdefault(src(t), val)
                    if src(t) not in held:
                        held.append(src(t))
    byid = {t[-1]: t for t in lines}
    excl = {tgt for act, tgt, _, _ in rules if act == "exclude"}
    for act, tgt, val, _ in rules:
        if act == "negate":
            t = byid[tgt]
            t[0] = "-" + t[0].lstrip("-")
        elif act == "relabel":
            t = byid[tgt]
            for part in val.split(";"):
                side, qn = part.split("=")
                q = qn.split()
                assert len(q) == NQN, f"relabel {tgt}: need {NQN} QNs"
                s = 3 if side.strip() == "upper" else 3 + NQN
                t[s:s + NQN] = q
        elif act == "scale":
            for t in lines:
                if src(t) == tgt:
                    t[1] = f"{float(t[1]) * float(val):.6g}"
                    t[2] = f"{float(t[2]) * float(val):.6g}"
        elif act == "double":
            t = byid[tgt]
            t[1], t[2] = f"{float(t[1]) * 2:.6g}", f"{float(t[2]) * 2:.6g}"
        elif act == "wn_scale":
            for t in lines:
                if src(t) == tgt:
                    dec = len(t[0].split(".")[1]) if "." in t[0] else 0
                    t[0] = f"{float(t[0]) * float(val):.{dec + 2}f}"  # sign kept: negated stays negated
    lines = [t for t in lines if src(t) not in excl]
    for s in {src(t) for t in lines} - set(seg):
        print(f"WARNING: no segment unit for {s}, using cm-1")
        seg[s] = "cm-1"
    # a kHz source declared MHz cost ~6 runs (78ReMeDy); stop here instead of flagging 14k lines
    ok = {tgt for act, tgt, _, _ in rules if act == "unit-ok"}
    ref = ROOT / "network" / iso / "final" / "EnergyLevels.txt"
    bad = {s: r for s, r in suspicious(lines, seg, load_levels(ref, NQN) if ref.exists() else None).items() if s not in ok}
    if bad:
        sys.exit("".join(f"UNIT? {s}: declared {seg[s]}, values are {r:.3g}x other sources or reference levels\n"
                         for s, r in sorted(bad.items())) + "Fix the segment unit, or add `unit-ok <SRC> <reason>` to overrides.tsv.")
    return lines, seg, held


def run(d, lines, seg, boot=False):
    d.mkdir(parents=True, exist_ok=True)
    (d / "trans.txt").write_text("".join(" ".join(t) + "\n" for t in lines))
    (d / "segment.txt").write_text("".join(f"{s} {seg[s]}\n" for s in sorted({src(t) for t in lines})))
    # Tiny tree components can give an exact-zero pivot ("wrong decomp 1": fatal in the main solve,
    # silent uncertainty corruption in the bootstrap). Raise --minsize past the smallest component
    # and retry until neither happens; skipped components have no loops to check anyway.
    comp = components(lines)
    g = comp.get(GROUND)
    gsize = sum(1 for r in comp.values() if r == g) if g else 10**9
    minsize = 2
    while True:
        for f in OUTPUTS:
            (d / f).unlink(missing_ok=True)
        args = [BIN, "-n", str(NQN), "-t", "trans.txt", "-s", "segment.txt", "--minsize", str(minsize)]
        with open(d / "run.log", "w") as log:
            rc = subprocess.run(args + (["-b"] if boot else []), cwd=d, stdout=log, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, timeout=7200).returncode
        failed = rc != 0 or "wrong decomp" in (d / "run.log").read_text()
        sizes = [int(m) for m in re.findall(r"nbEL=\s*(\d+)", (d / "Components.txt").read_text())] \
            if (d / "Components.txt").exists() else []
        nxt = min((n for n in sizes if n >= minsize), default=None)
        if not failed or nxt is None or not [n for n in sizes if n > nxt]:
            break
        minsize = nxt + 1
    note = ""
    if failed:
        note += f" FAILED: Marvel still fails at minsize {minsize}"
    if minsize > gsize < 10**9:
        note += f" GROUND COMPONENT SKIPPED ({gsize} levels < minsize {minsize})"
    if note:
        print(f"WARNING {d.name}:{note}")
    (d / "minsize.txt").write_text(f"{minsize}{note}\n")
    comps = [tuple(map(int, m)) for m in re.findall(r"nbEL=\s*(\d+)\s+nbTR=\s*(\d+)", (d / "Components.txt").read_text())] \
        if (d / "Components.txt").exists() else []
    byid = {t[-1]: t for t in lines}
    flagged = []
    if (d / "BadLines.txt").exists():
        for m in re.finditer(r"^\d+\)\s+(\S+)\s.*ratio = ([\d.]+)", (d / "BadLines.txt").read_text(), re.M):
            t = byid.get(m.group(1))
            flagged.append((m.group(1), float(m.group(2)), t))
    with open(d / "flagged.tsv", "w") as o:
        o.write("id\tsource\tratio\twn\tunc\tupper\tlower\n")
        for i, r, t in flagged:
            o.write(f"{i}\t{i.split('.')[0]}\t{r:.2f}\t{t[0] if t else ''}\t{t[2] if t else ''}\t"
                    f"{up(t) if t else ''}\t{lo(t) if t else ''}\n")
    bad = defaultdict(list)
    for i, r, _ in flagged:
        bad[i.split(".")[0]].append(r)
    return rc, comps, bad, minsize


def levels(d):
    E = {}
    if (d / "EnergyLevels.txt").exists():
        for l in open(d / "EnergyLevels.txt"):
            t = l.split()
            if len(t) >= 7:
                E[" ".join(t[:NQN])] = (float(t[NQN]), t)
    return E


def post(d, iso, lines, seg, final, E=None):
    """revive.tsv, ames_check.tsv, summary.txt (+ states file when final)."""
    E = E or levels(d)
    comp = components(lines)
    groot = comp.get(GROUND)
    gset = {x for x, r in comp.items() if r == groot} if groot else set()
    # revive: negated lines that now fit within their (scaled) stated uncertainty
    with open(d / "revive.tsv", "w") as o:
        o.write("id\twn\tunc\tcalc\tratio\n")
        for t in lines:
            if float(t[0]) < 0 and up(t) in E and lo(t) in E:
                f = TO_CM[seg[src(t)]]
                calc = E[up(t)][0] - E[lo(t)][0]
                r = abs(-float(t[0]) * f - calc) / (float(t[2]) * f)
                if r <= 1:
                    o.write(f"{t[-1]}\t{t[0]}\t{t[2]}\t{calc / f:.6f}\t{r:.2f}\n")
    # obs - Ames per (P l N ef) band vs J; flag jumps from a running median
    st = []
    for f in (ROOT / "states" / f"{iso}_states.tsv", ROOT / "states" / f"{iso}_extra_states.tsv"):
        if f.exists():
            st += csv.DictReader([l for l in open(f) if not l.startswith("#")], delimiter="\t")
    tr = AmesTracker(iso, st)
    band = defaultdict(list)
    for k, (e, _) in E.items():
        if k in gset:
            P, l, N, ef, J = k.split()
            a = tr.energy(int(P), int(l), int(N), ef, int(J))
            if a is not None:
                band[(P, l, N, ef)].append((int(J), e - a))
    with open(d / "ames_check.tsv", "w") as o:
        o.write("band\tJ\tobs_minus_ames\trunning_median\tdeviation\n")
        nflag = 0
        for b, pts in sorted(band.items()):
            pts.sort()
            for i, (J, v) in enumerate(pts):
                win = [p[1] for p in pts[max(0, i - 3):i + 4]]
                med = statistics.median(win)
                mad = statistics.median(abs(x - med) for x in win) or 1e-4
                if abs(v - med) > max(5 * mad, 0.02):
                    nflag += 1
                    o.write(f"{' '.join(b)}\t{J}\t{v:.5f}\t{med:.5f}\t{v - med:.5f}\n")
    pos = [t for t in lines if float(t[0]) >= 0]
    ing = [t for t in pos if up(t) in gset]
    nlev = sum(1 for k in E if k in gset)
    txt = (f"lines total {len(lines)}; positive {len(pos)}; negated {len(lines) - len(pos)}\n"
           f"ground component: {len(gset)} levels ({nlev} solved), {len(ing)} transitions\n"
           f"other components: {len(set(comp.values())) - (1 if groot else 0)}, "
           f"{len(pos) - len(ing)} transitions outside ground component\n"
           f"revive candidates: {sum(1 for _ in open(d / 'revive.tsv')) - 1}\n"
           f"ames jumps flagged: {nflag}\n")
    if final:
        val = validation(lines)
        cnt = defaultdict(int)
        with open(d / f"{iso}_states.txt", "w") as o:
            for k, (e, t) in sorted(E.items(), key=lambda kv: kv[1][0]):
                if k in gset:
                    v = val.get(k, "model-anchored")
                    cnt[v] += 1
                    o.write("\t".join([k] + t[NQN:] + [v]) + "\n")
        txt += "validation: " + ", ".join(f"{k} {cnt[k]}" for k in ("validated", "tree", "model-anchored")) + "\n"
    (d / "summary.txt").write_text(txt)
    print(txt, end="")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("iso")
    ap.add_argument("--mode", choices=["steps", "full", "final"], default="steps")
    ap.add_argument("--tag", default="")
    ap.add_argument("--first", default="", help="comma list: sources right after the backbone")
    ap.add_argument("--last", default="", help="comma list: sources at the very end")
    ap.add_argument("--dir", default="", help="overrides + extra files + outputs (default network/<iso>)")
    a = ap.parse_args()
    out = Path(a.dir).resolve() if a.dir else ROOT / "network" / a.iso
    lines, seg, held = load(a.iso, out / "overrides.tsv")
    print(f"{a.iso}: {len(lines)} lines, {len({src(t) for t in lines})} sources")

    if a.mode != "steps":
        d = out / (("final" if a.mode == "final" else "full") + (f"_{a.tag}" if a.tag else ""))
        rc, comps, bad, minsize = run(d, lines, seg, boot=a.mode == "final")
        allr = sum(bad.values(), [])
        print(f"exit {rc} minsize {minsize} components {len(comps)} main {comps[0] if comps else None} "
              f"flagged {len(allr)} >10: {sum(r > 10 for r in allr)} "
              f"by source: {', '.join(f'{k}:{len(v)}' for k, v in sorted(bad.items(), key=lambda kv: -len(kv[1])))}")
        E = None
        if a.mode == "final" and "wrong decomp" in (d / "run.log").read_text():
            # Marvel4.1.x bug: failed bootstrap leaves uncertainties inflated -> core-only bootstrap
            print("bootstrap failed in final/: core bootstrap + no -b run for tree levels")
            run(d / "core", prune(lines), seg, boot=True)
            run(d / "nob", lines, seg)
            if "wrong decomp" in (d / "core" / "run.log").read_text():
                print("WARNING: core bootstrap also failed; core uncertainties unreliable")
            (d / "flagged.tsv").write_text((d / "nob" / "flagged.tsv").read_text())  # -b flags unreliable
            E, Ec = levels(d / "nob"), levels(d / "core")
            for k, (e, t) in E.items():
                if k in Ec:
                    t[NQN + 1] = Ec[k][1][NQN + 1]
        post(d, a.iso, lines, seg, a.mode == "final", E)
        return

    by = defaultdict(list)
    for t in lines:
        by[src(t)].append(t)
    med = {s: statistics.median(float(t[2]) * TO_CM[seg[s]] for t in ls) for s, ls in by.items()}
    first = [s for s in a.first.split(",") if s in by]
    last = [s for s in a.last.split(",") if s in by] + [s for s in held if s in by and s not in a.last.split(",")]
    core = [s for s in by if s not in last]
    backbone = max(core, key=lambda s: len(by[s])) if core else None
    order = ([backbone] if backbone else []) + [s for s in first if s != backbone]
    order += sorted((s for s in core if s not in order), key=lambda s: (med[s], -len(by[s]))) + last

    rows = ["phase\tstep\tsource\tn_src\tmed_unc_cm\tcycle_rank\texit\tminsize\tcomponents\tmain_EL\tmain_TR\t"
            "flag_new\tvbad_new\tflag_old\tvbad_old\tflag_total\tvbad_total\tmax_ratio\tworst_sources"]

    def row(phase, step, s, ls, res):
        rc, comps, bad, minsize = res
        new = bad.get(s, []) if phase == "P2" else sum(bad.values(), [])
        old = [r for k, v in bad.items() if k != s for r in v] if phase == "P2" else []
        allr = sum(bad.values(), [])
        worst = ",".join(f"{k}:{len(v)}" for k, v in sorted(bad.items(), key=lambda kv: -len(kv[1]))[:4])
        main = comps[0] if comps else (0, 0)
        rows.append("\t".join(map(str, [phase, step, s, len(by[s]), f"{med[s]:.2e}", cycle_rank(ls), rc, minsize,
                    len(comps), *main, len(new), sum(r > 10 for r in new), len(old), sum(r > 10 for r in old),
                    len(allr), sum(r > 10 for r in allr), f"{max(allr, default=0):.1f}", worst])))
        print(rows[-1], flush=True)

    print(rows[0])
    for s in order:
        if cycle_rank(by[s]) > 0:
            row("P1", "-", s, by[s], run(out / f"single_{s}", by[s], seg))
    cum = []
    for i, s in enumerate(order, 1):
        cum += by[s]
        row("P2", i, s, cum, run(out / f"step{i:02d}_{s}", cum, seg))
    (out / "summary.tsv").write_text("\n".join(rows) + "\n")


if __name__ == "__main__":
    main()
