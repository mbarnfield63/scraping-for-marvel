"""Build per-isotopologue N2O vibrational-state tables in the 24TeFuYu (P, l, N) scheme.

24TeFuYu numbered N within each (P, l) by the Ames-1 energy of the lowest e level
(J = l) of each state, for 446 only. For a minor isotopologue we carry each 446
state over to the isotopologue's own Ames-1 level list by position in the same
symmetry block, so the (P, l, N) labels are identical and only the energies change.
Ames automatic HO labels are used only for the shift estimate and as a cross-check.

Usage:
    python3 scripts/n2o_states.py template <supp_info.txt> <out 446_template.tsv>
    python3 scripts/n2o_states.py build <template.tsv> <ames_dir> <iso> <out.tsv>
"""
import re
import sys
from pathlib import Path

JMAX = 12  # largest l considered; levels needed only at J = l


def parse_template(supp_txt):
    """Rows of supp Table 1: P l N [v1 v2 l v3] Ames [Obs ...]."""
    rows = []
    for line in Path(supp_txt).read_text().splitlines():
        t = line.split()
        if len(t) < 4 or not all(x.isdigit() for x in t[:3]):
            continue
        P, l, N = map(int, t[:3])
        rest = t[3:]
        # Ames column is the first float (or -1 = not computed); integers before it are the HO label
        k = next((i for i, x in enumerate(rest) if "." in x or x == "-1"), None)
        if k is None:
            continue
        ho = " ".join(rest[:k]) if k == 4 else ""
        if k not in (0, 4):
            ho = "?" + " ".join(rest[:k])  # HO label lost a column in the PDF text layer
        ames = float(rest[k])
        if P == 0:
            ames = 0.0
        nxt = rest[k + 1] if len(rest) > k + 1 else ""
        obs = nxt if re.fullmatch(r"\d+\.\d+", nxt) else ""
        rows.append(dict(P=P, l=l, N=N, ho=ho, ames=ames, obs=obs))
    return rows


def load_ames(path):
    """{(J, block): [(E, 'v1 v2 l v3'), ...]} for J <= JMAX, sorted by E."""
    lev = {}
    with open(path) as f:
        for line in f:
            t = line.split()
            J = int(t[0])
            if J > JMAX:
                break
            lev.setdefault((J, int(t[1])), []).append((float(t[3]), " ".join(t[4:8])))
    for v in lev.values():
        v.sort()
    return lev


def e_block(J):
    # Ames block 2 = + total parity; e levels have parity (-1)^J
    return 2 if J % 2 == 0 else 1


def ladders(lev):
    """{l: [(E, label), ...]}: e levels at J = l that belong to l-states only.

    The J = l block also holds rotational levels of every l' < l state. Those couple to the
    l-states only weakly, so they effectively cross them between isotopologues. Remove them
    by following each l' level up to J = l (dE = B[l(l+1) - l'(l'+1)]) before indexing."""
    B = lev[(1, e_block(1))][0][0] / 2  # ground state J=1 e level = 2B
    out = {}
    for l in range(JMAX + 1):
        pool = list(lev[(l, e_block(l))])
        for lp in range(l):
            dE = B * (l * (l + 1) - lp * (lp + 1))
            for E, _ in out[lp]:
                if not pool:
                    break
                k = min(range(len(pool)), key=lambda i: abs(pool[i][0] - E - dE))
                pool.pop(k)
        out[l] = pool
    return out


def build(template, ames_dir, iso, out):
    """Same-index (adiabatic) map on the pure-l ladders: within one ladder levels do not cross
    as the masses change, so the k-th 446 level is the k-th isotopologue level and N carries
    over. Weak-coupling crossings that still slip through go in states/<iso>_overrides.tsv
    (P l N Eiso evidence), set from observed band origins."""
    rows = [r for r in read_tsv(template) if int(r["l"]) <= JMAX and float(r["ames"]) >= 0]
    L446 = ladders(load_ames(next(Path(ames_dir, "446").glob("*.dat"))))
    Liso = ladders(load_ames(next(Path(ames_dir, iso).glob("*.dat"))))
    ov_path = Path(out).with_name(f"{iso}_overrides.tsv")
    overrides = {(r["P"], r["l"], r["N"]): r for r in read_tsv(ov_path)} if ov_path.exists() else {}
    cols = ["P", "l", "N", "ho", "lab446", "labiso", "E446", "Eiso", "rel_shift", "flag"]
    with open(out, "w") as f:
        f.write("# iso=%s; (P,l,N) = 24TeFuYu 446 labels carried over by same-index map on the "
                "pure-l ladder (J=l, e) of Ames-1 levels; ho = 24TeFuYu HO label (blank if not given); "
                "lab446/labiso = Ames automatic labels (unreliable, info only)\n" % iso)
        f.write("\t".join(cols) + "\n")
        for r in rows:
            l = int(r["l"])
            L = L446[l]
            k = min(range(len(L)), key=lambda i: abs(L[i][0] - float(r["ames"])))
            (E446, lab446), (Eiso, labiso) = L[k], Liso[l][k]
            flags = []
            if abs(E446 - float(r["ames"])) > 0.1:
                flags.append("PIN_446_DEV")
            if r["ho"].startswith("?"):
                flags.append("HO_PARTIAL")
            ov = overrides.get((r["P"], r["l"], r["N"]))
            if ov:
                flags.append("OVERRIDE(same-index Eiso=%.4f; %s)" % (Eiso, ov["evidence"]))
                Eiso, labiso = min(Liso[l], key=lambda x: abs(x[0] - float(ov["Eiso"])))
            rel = (Eiso - E446) / E446 if E446 else 0.0
            vals = [r["P"], r["l"], r["N"], r["ho"], lab446, labiso,
                    "%.4f" % E446, "%.4f" % Eiso, "%.5f" % rel, ",".join(flags)]
            f.write("\t".join(vals) + "\n")


def read_tsv(path):
    lines = [x for x in Path(path).read_text().splitlines() if not x.startswith("#")]
    head = lines[0].split("\t")
    return [dict(zip(head, x.split("\t"))) for x in lines[1:]]


def write_template(supp_txt, out):
    rows = parse_template(supp_txt)
    with open(out, "w") as f:
        f.write("# 24TeFuYu supp Table 1 (446): ho blank where the paper gives no HO label\n")
        f.write("P\tl\tN\tho\tames\tobs\n")
        for r in rows:
            f.write("%d\t%d\t%d\t%s\t%.4f\t%s\n" % (r["P"], r["l"], r["N"], r["ho"], r["ames"], r["obs"]))
    print(len(rows), "template states")


if __name__ == "__main__":
    if sys.argv[1] == "template":
        write_template(*sys.argv[2:4])
    else:
        build(*sys.argv[2:6])
