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


def per_date_ic(samples, w):
    """對每個 as-of 日各自算一次橫斷面排序 IC（分數 vs 未來報酬）。
    回傳有效日期的 IC 清單（每日 ≥3 檔才計）。這是處理『樣本不獨立』的正確做法。"""
    by_date = {}
    for s in samples:
        if s.get("ret") is None:
            continue
        by_date.setdefault(s["date"], []).append(
            (weighted_score(s, w), s["ret"]))
    ics = []
    for d in sorted(by_date):
        ic = rank_ic(by_date[d])
        if ic is not None:
            ics.append(ic)
    return ics


def ic_stats(ics):
    """IC 時間序列的統計：平均、標準差、t 值（mean/std×√n）、為正比例。"""
    ics = [x for x in ics if x is not None]
    n = len(ics)
    if n == 0:
        return {"n": 0, "mean": None, "std": None, "t": None, "pos_frac": None}
    mean = sum(ics) / n
    var = sum((x - mean) ** 2 for x in ics) / (n - 1) if n > 1 else 0.0
    std = var ** 0.5
    t = round(mean / std * (n ** 0.5), 3) if std > 0 else None
    return {"n": n, "mean": round(mean, 4), "std": round(std, 4), "t": t,
            "pos_frac": round(sum(1 for x in ics if x > 0) / n, 3)}


def grid_search_ic(samples, step=0.1):
    """以『每日 IC 平均』為主指標搜尋權重（比 pooled 更誠實）。依平均 IC 由高到低。"""
    results = []
    for w in _weight_grid(step):
        st = ic_stats(per_date_ic(samples, w))
        if st["mean"] is None:
            continue
        results.append({"w": w, "mean_ic": st["mean"], "t": st["t"],
                        "pos_frac": st["pos_frac"], "n_dates": st["n"]})
    results.sort(key=lambda x: x["mean_ic"], reverse=True)
    return {"best": results[0] if results else None, "top": results[:10],
            "n_samples": len(samples)}


def fold_means(samples, w, k=4):
    """把 as-of 日期切成 k 段（時間連續），各段的每日 IC 平均——用來看穩定度。"""
    dates = sorted({s["date"] for s in samples})
    if not dates:
        return []
    size = max(1, len(dates) // k)
    out = []
    for i in range(0, len(dates), size):
        chunk = set(dates[i:i + size])
        sub = [s for s in samples if s["date"] in chunk]
        st = ic_stats(per_date_ic(sub, w))
        if st["mean"] is not None:
            out.append(st["mean"])
    return out[:k] if len(out) > k else out


def score_calibration(scored, edges):
    """分數帶校準：scored=[(分數0~100, 未來報酬)]，edges=分帶界（如 [40,55,70]）。
    回每帶 {lo, hi, n, hit_rate(報酬>0比例), avg_ret}。把抽象分數變成『歷史命中率』。"""
    bounds = [0] + list(edges) + [100]
    bands = []
    for i in range(len(bounds) - 1):
        lo, hi = bounds[i], bounds[i + 1]
        top = (i == len(bounds) - 2)
        rets = [r for sc, r in scored
                if r is not None and (lo <= sc <= hi if top else lo <= sc < hi)]
        n = len(rets)
        bands.append({
            "lo": lo, "hi": hi, "n": n,
            "hit_rate": round(sum(1 for r in rets if r > 0) / n, 3) if n else None,
            "avg_ret": round(sum(rets) / n, 4) if n else None,
        })
    return bands


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
