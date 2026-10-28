"""12C2H4: convert tensorial (J, C, n) / (J, C, alpha) labels to (12 vib QNs, J, Ka, Kc).

Rule (Vander Auwera 2013, dijon_to_kakc.m): Gamma_rot = (Ka mod 2, Kc mod 2) with
ee=Ag, eo=B1g, oe=B2g, oo=B3g; C = Gamma_vib x Gamma_rot (D2h). Inside one complete
(vib, J, Gamma_rot) block, energy order = Ka order (near-prolate top).

    python3 scripts/c2h4_labels.py --selftest
"""
import re
import sys
from collections import defaultdict

D2 = {'A': 0, 'B1': 1, 'B2': 2, 'B3': 3}
D2_NAME = {v: k for k, v in D2.items()}
ROT = {(0, 0): 'Ag', (0, 1): 'B1g', (1, 0): 'B2g', (1, 1): 'B3g'}


# Mode symmetries in the TheoReTS / jener axis convention (checked against every mmc5/mmc6 label).
MODE_SYM = ('Ag', 'Ag', 'Ag', 'Au', 'B2g', 'B2g', 'B2u', 'B3g', 'B3u', 'B3u', 'B1u', 'B1u')


def vib_sym(v):
    g = 'Ag'
    for n, m in zip(v, MODE_SYM):
        for _ in range(n):
            g = mul(g, m)
    return g


def allowed(vu, qu, vl, ql):
    """Electric-dipole rule: (Gamma_vib x Gamma_rot)_u x (...)_l = Au, |Delta J| <= 1."""
    return abs(qu[0] - ql[0]) <= 1 and \
        mul(mul(vib_sym(vu), grot(*qu[1:])), mul(vib_sym(vl), grot(*ql[1:]))) == 'Au'


def norm_sym(s):
    """'A g' / 'A ' / 'Ag' / 'b1u' -> 'Ag' / 'A' / 'Ag' / 'B1u'."""
    s = s.replace(' ', '')
    return s[0].upper() + s[1:].lower()


def mul(a, b):
    """D2h product of two irreps ('B1u' x 'B3g' = 'B2u'); parity dropped if either lacks it."""
    a, b = norm_sym(a), norm_sym(b)
    pa, pb = a[-1] if a[-1] in 'gu' else '', b[-1] if b[-1] in 'gu' else ''
    d = D2_NAME[D2[a.rstrip('gu')] ^ D2[b.rstrip('gu')]]
    if pa and pb:
        return d + ('g' if pa == pb else 'u')
    return d


def grot(ka, kc):
    return ROT[(ka % 2, kc % 2)]


def block_levels(J, gr):
    """All (Ka, Kc) of a (J, Gamma_rot) block, in Ka (= energy) order."""
    out = []
    for ka in range(J + 1):
        for kc in (J - ka, J - ka + 1):
            if 0 <= kc <= J and grot(ka, kc) == gr:
                out.append((ka, kc))
    return out


def rank_to_kakc(J, gr, rank):
    lev = block_levels(J, gr)
    return lev[rank - 1] if 1 <= rank <= len(lev) else None


def _dijon_port(J, S, N):
    """Literal port of dijon_to_kakc.m (S = rotational symmetry, D2 name)."""
    Ka, par = 2 * (N - 1), J % 2
    if S in ('B2', 'B3'):
        Ka += 1
    elif (par == 0 and S == 'B1') or (par == 1 and S == 'A'):
        Ka += 2
    Kc = J - Ka
    if (par == 0 and S in ('B2', 'B1')) or (par == 1 and S in ('B3', 'A')):
        Kc += 1
    return Ka, Kc


# 12 single-digit quanta + symmetry; 23MrMaReAr glues a 13th digit to the symmetry ('0B1u').
VIB_RE = re.compile(r'(?<![\d.])((?:\d\s+){11}\d)(?:\s+\d(?=[AB]))?\s*(A\s?[gu]|B[123]\s?[gu])(?=\s|$)')
SYM_TOK = r'(?:A\s?[gu]|B[123]\s?[gu])'


def vibs(line):
    """All (12-tuple, sym) vibrational labels in a line, in order."""
    return [(tuple(int(x) for x in m.group(1).split()), norm_sym(m.group(2)))
            for m in VIB_RE.finditer(line)]


class Levels:
    """Variational levels keyed by (J, C, n, P): energy, vib label, vib sym, Gamma_rot.

    TheoReTS n counts levels within (J, C, P), P = total vib quanta (sum of v): in the
    23MrMaReAr lists (J, C, n) alone repeats at different energies, (J, C, n, P) never does.
    """

    def __init__(self):
        self.lev = {}
        self.clash = []   # same key, different vib label or energy

    def add(self, J, C, n, E, vib, cv, cr=None, src=''):
        k = (J, norm_sym(C), n, sum(vib))
        if cr is None:
            cr = mul(C, cv)
        new = (E, vib, norm_sym(cv), norm_sym(cr))
        old = self.lev.get(k)
        if old is None:
            self.lev[k] = new
        elif old[1] != vib or abs(old[0] - E) > 0.01:
            self.clash.append((k, old, new, src))

    def assign(self):
        """key -> (vib, J, Ka, Kc, rank, block_size_found, block_size_expected)."""
        blocks = defaultdict(list)
        for k, (E, vib, cv, cr) in self.lev.items():
            blocks[(vib, k[0], cr)].append((E, k))
        out = {}
        for (vib, J, cr), lst in blocks.items():
            lst.sort()
            exp = len(block_levels(J, cr))
            for r, (E, k) in enumerate(lst, 1):
                kk = rank_to_kakc(J, cr, r)
                out[k] = (vib, J) + (kk if kk else (None, None)) + (r, len(lst), exp)
        return out


def read_theorets_list(path, lv):
    """23MrMaReAr mmc5/mmc6: Freq I A Ji Ci ni Js Cs ns Einf Kri Cri Krs Crs vib_i Cv vib_s Cv."""
    for line in open(path, encoding='latin-1'):
        t = line.split()
        if len(t) != 40 or not t[0][0].isdigit():
            continue
        nu, Ji, Ci, ni, Js, Cs, ns, Ei = float(t[0]), int(t[3]), t[4], int(t[5]), int(t[6]), t[7], int(t[8]), float(t[9])
        Cri, Crs = t[11], t[13]
        vi, vs = tuple(map(int, t[14:26])), tuple(map(int, t[27:39]))
        lv.add(Ji, Ci, ni, Ei, vi, t[26], Cri, path)
        lv.add(Js, Cs, ns, Ei + nu, vs, t[39], Crs, path)


RAW = '/mnt/c/Code/_raw_data_store/Polyatomics/Ethylene/'
SRC = RAW + 'Sources/'
SYMFIX = re.compile(r'\b([AB][123]?) ([gu])\b')


def _split(line):
    """(tokens before 1st vib label, (vib_l, cv_l), (vib_u, cv_u), tokens after 2nd), or None."""
    m = list(VIB_RE.finditer(line))
    if len(m) != 2:
        return None
    v = vibs(line)
    return (SYMFIX.sub(r'\1\2', line[:m[0].start()]).split(), v[0], v[1],
            SYMFIX.sub(r'\1\2', line[m[1].end():]).split())


def _rec(wn, Jl, Cl, nl, vl, El, Ju, Cu, nu, vu, Eu, **kw):
    r = dict(wn=wn, Jl=int(Jl), Cl=norm_sym(Cl), nl=int(nl), vl=vl[0], cvl=vl[1], El=El,
             Ju=int(Ju), Cu=norm_sym(Cu), nu=int(nu), vu=vu[0], cvu=vu[1], Eu=Eu, Kl=None, Ku=None)
    r.update(kw)
    return r


