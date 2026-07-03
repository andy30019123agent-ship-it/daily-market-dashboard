"""回測純函式：報酬、排序 IC、五分位差、加權分、權重網格搜尋。不碰網路。"""
from __future__ import annotations


def forward_return(rows, as_of, horizon):
    """as_of（含）當根往後第 horizon 根的 close / as_of 根 close − 1；不足回 None。"""
    rows = [r for r in rows if r.get("close") is not None]
    idx = next((i for i, r in enumerate(rows) if r["date"] >= as_of), None)
    if idx is None or idx + horizon >= len(rows):
        return None
    base = rows[idx]["close"]
    fut = rows[idx + horizon]["close"]
    return (fut / base - 1) if base else None


def weighted_score(sub, w):
    return sum((sub.get(k) or 0) * w.get(k, 0) for k in ("chip", "struct", "fund"))


def _rank(xs):
    """平均秩（tie 取平均），供 Spearman 用。"""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def rank_ic(pairs):
    """Spearman 排序相關（分數 vs 報酬）；<3 筆或無變異回 None。"""
    pairs = [(s, r) for s, r in pairs if s is not None and r is not None]
    n = len(pairs)
    if n < 3:
        return None
    rs = _rank([p[0] for p in pairs])
    rr = _rank([p[1] for p in pairs])
    ms, mr = sum(rs) / n, sum(rr) / n
    num = sum((rs[i] - ms) * (rr[i] - mr) for i in range(n))
    den = (sum((x - ms) ** 2 for x in rs) * sum((x - mr) ** 2 for x in rr)) ** 0.5
    return round(num / den, 4) if den else None


def quintile_spread(pairs):
    """高分五分之一平均報酬 − 低分五分之一平均報酬；<5 筆回 None。"""
    pairs = sorted([(s, r) for s, r in pairs if s is not None and r is not None])
    n = len(pairs)
    if n < 5:
        return None
    q = max(1, n // 5)
    low = sum(r for _, r in pairs[:q]) / q
    high = sum(r for _, r in pairs[-q:]) / q
    return round(high - low, 4)


def _weight_grid(step):
    """列舉 chip+struct+fund=1 的網格點。"""
    out = []
    n = round(1 / step)
    for a in range(n + 1):
        for b in range(n - a + 1):
            c = n - a - b
            out.append({"chip": round(a * step, 4), "struct": round(b * step, 4),
                        "fund": round(c * step, 4)})
    return out


def grid_search_weights(samples, step=0.1):
    """對權重網格算 IC/五分位差，依 IC 由高到低。samples=[{chip,struct,fund,ret}]。"""
    results = []
    for w in _weight_grid(step):
        pairs = [(weighted_score(s, w), s["ret"]) for s in samples if s.get("ret") is not None]
        ic = rank_ic(pairs)
        if ic is None:
            continue
        results.append({"w": w, "ic": ic, "spread": quintile_spread(pairs)})
    results.sort(key=lambda x: x["ic"], reverse=True)
    return {"best": results[0] if results else None, "top": results[:10],
            "n_samples": len(samples)}
