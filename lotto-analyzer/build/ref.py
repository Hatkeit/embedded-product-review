"""Python mirror of LottoAnalyzer.AnalyzeCore, used to cross-check the VBA output.

Every arithmetic step follows the VBA code in the same order so the results
(including tie-breaking) match exactly.
"""
import math

HEAP_SIZE = 20000
SUM_WIN = 7
LOW_MAX = 22
SUM_TOP = 300


def features(t):
    """t sorted -> (sum, odd, low, consecutive pairs, distinct last digits, max per section, AC)."""
    s = sum(t)
    odd = sum(x % 2 for x in t)
    low = sum(1 for x in t if x <= LOW_MAX)
    con = sum(1 for k in range(1, 6) if t[k] == t[k - 1] + 1)
    dig = len({x % 10 for x in t})
    sec = [0] * 5
    mx = 0
    for x in t:
        sec[x // 10] += 1
        mx = max(mx, sec[x // 10])
    diffs = {t[j] - t[k] for k in range(6) for j in range(k + 1, 6)}
    return s, odd, low, con, dig, mx, len(diffs) - 5


def code_of(t):
    cd = 0.0
    for x in t:
        cd = cd * 64 + x
    return cd


def decode(cd):
    t = [0] * 6
    for k in range(5, -1, -1):
        q = math.floor(cd / 64)
        t[k] = int(cd - q * 64)
        cd = q
    return t


class Heap:
    def __init__(self):
        self.s = [0.0] * (HEAP_SIZE + 1)
        self.c = [0.0] * (HEAP_SIZE + 1)
        self.n = 0

    def push(self, sc, cd):
        self.n += 1
        i = self.n
        while i > 1:
            p = i // 2
            if self.s[p] <= sc:
                break
            self.s[i] = self.s[p]
            self.c[i] = self.c[p]
            i = p
        self.s[i] = sc
        self.c[i] = cd

    def replace_top(self, sc, cd):
        i = 1
        while True:
            l = 2 * i
            if l > self.n:
                break
            if l < self.n and self.s[l + 1] < self.s[l]:
                l += 1
            if self.s[l] >= sc:
                break
            self.s[i] = self.s[l]
            self.c[i] = self.c[l]
            i = l
        self.s[i] = sc
        self.c[i] = cd


def analyze(draws, n_pick=10, max_ov=3, n_recent=50, excl=True, w=None, n_max=45):
    """draws: list of sorted 6-number lists, oldest first."""
    w = w or [1.0] * 10
    nd = len(draws)
    n_recent = min(n_recent, nd)
    c_num = [0] * 46
    c_rec = [0] * 46
    c_sum = [0] * (SUM_TOP + 1)
    c_odd = [0] * 7
    c_low = [0] * 7
    c_con = [0] * 6
    c_dig = [0] * 7
    c_sec = [0] * 7
    c_prv = [0] * 7
    c_ac = [0] * 11
    for i, t in enumerate(draws, 1):
        for x in t:
            c_num[x] += 1
            if i > nd - n_recent:
                c_rec[x] += 1
        f = features(t)
        c_sum[f[0]] += 1
        c_odd[f[1]] += 1
        c_low[f[2]] += 1
        c_con[f[3]] += 1
        c_dig[f[4]] += 1
        c_sec[f[5]] += 1
        c_ac[f[6]] += 1
        if i > 1:
            c_prv[len(set(t) & set(draws[i - 2]))] += 1

    L = math.log
    t_num = [0.0] * 46
    for i in range(1, 46):
        t_num[i] = w[0] * L((c_num[i] + 1) / (6.0 * nd + 45.0) * 45.0) + \
            w[1] * L((c_rec[i] + 1) / (6.0 * n_recent + 45.0) * 45.0)
    t_sum = [0.0] * (SUM_TOP + 1)
    for s in range(SUM_TOP + 1):
        cw = sum(c_sum[j] for j in range(s - SUM_WIN, s + SUM_WIN + 1) if 0 <= j <= SUM_TOP)
        t_sum[s] = w[2] * L((cw + 1) / ((2 * SUM_WIN + 1) * float(nd) + 235.0))
    t_odd = [w[3] * L((c_odd[i] + 1) / (nd + 7.0)) for i in range(7)]
    t_low = [w[4] * L((c_low[i] + 1) / (nd + 7.0)) for i in range(7)]
    t_prv = [w[8] * L((c_prv[i] + 1) / (nd - 1 + 7.0)) for i in range(7)]
    t_con = [w[5] * L((c_con[i] + 1) / (nd + 6.0)) for i in range(6)]
    t_dig = [0.0] + [w[6] * L((c_dig[i] + 1) / (nd + 6.0)) for i in range(1, 7)]
    t_sec = [0.0] + [w[7] * L((c_sec[i] + 1) / (nd + 6.0)) for i in range(1, 7)]
    t_ac = [w[9] * L((c_ac[i] + 1) / (nd + 11.0)) for i in range(11)]

    prev = set(draws[-1])
    pc = [bin(i).count("1") for i in range(1024)]
    h = Heap()
    M = n_max
    for a in range(1, M - 4):
        for b in range(a + 1, M - 3):
            for c in range(b + 1, M - 2):
                for d in range(c + 1, M - 1):
                    for e in range(d + 1, M):
                        z5 = t_num[a] + t_num[b] + t_num[c] + t_num[d] + t_num[e]
                        for f in range(e + 1, M + 1):
                            t = (a, b, c, d, e, f)
                            s, odd, low, con, dig, mx, _ = features(t)
                            prv = sum(1 for x in t if x in prev)
                            sc = z5 + t_num[f] + t_sum[s] + t_odd[odd] + t_low[low] \
                                + t_con[con] + t_dig[dig] + t_sec[mx] + t_prv[prv]
                            if h.n < HEAP_SIZE:
                                h.push(sc, code_of(t))
                            elif sc > h.s[1]:
                                h.replace_top(sc, code_of(t))

    tot = {}
    entries = []
    for i in range(1, h.n + 1):
        t = decode(h.c[i])
        total = h.s[i] + t_ac[features(t)[6]]
        entries.append((total, h.c[i]))
    entries.sort(key=lambda x: (-x[0], x[1]))
    past = {code_of(t) for t in draws}
    picked = []
    for total, cd in entries:
        if len(picked) >= n_pick:
            break
        if excl and cd in past:
            continue
        t = decode(cd)
        if all(len(set(t) & set(p[0])) <= max_ov for p in picked):
            picked.append((t, total))
    return picked