def read_23MrMaReAr():
    """data.txt: Pos Int Freq I A Elow vib_u vib_l JuCu nu Eu JlCl nl (upper label first; J, C fused)."""
    out = []
    for line in open(SRC + '23MrMaReAr/23MrMaReAr data.txt', encoding='latin-1'):
        s = _split(line)
        if s:
            b, vu, vl, a = s
            (Ju, Cu), nu, Eu, (Jl, Cl), nl = re.match(r'(\d+)([AB]\d?[gu])', a[0]).groups(), a[1], a[2], \
                re.match(r'(\d+)([AB]\d?[gu])', a[3]).groups(), a[4]
            out.append(_rec(float(b[0]), Jl, Cl, nl, vl, float(b[5]), Ju, Cu, nu, vu, float(Eu)))
    return out


def read_reims(path, ncol):
    """Reims lists (24BeBeReMa SM1/SM2, 24BeReCa mmc2, 25BeBeReCa mmc1):
    [ISO] Pos [Int] Freq I [I'] A Jl Cl nl Ju Cu nu Elow Ka_l Cr_l Ka_u Cr_u vib_l vib_u <after>.
    ncol = columns from Freq to A (3, or 4 with I'). Ka (always 0 except in 25BeBeReCa) and Cr
    can be missing as a pair."""
    out = []
    for line in open(path, encoding='latin-1'):
        s = _split(line)
        if not s:
            continue
        b, vl, vu, a = s
        star = b[0].startswith('*')
        b = [x.lstrip('*') for x in b if x != '*']
        k = max(i for i, x in enumerate(b) if '.' in x)    # Elow: Ka/Cr after it may be missing
        rest = b[k + 1:]
        if len(rest) == 2:
            rest = [rest[0], None, rest[1], None]
        b = b[:k + 1] + (rest or ['0', None, '0', None])
        Jl, Cl, nl, Ju, Cu, nu, El, Kal, Crl, Kau, Cru = b[-11:]
        El, fv = float(El), float(b[-11 - ncol])
        iso = b.pop(0) if ncol == 4 else ''     # 25BeBeReCa: 381; '13C' = 382 in HITRAN; '281' typo
        if iso == '382':
            continue
        out.append(_rec(float(b[0]), Jl, Cl, nl, vl, El, Ju, Cu, nu, vu, El + fv,
                        Ka=(int(Kal), int(Kau)), Cr=(Crl, Cru), star=star, iso=iso, after=a))
    return out


def read_24PeLeSuRu():
    """SupMat1: Pos Abs Int Freq I A Einf vib_l vib_u Ji Ci ni Jf Cf nf d(nu) I-ratio [12+12 vib, J Ka Kc x2]."""
    out = []
    for line in open(SRC + '24PeLeSuRu/SupMat1.txt', encoding='latin-1'):
        s = _split(line)
        if s:
            b, vl, vu, a = s
            El = float(b[-1])
            r = _rec(float(b[0]), a[0], a[1], a[2], vl, El, a[3], a[4], a[5], vu, El + float(b[-4]))
            if len(a) >= 38:    # second label set: v x12 lower, v x12 upper, J Ka Kc lower, upper
                r['Kl'], r['Ku'] = tuple(map(int, a[32:35])), tuple(map(int, a[35:38]))
            out.append(r)
    return out


def read_26PeLeSuRu():
    """SupMat2 (cold) / SupMat3 (hot): Pos [Pos_LIPhy diff] Freq diff I A E'' vib_l vib_u
    [Jl Cl nl Ju Cu nu] Jl Ka Kc Ju Ka Kc. Rows without a variational match have no (J, C, n)."""
    out = []
    for f in ('SupMat2.txt', 'SupMat3.txt'):
        for line in open(SRC + '26PeLeSuRu/' + f, encoding='latin-1'):
            s = _split(line)
            if not s:
                continue
            b, vl, vu, a = s
            Kl, Ku = tuple(map(int, a[-6:-3])), tuple(map(int, a[-3:]))
            if len(a) == 12:
                El = float(b[-1])
                r = _rec(float(b[0]), a[0], a[1], a[2], vl, El, a[3], a[4], a[5], vu, El + float(b[-5]))
            else:
                r = dict(wn=float(b[0]), Jl=Kl[0], Cl=None, nl=None, vl=vl[0], cvl=vl[1], El=None,
                         Ju=Ku[0], Cu=None, nu=None, vu=vu[0], cvu=vu[1], Eu=None)
            r.update(Kl=Kl[1:], Ku=Ku[1:], file=f)
            out.append(r)
    return out


def read_theorets_sources():
    import glob
    d = glob.glob(SRC + '24BeBe*ReMa')[0] + '/'
    return {'23MrMaReAr': read_23MrMaReAr(),
            '24BeBeReMa': read_reims(d + 'rev-SM1_296K_31-05-2024.txt', 3)
            + read_reims(d + 'rev_SM2_130K_3 bands_19-04-2024.txt', 3),
            '24BeReCa': read_reims(SRC + '24BeReCa/1-s2.0-S0022407324000128-mmc2.txt', 3),
            '24PeLeSuRu': read_24PeLeSuRu(),
            '25BeBeReCa': read_reims(SRC + '25BeBeReCa/mmc1.txt', 4),
            '26PeLeSuRu': read_26PeLeSuRu()}


# QN (user-approved 2026-10-28): 25BeBeReCa ground-state lower labels come from (J, C, n), not the
# printed Ka (wrong on 234 lines); one n typo is corrected.
N_TYPO = {('25BeBeReCa', 20, 'Ag', 11): 9,
          ('25BeBeReCa', 20, 'B1g', 10): 8}   # QU: doublet twin on the same exp line (approved 2026-10-28)
SAME_COUNTER = ('23MrMaReAr', '24BeBeReMa', '24BeReCa')   # n-consistency check vs mmc5/mmc6
GIVEN_KAKC = ('25BeBeReCa', '26PeLeSuRu')                    # print Ka (and Kc) next to (J, C, n)


def bad_label(J, Ka, Kc, C, cv):
    """Reason a (J, Ka, Kc) label is impossible for total symmetry C and vib symmetry cv, else None."""
    if not (0 <= Ka <= J and 0 <= Kc <= J and Ka + Kc in (J, J + 1)):
        return 'Ka+Kc not J or J+1'
    if C and mul(cv, grot(Ka, Kc)) != norm_sym(C):
        return 'C != Gamma_vib x Gamma_rot(Ka,Kc): %s x %s != %s' % (cv, grot(Ka, Kc), C)
    return None


def kc_for(J, Ka, gr):
    """The Kc in {J-Ka, J-Ka+1} that puts (Ka, Kc) in rotational symmetry gr."""
    for kc in (J - Ka, J - Ka + 1):
        if 0 <= kc <= J and grot(Ka, kc) == gr:
            return kc
    return None


def jcn(r, sd):
    return '%s %s %s' % (r['J' + sd], r['C' + sd], r['n' + sd]) if r['n' + sd] is not None else ''


def theorets_reference(R):
    """mmc5/mmc6 levels plus the levels of every source that shares their n counter."""
    lv = Levels()
    for f in ('mmc6', 'mmc5'):
        read_theorets_list(SRC + '23MrMaReAr/1-s2.0-S0022407323002522-%s.txt' % f, lv)
    for tag in SAME_COUNTER:
        for r in R[tag]:
            for sd in 'lu':
                lv.add(r['J' + sd], r['C' + sd], r['n' + sd], r['E' + sd], r['v' + sd], r['cv' + sd], src=tag)
    return lv


def convert_theorets(R):
    """-> rows {tag: [row]}, conflicts [(tag, wn, side, kind, detail)]. A row is
    (wn, vib_u, (J, Ka, Kc)_u, vib_l, (J, Ka, Kc)_l, original label, note)."""
    lv = theorets_reference(R)
    A = lv.assign()
    rows, conf = defaultdict(list), []
    for tag in SAME_COUNTER:
        for r in R[tag]:
            lab, why = {}, []
            for sd in 'lu':
                k = (r['J' + sd], r['C' + sd], r['n' + sd], sum(r['v' + sd]))
                vib, J, Ka, Kc, rank, found, exp = A[k]
                if found != exp:
                    why.append((sd, 'incomplete block' if found < exp else 'overfull block',
                                '%s %s: %s vib %s Gamma_rot %s, %d of %d levels, rank %d' % (
                                    'upper' if sd == 'u' else 'lower', jcn(r, sd), k, vib,
                                    mul(r['C' + sd], r['cv' + sd]), found, exp, rank)))
                lab[sd] = (vib, (J, Ka, Kc))
            if why:
                conf += [(tag, r['wn'], sd, kind, d) for sd, kind, d in why]
                continue
            note = 'doublet: one exp line for two variational components' if r.get('star') else ''
            rows[tag].append((r['wn'], lab['u'][0], lab['u'][1], lab['l'][0], lab['l'][1],
                              '%s <- %s' % (jcn(r, 'u'), jcn(r, 'l')), note))
    own = Levels()   # QW: 25BeBeReCa's own upper levels, ranked inside (vib, J, Gamma_rot)
    for r in R['25BeBeReCa']:
        own.add(r['Ju'], r['Cu'], r['nu'], r['Eu'], r['vu'], r['cvu'])
    own = own.assign()
    for tag in GIVEN_KAKC:
        for r in R[tag]:
            lab, why = {}, []
            for sd in 'lu':
                J, C, cv = r['J' + sd], r['C' + sd], r['cv' + sd]
                if (tag, J, C, r['n' + sd]) in N_TYPO and sd == 'l':
                    r.setdefault('notes', []).append('QN: lower n %d printed, %d (energy check)' % (
                        r['nl'], N_TYPO[(tag, J, C, r['nl'])]))
                    r['nl'] = N_TYPO[(tag, J, C, r['nl'])]
                if tag == '25BeBeReCa' and sd == 'l' and sum(r['vl']) == 0 and gs_kakc(J, C, r['nl']):
                    # printed ground-state Ka is wrong on 234 lines; (J, C, n) is not (CD spread 0 this way)
                    Ka, Kc = gs_kakc(J, C, r['nl'])
                    if Ka != r['Ka'][0]:
                        r.setdefault('notes', []).append('QN: Ka_l %d printed, %d from (J,C,n)' % (r['Ka'][0], Ka))
                elif tag == '25BeBeReCa' and sd == 'u' and J >= 25 and r['Ka'][1] <= 4 and \
                        own[(J, C, r['nu'], sum(r['vu']))][2] is not None:
                    # QW (approved 2026-10-28): printed upper Ka fails at high J / low Ka (rank right 42/45)
                    Ka, Kc = own[(J, C, r['nu'], sum(r['vu']))][2:4]
                    if Ka != r['Ka'][1]:
                        r.setdefault('notes', []).append('QW: Ka_u %d printed, %d from (J,C,n) rank' % (r['Ka'][1], Ka))
                elif tag == '25BeBeReCa':
                    Ka, Kc_printed = r['Ka'][0 if sd == 'l' else 1], r['after'][2 if sd == 'l' else 3]
                    Kc = kc_for(J, Ka, mul(C, cv)) if Ka <= J else None
                    if Kc is None:
                        why.append((sd, 'impossible label', 'Ka %d for J %d' % (Ka, J)))
                        continue
                    if str(Kc) != Kc_printed:
                        r.setdefault('notes', []).append('Kc_%s %s -> %d from C rule' % (sd, Kc_printed, Kc))
                else:
                    Ka, Kc = r['K' + sd]
                b = bad_label(J, Ka, Kc, C, cv)
                if b:
                    why.append((sd, 'impossible label', '%s %s (%d %d %d): %s' % (jcn(r, sd), r['v' + sd], J, Ka, Kc, b)))
                lab[sd] = (r['v' + sd], (J, Ka, Kc))
            if why:
                conf += [(tag, r['wn'], sd, kind, d) for sd, kind, d in why]
                continue
            note = '; '.join(r.get('notes', []) + ([r['iso']] if r.get('iso') not in (None, '', '381') else []))
            rows[tag].append((r['wn'], lab['u'][0], lab['u'][1], lab['l'][0], lab['l'][1],
                              '%s <- %s' % (jcn(r, 'u'), jcn(r, 'l')), note))
    # one full label carried by two different (J, C, n) levels in one source
    for tag, lst in rows.items():
        seen = defaultdict(set)
        for row in lst:
            u, l = row[5].split(' <- ')
            seen[(row[1], row[2])].add(u)
            seen[(row[3], row[4])].add(l)
        for (vib, q), ks in seen.items():
            if len(ks - {''}) > 1:
                conf.append((tag, '', '', 'one label, two (J,C,n)', '%s %s <- %s' % (vib, q, sorted(ks))))
    return rows, conf, lv


# ---- Dijon (tensorial J, C, alpha) ----
JENER = RAW + 'Correspondence with Vincent and Cyril/'
CIDX = {1: 'A', 2: 'B1', 3: 'B2', 4: 'B3'}   # jener C index; from J=0 levels of known vib symmetry
V = lambda *q: tuple(1 if i + 1 in q else 0 for i in range(12))
# jener #vib order, from the J=0 levels (schem1) and the 24BeVaTuBo sublevel list (schem2)
JENER_VIBS = {'jener_schem1.txt': [(V(12), 'B1u'), (V(4), 'Au'), (V(7), 'B2u'), (V(10), 'B3u')],
              'jener_schem2.txt': [(V(9), 'B3u'), (V(11), 'B1u'), (V(2, 12), 'B1u'), (V(2, 10), 'B3u'),
                                   ((0,) * 9 + (2, 0, 1), 'B1u')]}
JENER_RE = re.compile(r'^\s*(-?[\d.]+)\s+(\d+)\s+([1-4])\s+(\d)\s*(\d+)\s+(\d+)\s+(\d+)%')


def read_jener(name):
    """(J, C, n) -> (E, #vib, main-component %), C as a D2 name. n >= 100 is fused to P ('2100')."""
    out, on = {}, False
    for line in open(JENER + name, encoding='latin-1'):
        if 'Energy   J  C  P  n' in line:
            on = True
            continue
        m = JENER_RE.match(line) if on else None
        if m:
            E, J, C, P, n, vib, pct = m.groups()
            out[(int(J), CIDX[int(C)], int(n))] = (float(E), int(vib), int(pct))
    return out


def dijon_assign(name):
    """jener levels -> (J, C, n) -> (vib, vibsym, Ka, Kc, rank, pct); ranks inside each (#vib, J, C)."""
    lev, vibs_ = read_jener(name), JENER_VIBS[name]
    blocks = defaultdict(list)
    for (J, C, n), (E, vib, pct) in lev.items():
        blocks[(vib, J, C)].append((E, n, pct))
    out = {}
    for (vib, J, C), lst in blocks.items():
        v, cv = vibs_[vib - 1]
        gr = mul(C, cv) + 'g'
        for r, (E, n, pct) in enumerate(sorted(lst), 1):
            ka, kc = rank_to_kakc(J, gr, r) or (None, None)
            out[(J, C, n)] = (v, cv, ka, kc, r, pct)
    return out


def gs_kakc(J, C, n):
    """Ground state: Gamma_rot = C, rank = n."""
    return rank_to_kakc(J, norm_sym(C).rstrip('gu') + 'g', n)


def read_24BeVaTuBo():
    """24BeVaTuBo.txt (Fexp Fcal Jl Cl nl Ju Cu nu sublevel), with (J, C, n) taken from the
    calculated list mmc3 (matched on Fcal and J, C): the .txt prints lower n=4 as 5 in 532 rows."""
    calc = defaultdict(list)
    for line in open(SRC + '24BeVaTuBo/1-s2.0-S002240732400102X-mmc3.txt', encoding='latin-1'):
        t = SYMFIX.sub(r'\1\2', line).split()
        if len(t) >= 14 and t[2] in ('P', 'Q', 'R'):
            calc[round(float(t[0]), 3)].append((int(t[3]), t[4], int(t[5]), int(t[8]), t[9], int(t[10])))
    out = []
    for line in open(SRC + '24BeVaTuBo/24BeVaTuBo.txt', encoding='latin-1'):
        t = line.split()
        if len(t) != 9 or not t[2].isdigit():
            continue
        fc = round(float(t[1]), 3)
        Jl, Cl, nl, Ju, Cu, nu = int(t[2]), t[3], int(t[4]), int(t[5]), t[6], int(t[7])
        cs = [x for d in (-0.001, 0, 0.001) for x in calc.get(round(fc + d, 3), [])
              if (x[0], x[1], x[3], x[4]) == (Jl, Cl, Ju, Cu)]
        r = dict(wn=float(t[0]), Jl=Jl, Cl=Cl, nl=nl, Ju=Ju, Cu=Cu, nu=nu, sub=int(t[8]), printed=(nl, nu))
        if len(cs) == 1:
            r['nl'], r['nu'] = cs[0][2], cs[0][5]
        r['mmc3'] = len(cs)
        out.append(r)
    return out


def convert_dijon():
    """24BeVaTuBo (jener_schem2) and 16AlBoRoBo (jener_schem1): lower = ground state, rank = n;
    upper = jener main component, re-ranked inside (#vib, J, C)."""
    rows, conf = defaultdict(list), []
    D2_ = dijon_assign('jener_schem2.txt')
    for r in read_24BeVaTuBo():
        lbl = '%d %s %d <- %d %s %d' % (r['Ju'], r['Cu'], r['nu'], r['Jl'], r['Cl'], r['nl'])
        if r['mmc3'] != 1:
            conf.append(('24BeVaTuBo', r['wn'], '', 'no unique mmc3 match', lbl + ' (as printed)'))
            continue
        note = '' if (r['nl'], r['nu']) == r['printed'] else 'n from mmc3; .txt prints %d / %d' % (r['printed'][1], r['printed'][0])
        if note:
            conf.append(('24BeVaTuBo', r['wn'], '', 'printed n differs from mmc3 (kept, mmc3 n)', lbl + '; ' + note))
        gl = gs_kakc(r['Jl'], r['Cl'], r['nl'])
        a = D2_.get((r['Ju'], norm_sym(r['Cu']).rstrip('gu'), r['nu']))
        if gl is None or a is None or a[2] is None:
            conf.append(('24BeVaTuBo', r['wn'], '', 'impossible label', lbl))
            continue
        if a[5] < 72:
            conf.append(('24BeVaTuBo', r['wn'], 'u', 'low-purity Dijon level', '%s: main component %d%% %s' % (lbl, a[5], a[0])))
            continue
        if JENER_VIBS['jener_schem2.txt'][r['sub'] - 1][0] != a[0]:
            note = (note + '; ' if note else '') + 'sublevel %d printed, jener main component %s' % (r['sub'], a[0])
        rows['24BeVaTuBo'].append((r['wn'], a[0], (r['Ju'], a[2], a[3]), (0,) * 12, (r['Jl'],) + gl, lbl, note))
    D1 = dijon_assign('jener_schem1.txt')
    for line in open(SRC + '16AlBoRoBo/supmat_positions.txt', encoding='latin-1'):
        t = SYMFIX.sub(r'\1\2', line).split()
        if len(t) != 15 or not t[0].startswith('v'):
            continue
        Ju, Cu, Nu, Jl, Cl, Nl = int(t[5]), t[6], int(t[7]), int(t[10]), t[11], int(t[12])
        lbl = '%d %s %d <- %d %s %d' % (Ju, Cu, Nu, Jl, Cl, Nl)
        a, gl = D1[(Ju, norm_sym(Cu).rstrip('gu'), Nu)], gs_kakc(Jl, Cl, Nl)
        if (a[2], a[3]) != (int(t[8]), int(t[9])) or gl != (int(t[13]), int(t[14])):
            conf.append(('16AlBoRoBo', float(t[1]), '', 'rule disagrees with printed Ka Kc', lbl))
        if a[5] < 72:
            conf.append(('16AlBoRoBo', float(t[1]), 'u', 'low-purity Dijon level', '%s: main component %d%% %s' % (lbl, a[5], a[0])))
            continue
        rows['16AlBoRoBo'].append((float(t[1]), a[0], (Ju, a[2], a[3]), (0,) * 12, (Jl,) + gl, lbl, 'spectrum ' + t[2]))
    return rows, conf


SWAP23 = {'B2': 'B3', 'B3': 'B2'}


def swap23(C):
    """10LoBoLoRo P2 names the b and c axes the other way round (nu9 = B2u, 1_11 = B2g)."""
    C = norm_sym(C)
    return SWAP23.get(C[:2], C[:2]) + C[2:] if C[0] == 'B' else C


def read_10LoBoLoRo():
    """-> {'P2': [...], 'P3': [...]}: Fexp Diff Fcal vib pct% Jl Cl al Ju Cu au."""
    out, part = {'P2': [], 'P3': []}, None
    for line in open(SRC + '10LoBoLoRo/10LoBoLoRo Supplementary Data.txt', encoding='latin-1'):
        if 'P2mP0' in line:
            part = 'P2'
        elif 'P3mP0' in line:
            part = 'P3'
        t = SYMFIX.sub(r'\1\2', line).split()
        if part and len(t) == 11 and t[4].endswith('%'):
            out[part].append(dict(wn=float(t[0]), vib=int(t[3]), pct=int(t[4][:-1]), Jl=int(t[5]), Cl=t[6],
                                  nl=int(t[7]), Ju=int(t[8]), Cu=t[9], nu=int(t[10])))
    return out


def convert_10LoBoLoRo_P2(recs):
    """Dyad nu9/nu11, no jener file: rank inside the source's own (J, C) levels. A level's rank is
    exact only when every alpha below it in its (J, C) appears in the list."""
    vibs_ = {1: (V(9), 'B3u'), 2: (V(11), 'B1u')}
    lev = defaultdict(dict)
    for r in recs:
        lev[(r['Ju'], swap23(r['Cu']))][r['nu']] = (r['vib'], r['pct'])
    rows, conf = [], []
    for r in recs:
        Cu, Cl = swap23(r['Cu']), swap23(r['Cl'])
        lbl = '%d %s %d <- %d %s %d (printed)' % (r['Ju'], r['Cu'], r['nu'], r['Jl'], r['Cl'], r['nl'])
        known = lev[(r['Ju'], Cu)]
        gl = gs_kakc(r['Jl'], Cl, r['nl'])
        if r['pct'] < 72:
            conf.append(('10LoBoLoRo', r['wn'], 'u', 'low-purity Dijon level', '%s: main component %d%%' % (lbl, r['pct'])))
            continue
        if len(set(v for v, p in known.values())) and known[r['nu']][0] != r['vib']:
            conf.append(('10LoBoLoRo', r['wn'], 'u', 'one J,C,n with two labels', lbl))
            continue
        if any(a not in known for a in range(1, r['nu'])):
            conf.append(('10LoBoLoRo', r['wn'], 'u', 'incomplete block',
                         '%s: alpha %s missing' % (lbl, [a for a in range(1, r['nu']) if a not in known])))
            continue
        rank = sum(1 for a in range(1, r['nu'] + 1) if known[a][0] == r['vib'])
        v, cv = vibs_[r['vib']]
        ku = rank_to_kakc(r['Ju'], mul(Cu, cv), rank)
        if gl is None or ku is None:
            conf.append(('10LoBoLoRo', r['wn'], '', 'impossible label', lbl))
            continue
        rows.append((r['wn'], v, (r['Ju'],) + ku, (0,) * 12, (r['Jl'],) + gl, lbl, 'B2/B3 swapped to jener convention'))
    return rows, conf


def convert_10LoBoLoRo_P3(recs, R, rows):
    """No jener file: take the label of the 24BeReCa / 26PeLeSuRu line at the same wavenumber
    (within 0.005 cm-1) from the same ground-state level (B2/B3 swapped as in P2)."""
    lab = {}
    for tag in ('24BeReCa', '26PeLeSuRu'):
        for row in rows.get(tag, []):
            lab.setdefault((row[0], row[4]), set()).add((row[1], row[2], tag))
    cand = []
    for tag in ('24BeReCa', '26PeLeSuRu'):
        for r in R[tag]:
            if sum(r['vl']) == 0:
                gl = tuple(r['Kl']) if tag == '26PeLeSuRu' else gs_kakc(r['Jl'], r['Cl'], r['nl'])
                cand.append((r['wn'], (r['Jl'],) + gl))
    cand.sort()
    ws = [c[0] for c in cand]
    out, conf, nmatch = [], [], 0
    import bisect
    for r in recs:
        lbl = '%d %s %d <- %d %s %d (printed)' % (r['Ju'], r['Cu'], r['nu'], r['Jl'], r['Cl'], r['nl'])
        if r['wn'] < 6030:     # QT 2026-10-28: the paper recorded 6030-6250 cm-1 only
            conf.append(('10LoBoLoRo', r['wn'], '', 'P3 line outside recorded range (held out)', lbl))
            continue
        gl = gs_kakc(r['Jl'], swap23(r['Cl']), r['nl'])
        if gl is None:
            conf.append(('10LoBoLoRo', r['wn'], 'l', 'impossible label', lbl))
            continue
        gl = (r['Jl'],) + gl
        i = bisect.bisect_left(ws, r['wn'] - 0.005)
        m = [c for c in cand[i:i + 30] if abs(c[0] - r['wn']) <= 0.005 and c[1] == gl]
        if not m:
            conf.append(('10LoBoLoRo', r['wn'], 'u', 'P3 unmatched', lbl))
            continue
        nmatch += 1
        ups = set().union(*[lab.get(c, set()) for c in m])
        if len({(v, q) for v, q, t in ups}) != 1:
            conf.append(('10LoBoLoRo', r['wn'], 'u', 'P3 matched, partner label not converted' if not ups
                          else 'P3 matched, partners disagree', '%s: %s' % (lbl, sorted(ups))))
            continue
        v, q, t = sorted(ups)[0]
        out.append((r['wn'], v, q, (0,) * 12, gl, lbl, 'upper label from %s line at %.5f' % (t, m[0][0])))
    return out, conf, nmatch


def convert_26HjSiCaSi(A, rows):
    """csv/26HjSiCaSi_extract.tsv (3 pump + 14 V-type lines, all from GS (4, Ag, 1) = 4_04).
    V-type uppers carry the 23MrMaReAr (J, C, N) and go through its blocks; pump uppers (nu9)
    take the label of the 25BeBeReCa line within 0.0005 cm-1 from the same lower level."""
    path = OUT + '../csv/26HjSiCaSi_extract.tsv'
    out, conf = [], []
    low = (4,) + gs_kakc(4, 'Ag', 1)
    for line in open(path):
        if line.startswith(('#', 'kind')):
            continue
        kind, wn, ud, J, C, N, vib = line.split('\t')[:7]
        wn, J, N = float(wn), int(J), int(N)
        v = tuple(int(x) for x in vib.split()[:12])
        unc = int(ud) * 10 ** -len(wn_frac(line.split('\t')[1]))
        lbl = '%d %s %d <- 4 Ag 1' % (J, C, N)
        if kind == 'vtype':
            a = A.get((J, C, N, sum(v)))
            if a is None or a[0] != v or a[5] != a[6]:
                conf.append(('26HjSiCaSi', wn, 'u', 'incomplete block' if a else 'not in 23MrMaReAr list', lbl))
                continue
            out.append((wn, v, (J, a[2], a[3]), (0,) * 12, low, lbl, 'V-type; unc %.0e from paper' % unc, unc))
        else:
            m = {(r[1], r[2]) for r in rows['25BeBeReCa'] if abs(r[0] - wn) <= 0.0005 and r[4] == low}
            if len(m) != 1:
                conf.append(('26HjSiCaSi', wn, 'u', 'pump: no unique 25BeBeReCa partner', '%s: %s' % (lbl, m)))
                continue
            (vu, qu), = m
            out.append((wn, vu, qu, (0,) * 12, low, lbl, 'pump; upper label from 25BeBeReCa; unc %.0e from paper' % unc, unc))
    return out, conf


def convert_18AsRa():
    """csv/18AsRa_extract.tsv: nu11 <- GS, printed J Ka Kc. Keeps a row only when both labels
    are possible and Gamma_vib(nu11) x Gamma_rot(upper) = Gamma_rot(lower) with g -> u."""
    out, conf = [], []
    for line in open(OUT + '../csv/18AsRa_extract.tsv'):
        if line.startswith(('#', 'table')):
            continue
        t = line.rstrip('\n').split('\t')
        qu, ql, wn = tuple(map(int, t[1:4])), tuple(map(int, t[4:7])), float(t[7])
        lbl = '%s %s <- %s (printed, %s)' % (qu, 'nu11', ql, t[0])
        b = bad_label(*qu, None, 'B1u') or bad_label(*ql, None, 'Ag') or (
            None if abs(qu[0] - ql[0]) <= 1 and mul('B1u', grot(*qu[1:])) == mul(grot(*ql[1:]), 'Au')
            else 'symmetry or Delta J forbids nu11 <- GS')
        if b:
            conf.append(('18AsRa', wn, '', 'impossible label', '%s: %s; 25BeBeReCa: %s' % (lbl, b, t[8])))
            continue
        out.append((wn, V(11), qu, (0,) * 12, ql, lbl, 'caption says nu9; upper energy is nu11'))
    return out, conf


HITRAN_VIB = {'GROUND': ((0,) * 12, 'Ag'), 'V11': (V(11), 'B1u'), 'V9': (V(9), 'B3u'), 'V10': (V(10), 'B3u'),
              'V2+V12': (V(2, 12), 'B1u'), '2V10+V12': ((0,) * 9 + (2, 0, 1), 'B1u'), 'V9+V10': (V(9, 10), 'Ag')}


def convert_25BeBeReCa_hitran():
    """25BeBeReCa mmc1 lines the authors left unassigned, with the HITRAN2020 labels printed next to
    them (user decision 2026-10-28: include). Kept when Ka Kc are possible and the dipole rule holds."""
    out, conf = [], []
    for line in open(SRC + '25BeBeReCa/mmc1.txt', encoding='latin-1'):
        t = line.split()
        if not t or t[0] not in ('381', '281', '13C') or len(t) not in (24, 25):
            continue
        m = re.search(r'\s([A-Z0-9+]+)\s+([A-Z0-9+]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s', line)
        (vu, cvu), (vl, cvl) = HITRAN_VIB[m.group(1)], HITRAN_VIB[m.group(2)]
        qu, ql = tuple(map(int, m.group(3, 4, 5))), tuple(map(int, m.group(6, 7, 8)))
        wn = float(t[1])
        lbl = 'HITRAN %s %s <- %s %s' % (m.group(1), qu, m.group(2), ql)
        b = bad_label(*qu, None, cvu) or bad_label(*ql, None, cvl) or (
            None if abs(qu[0] - ql[0]) <= 1 and mul(mul(cvu, grot(*qu[1:])), mul(cvl, grot(*ql[1:]))) == 'Au'
            else 'dipole rule broken')
        if b:
            conf.append(('25BeBeReCa', wn, '', 'impossible label', '%s: %s' % (lbl, b)))
            continue
        out.append((wn, vu, qu, vl, ql, 'HITRAN <- HITRAN', 'unassigned by 25BeBeReCa; HITRAN2020 label'))
    return out, conf


def convert_24PeLeSuRu(recs, rows26):
    """Own n counter, no list: copy the label of the 26PeLeSuRu line within 0.005 cm-1 that shares
    the lower level (user decision 2026-10-28). Lower: ground state, rank = n."""
    out, conf = [], []
    for r in recs:
        lbl = '%s <- %s' % (jcn(r, 'u'), jcn(r, 'l'))
        gl = gs_kakc(r['Jl'], r['Cl'], r['nl']) if sum(r['vl']) == 0 else None
        m = {(x[1], x[2]) for x in rows26 if gl and abs(x[0] - r['wn']) <= 0.005
             and x[3] == r['vl'] and x[4] == (r['Jl'],) + gl}
        if len(m) != 1:
            conf.append(('24PeLeSuRu', r['wn'], 'u', 'no unique 26PeLeSuRu match (own n counter, no list)',
                         '%s: %d candidates' % (lbl, len(m))))
            continue
        (vu, qu), = m
        out.append((r['wn'], vu, qu, r['vl'], (r['Jl'],) + gl, lbl, 'label via 26PeLeSuRu'))
    return out, conf


EXTRACTED = ('13LeTab', '13LeTac', '13LeTad', '88ThCoDeCo')   # pipeline extractions, csv/<id>_merged.csv
MHZ_PER_CM = 29979.2458


def convert_extracted(paper):
    """A reviewed pipeline extraction (already in J Ka Kc). Drops rows flagged for manual review or
    breaking the dipole rule; converts MHz rows to cm-1."""
    import csv
    out, conf = [], []
    for r in csv.DictReader(open(OUT + '../csv/%s_merged.csv' % paper)):
        q = lambda s: tuple(int(r[x + '_' + s]) for x in ('J', 'Ka', 'Kc'))
        v = lambda s: tuple(int(r['v%d_%s' % (i, s)]) for i in range(1, 13))
        wn, unc = float(r['transition_wavenumber']), float(r['uncertainty'])
        if 'unit: MHz' in r['notes']:
            wn, unc = wn / MHZ_PER_CM, unc / MHZ_PER_CM
        lbl = '%s %s <- %s (printed)' % (r['id'], q('upper'), q('lower'))
        if 'REQUIRES MANUAL REVIEW' in r['notes']:
            conf.append((paper, wn, '', 'requires manual review', '%s: %s' % (lbl, r['notes'])))
            continue
        b = bad_label(*q('upper'), None, 'Ag') or bad_label(*q('lower'), None, 'Ag')
        if b or not allowed(v('upper'), q('upper'), v('lower'), q('lower')):
            conf.append((paper, wn, '', 'impossible label', '%s: %s' % (lbl, b or 'dipole rule broken')))
            continue
        out.append((wn, v('upper'), q('upper'), v('lower'), q('lower'), r['id'], '', unc))
    return out, conf


def gs_energies():
    """Ground-state (J, Ka, Kc) -> energy from jener_v0 (the Dijon ground-state fit)."""
    out = {}
    for (J, C, n), (E, vib, pct) in read_jener('jener_v0_schema1.txt').items():
        k = gs_kakc(J, C, n)
        if k:
            out[(J,) + k] = E
    return out


def base_levels(tags, gs):
    """Upper levels of input_base lines from the ground state: (J, C) -> [(E, vib, (J, Ka, Kc))]."""
    out = defaultdict(list)
    for line in open(OUT + 'input_base.txt'):
        t = line.rstrip('\r\n').split('\t')
        if t[33].rsplit('.', 1)[0] not in tags or t[0].startswith('-'):
            continue
        vu, qu, vl, ql = tuple(map(int, t[3:15])), tuple(map(int, t[15:18])), tuple(map(int, t[18:30])), tuple(map(int, t[30:33]))
        if sum(vl) == 0 and ql in gs:
            out[(qu[0], mul(vib_sym(vu), grot(*qu[1:])))].append((gs[ql] + float(t[0]), vu, qu))
    return out


def relabel_16AlBoRoBo(rows, conf):
    """QE (user-approved 2026-10-28, until the corrigendum): an upper level matching a level of Su's
    13UlGrAsHo / 19UlBeGrRa / 08RoBoVa (same J and C, energy within 0.005 cm-1) takes that label;
    unmatched nu7/nu10 uppers with J >= 20 and Ka >= 11 are held out."""
    gs = gs_energies()
    su = base_levels({'13UlGrAsHo', '19UlBeGrRa', '08RoBoVa'}, gs)
    out, relab, held = [], set(), set()
    for row in rows:
        wn, vu, qu, vl, ql, orig, note = row
        E = gs[ql] + wn if ql in gs else None
        m = {(v, q) for e, v, q in su.get((qu[0], mul(vib_sym(vu), grot(*qu[1:]))), []) if E and abs(e - E) <= 0.005}
        if len(m) == 1 and m != {(vu, qu)}:
            (v2, q2), = m
            relab.add((vu, qu, v2, q2))
            out.append((wn, v2, q2, vl, ql, orig, (note + '; ' if note else '') +
                        'upper relabelled %s %s -> %s %s to match Su input (await corrigendum)' % (vu, qu, v2, q2)))
        elif not m and vu in (V(7), V(10)) and qu[0] >= 20 and qu[1] >= 11:
            held.add((vu, qu))
            conf.append(('16AlBoRoBo', wn, 'u', 'await corrigendum', '%s: %s %s, no Su level within 0.005' % (orig, vu, qu)))
        else:
            out.append(row)
    lev = defaultdict(list)   # a relabel must not land on a label another 16AlBoRoBo level already has
    for row in out:
        if row[4] in gs:
            lev[(row[1], row[2])].append(gs[row[4]] + row[0])
    clash = {k for k, es in lev.items() if max(es) - min(es) > 0.005}
    for row in out:
        if (row[1], row[2]) in clash:
            conf.append(('16AlBoRoBo', row[0], 'u', 'relabel clash (await corrigendum)',
                         '%s: %s %s now carried by two levels' % (row[5], row[1], row[2])))
    held |= {k for k in clash}
    return [r for r in out if (r[1], r[2]) not in clash], relab, held


def wn_frac(x):
    return x.split('.')[1] if '.' in x else ''


def cross_check(rows, tol=0.005):
    """Same line (wavenumber within tol, same lower level) in two sources with different upper labels."""
    import bisect
    allr = sorted((row[0], row[4], row[3], row[1], row[2], tag, i) for tag, lst in rows.items() for i, row in enumerate(lst))
    ws = [a[0] for a in allr]
    bad, conf = set(), []
    for a in allr:
        j = bisect.bisect_right(ws, a[0] + tol)
        for b in allr[bisect.bisect_left(ws, a[0]):j]:
            if b[5] != a[5] and b[1:3] == a[1:3] and b[3:5] != a[3:5]:
                bad |= {(a[5], a[6]), (b[5], b[6])}
                conf.append((a[5], a[0], 'u', 'sources disagree on upper label',
                             '%s %s vs %s %.5f %s %s (lower %s)' % (a[3], a[4], b[5], b[0], b[3], b[4], a[1])))
    return bad, conf


def xlsx_sheet(path, name):
    """Rows of one sheet as {column letter: text} (stdlib only)."""
    import zipfile
    import xml.etree.ElementTree as ET
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    rid = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
    z = zipfile.ZipFile(path)
    ss = [''.join(t.itertext()) for t in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', ns)]
    tgt = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    sh = [x for x in ET.fromstring(z.read('xl/workbook.xml')).find('m:sheets', ns) if x.get('name') == name][0]
    out = []
    for row in ET.fromstring(z.read('xl/' + tgt[sh.get(rid)].replace('/xl/', ''))).iter('{%s}row' % ns['m']):
        d = {}
        for c in row:
            v = c.find('m:v', ns)
            if v is not None:
                d[re.match('[A-Z]+', c.get('r')).group()] = ss[int(v.text)] if c.get('t') == 's' else v.text
        out.append(d)
    return out


# Position uncertainty per source, as the paper states it (scratchpad lookup 2026-10-28).
# None = not stated: rows are written with a blank uncertainty and need a user decision.
UNC = {'24BeReCa': 0.001, '25BeBeReCa': 0.0002, '24BeVaTuBo': 0.0002, '16AlBoRoBo': 0.0001,
       '23MrMaReAr': None, '24BeBeReMa': None, '26PeLeSuRu': None, '10LoBoLoRo': None}
OUT = '/mnt/c/Code/MARVEL_scraping/molecules/C2H4/convert/'
UNC_ROW = {}   # (tag, wn) -> per-line uncertainty printed by the paper
# Lines negated (kept but excluded by MARVEL), user-approved: (tag, orig_label) -> reason
NEGATE = {(t[0], round(float(t[1]), 6), t[2]): t[4] for t in (x.rstrip('\n').split('\t') for x in open(OUT + 'negate.tsv')
                                                         if not x.startswith(('#', 'source')))} if __name__ == '__main__' else {}


def main():
    import os
    R = read_theorets_sources()
    rows, conf, _ = convert_theorets(R)
    d, c = convert_dijon()
    rows.update(d)
    conf += c
    rows['16AlBoRoBo'], relab, held = relabel_16AlBoRoBo(rows['16AlBoRoBo'], conf)
    print('16AlBoRoBo QE: %d upper levels relabelled, %d held out' % (len(relab), len(held)))
    L = read_10LoBoLoRo()
    p2, c = convert_10LoBoLoRo_P2(L['P2'])
    p3, c3, nmatch = convert_10LoBoLoRo_P3(L['P3'], R, rows)
    rows['10LoBoLoRo'] = p2 + p3
    conf += c + c3
    h, c = convert_25BeBeReCa_hitran()
    conf += c
    # QO (user-approved 2026-10-28): a HITRAN-labelled row whose upper energy (GS + wn) is more than
    # 0.05 cm-1 from the authors' own lines on that label is dropped; agreeing ones are kept.
    # QAO (approved 2026-10-28): the same for hot-band HITRAN rows, at 0.01 cm-1; hot lower energies
    # are the mean GS + wn of every ground-state line reaching that level (input_base and converted).
    gs, own, low = gs_energies(), defaultdict(list), defaultdict(list)
    for line in open(OUT + 'input_base.txt'):
        t = line.rstrip('\r\n').split('\t')
        q = tuple(map(int, t[30:33]))
        if not t[0].startswith('-') and t[18:30] == ['0'] * 12 and q in gs:
            low[(tuple(map(int, t[3:15])), tuple(map(int, t[15:18])))].append(gs[q] + float(t[0]))
    for lst in rows.values():
        for wn, vu, qu, vl, ql, orig, note in lst:
            if sum(vl) == 0 and ql in gs:
                low[(vu, qu)].append(gs[ql] + wn)
    E_low = {k: sum(v) / len(v) for k, v in low.items()}
    E_low.update({((0,) * 12, q): e for q, e in gs.items()})
    for wn, vu, qu, vl, ql, orig, note in rows['25BeBeReCa']:
        if (vl, ql) in E_low:
            own[(vu, qu)].append(E_low[(vl, ql)] + wn)
    for row in h:
        wn, vu, qu, vl, ql = row[:5]
        e, hot = own.get((vu, qu)), sum(vl) > 0
        if e and (vl, ql) in E_low and abs(E_low[(vl, ql)] + wn - sum(e) / len(e)) > (0.01 if hot else 0.05):
            conf.append(('25BeBeReCa', wn, 'u', 'HITRAN row disagrees with own lines (%s, dropped)' % ('QAO' if hot else 'QO'),
                         '%s %s <- %s %s: E_up %.4f vs own %.4f' % (vu, qu, vl, ql, E_low[(vl, ql)] + wn, sum(e) / len(e))))
        else:
            rows['25BeBeReCa'].append(row)
    for paper in EXTRACTED:
        x, c = convert_extracted(paper)
        rows[paper] = [h[:7] for h in x]
        UNC_ROW.update({(paper, h[0]): h[7] for h in x})
        conf += c
    rows['18AsRa'], c = convert_18AsRa()
    conf += c
    hj, c = convert_26HjSiCaSi(theorets_reference(R).assign(), rows)
    rows['26HjSiCaSi'] = [h[:7] for h in hj]
    UNC_ROW.update({('26HjSiCaSi', h[0]): h[7] for h in hj})
    conf += c
    rows['24PeLeSuRu'], c = convert_24PeLeSuRu(R['24PeLeSuRu'], rows['26PeLeSuRu'])
    conf += c
    # QV (approved 2026-10-28): 24BeVaTuBo nu2+nu12 / 2nu10+nu12 lines whose upper energy (GS + wn)
    # differs by more than 0.02 cm-1 from 13LeTab or 25BeBeReCa on the same label are held out.
    ref = defaultdict(list)
    for t in ('13LeTab', '25BeBeReCa'):
        for wn, vu, qu, vl, ql, orig, note in rows[t]:
            if ql in gs and sum(vl) == 0:
                ref[(vu, qu)].append(gs[ql] + wn)
    keep24 = []
    for row in rows['24BeVaTuBo']:
        wn, vu, qu, vl, ql = row[:5]
        e = ref.get((vu, qu))
        if vu in (V(2, 12), (0,) * 9 + (2, 0, 1)) and e and ql in gs and abs(gs[ql] + wn - sum(e) / len(e)) > 0.02 \
                and (('24BeVaTuBo', round(wn, 6), ' '.join(str(x) for x in vu + qu)) not in NEGATE):
            conf.append(('24BeVaTuBo', wn, 'u', 'dyad line disagrees with 13LeTab/25BeBeReCa (QV, held out)',
                         '%s %s: E_up %.4f vs %.4f' % (vu, qu, gs[ql] + wn, sum(e) / len(e))))
        else:
            keep24.append(row)
    rows['24BeVaTuBo'] = keep24
    bad, c = cross_check(rows)
    conf += c
    dup = {}   # one level label from two (J, C, n): drop its rows, unless they are all one transition
    for x in conf:
        if x[3] == 'one label, two (J,C,n)':
            dup.setdefault(x[0], set()).add(x[4].split(' <- ')[0])
    for tag, labs in dup.items():
        # harmless when every exp line reaching one of the (J, C, n) also reaches the other
        use = defaultdict(lambda: defaultdict(set))
        for wn, vu, qu, vl, ql, orig, note in rows[tag]:
            ku, kl = orig.split(' <- ')
            for lab, k, other in (('%s %s' % (vu, qu), ku, (vl, ql)), ('%s %s' % (vl, ql), kl, (vu, qu))):
                if lab in labs:
                    use[lab][k].add((wn, other))
        dup[tag] = {lab for lab, ks in use.items() if len({frozenset(v) for v in ks.values()}) > 1}
    W = OUT
    os.makedirs(W, exist_ok=True)
    counts = {}
    hdr = ['wn', 'unc', 'unc'] + ['v%d_u' % i for i in range(1, 13)] + ['J_u', 'Ka_u', 'Kc_u'] + \
          ['v%d_l' % i for i in range(1, 13)] + ['J_l', 'Ka_l', 'Kc_l', 'tag', 'orig_label', 'note']
    base = defaultdict(list)    # lines a source already has in input_base.txt: keep those, number after
    for line in open(OUT + 'input_base.txt'):
        t = line.rstrip('\r\n').split('\t')
        tag, n = t[33].rsplit('.', 1)
        base[tag].append((abs(float(t[0])), t[3:33], int(re.sub(r'\D', '', n))))
    for tag, lst in sorted(rows.items()):
        n, w, seen = max([b[2] for b in base[tag]], default=0), open(W + tag + '.tsv', 'w'), set()
        w.write('\t'.join(hdr) + '\n')
        for i, (wn, vu, qu, vl, ql, orig, note) in enumerate(lst):
            if (tag, i) in bad or {'%s %s' % (vu, qu), '%s %s' % (vl, ql)} & dup.get(tag, set()) \
                    or (wn, vu, qu, vl, ql) in seen:     # one exp line given to identical components
                continue
            seen.add((wn, vu, qu, vl, ql))
            inb = [b for b in base[tag] if abs(b[0] - wn) <= 1e-4]
            if inb:
                if all(b[1] != [str(x) for x in vu + qu + vl + ql] for b in inb):
                    conf.append((tag, wn, 'u', 'label differs from input.txt (input.txt kept)',
                                 '%s %s <- %s %s vs input.txt %s' % (vu, qu, vl, ql, inb[0][1])))
                continue
            n += 1
            u = UNC_ROW.get((tag, wn), UNC.get(tag))
            u = '' if u is None else '%.3g' % u
            neg = NEGATE.get((tag, round(wn, 6), ' '.join(str(x) for x in vu + qu)))
            if neg:
                note = (note + '; ' if note else '') + 'NEGATED: ' + neg
            w.write('\t'.join([repr(-wn if neg else wn), u, u] + [str(x) for x in vu + qu + vl + ql] +
                               ['%s.%d' % (tag, n), orig, note]) + '\n')
        counts[tag] = (len(lst), n - max([b[2] for b in base[tag]], default=0))
    # Su's 25BeBeReCa.xlsx '381 Discrepancies': 156 pairs of rows with one label
    kept = defaultdict(list)
    for line in open(W + '25BeBeReCa.tsv'):
        t = line.split('\t')
        if t[0] != 'wn':
            kept[tuple(map(int, t[3:33]))].append(t[0])
    cols = 'C D E F G H I J K L M N O P Q R S T U V W X Y Z AA AB AC AD AE AF'.split()
    pairs = defaultdict(list)
    for d in xlsx_sheet(SRC + '25BeBeReCa/25BeBeReCa.xlsx', '381 Discrepancies')[1:]:
        pairs[tuple(int(d[c]) for c in cols)].append('%s %s' % (d['AG'], d['A']))
    for lab, v in pairs.items():
        conf.append(('25BeBeReCa', '', '', '381 Discrepancies pair (Su xlsx)', '%s %s <- %s %s: %s; now %s' % (
            lab[:12], lab[12:15], lab[15:27], lab[27:], ' / '.join(v),
            'one row, wn %s (Kc from C rule)' % kept[lab][0] if len(kept[lab]) == 1 else 'dropped (conflict)')))
    with open(W + 'conflicts.tsv', 'w') as w:
        w.write('source\twn\tside\tkind\tdetail\n')
        for x in conf:
            w.write('\t'.join(str(y) for y in x) + '\n')
    src_n = {t: len(v) for t, v in R.items()}
    src_n.update({'10LoBoLoRo': len(L['P2']) + len(L['P3']), '24BeVaTuBo': len(read_24BeVaTuBo()),
                  '16AlBoRoBo': sum(1 for x in open(SRC + '16AlBoRoBo/supmat_positions.txt', encoding='latin-1')
                                    if len(SYMFIX.sub(r'\1\2', x).split()) == 15 and x.lstrip().startswith('v')),
                  '18AsRa': sum(1 for x in open(OUT + '../csv/18AsRa_extract.tsv') if x.startswith('Table')),
                  **{x: sum(1 for _ in open(OUT + '../csv/%s_merged.csv' % x)) - 1 for x in EXTRACTED},
                  '26HjSiCaSi': sum(1 for x in open(OUT + '../csv/26HjSiCaSi_extract.tsv') if x[:4] in ('pump', 'vtyp'))})
    print('source\tlines\tconverted\twritten')
    for t, (a, b) in counts.items():
        print('%s\t%s\t%d\t%d' % (t, src_n.get(t, '?'), a, b))
    n3 = sum(r['wn'] >= 6030 for r in L['P3'])
    print('10LoBoLoRo P3: matched %d of %d in the recorded range (%.1f%% unmatched)' % (nmatch, n3, 100 - 100 * nmatch / n3))
    from collections import Counter
    for (t, k), v in sorted(Counter((x[0], x[3]) for x in conf).items()):
        print('conflict\t%s\t%s\t%d' % (t, k, v))


def selftest():
    for J in range(0, 40):
        for S in 'A B1 B2 B3'.split():
            gr = S + 'g'
            for N, (ka, kc) in enumerate(block_levels(J, gr), 1):
                assert _dijon_port(J, S, N) == (ka, kc), (J, S, N)
        assert sum(len(block_levels(J, g)) for g in ROT.values()) == 2 * J + 1
    assert mul('B1u', 'B3g') == 'B2u' and mul('A g', 'B2u') == 'B2u' and mul('B3u', 'B3u') == 'Ag'
    assert grot(1, 7) == 'B3g' and grot(1, 8) == 'B2g' and grot(0, 7) == 'B1g'
    assert rank_to_kakc(8, 'Ag', 2) == (2, 6) and rank_to_kakc(7, 'Ag', 1) == (2, 6)
    v = vibs('82.60146      0 0 0 0 0 0 0 0 0 0 0 0 A g    0 1 1 0 0 0 0 0 0 0 1 0 B1u    8 A g')
    assert v == [((0,) * 12, 'Ag'), ((0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0), 'B1u')], v
    v = vibs('0 0 0 0 1 0 0 0 0 1 0 2 0B1u \t0 0 0 0 0 0 0 0 0 0 0 0 0Ag  \t12Au')
    assert v[0] == ((0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 2), 'B1u') and v[1][1] == 'Ag', v
    v = vibs('224.428689     6           5              0 0 0 0 0 0 0 0 0 0 0 0 Ag   0 0 0 0 0 0 0 0 1 0 0 0 B3u')
    assert v == [((0,) * 12, 'Ag'), ((0,) * 8 + (1, 0, 0, 0), 'B3u')], v
    assert vib_sym(V(6, 10)) == 'B1u' and vib_sym(V(9, 10)) == 'Ag'
    assert allowed(V(6, 10), (28, 2, 26), (0,) * 12, (29, 2, 27)) and not allowed(V(9), (1, 0, 1), (0,) * 12, (0, 0, 0))
    print('c2h4_labels selftest ok')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest()
    else:
        main()
