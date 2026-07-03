import datetime

from scripts.lib import backtest as bt


def _k(closes, start="2026-01-01"):
    d0 = datetime.date.fromisoformat(start)
    return [{"date": (d0 + datetime.timedelta(days=i)).isoformat(), "close": c}
            for i, c in enumerate(closes)]


def test_forward_return():
    rows = _k([100, 101, 102, 110])  # index0=as_of, horizon3 → 110/100-1
    assert round(bt.forward_return(rows, "2026-01-01", 3), 3) == 0.10
    assert bt.forward_return(rows, "2026-01-01", 99) is None  # 不足


def test_weighted_score():
    s = bt.weighted_score({"chip": 1.0, "struct": 0.0, "fund": 0.0},
                          {"chip": 0.5, "struct": 0.3, "fund": 0.2})
    assert s == 0.5


def test_rank_ic_monotonic():
    pairs = [(1, 0.1), (2, 0.2), (3, 0.3), (4, 0.4)]
    assert round(bt.rank_ic(pairs), 3) == 1.0


def test_quintile_spread_positive_when_score_predicts():
    pairs = [(i, i / 10) for i in range(10)]  # 分數高→報酬高
    assert bt.quintile_spread(pairs) > 0


def test_grid_search_recovers_chip():
    # 合成：報酬完全由 chip 決定 → 最佳權重應偏 chip
    samples = [{"chip": c, "struct": 0.5, "fund": 0.5, "ret": c}
               for c in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]]
    out = bt.grid_search_weights(samples, step=0.5)
    assert out["best"]["w"]["chip"] >= out["best"]["w"]["struct"]


# ===== v2 方法論：per-date IC / t 值 / K-fold =====

def _samples_chip_predicts(dates, per_date=8):
    """合成：每個 as-of 日，chip 越高報酬越高（其他子分隨機無關）。"""
    import random
    random.seed(1)
    out = []
    for d in dates:
        for i in range(per_date):
            chip = i / (per_date - 1)
            out.append({"date": d, "chip": chip, "struct": random.random(),
                        "fund": random.random(), "ret": chip * 0.1 + random.uniform(-0.005, 0.005)})
    return out


def test_per_date_ic_groups_by_date():
    dates = ["2026-01-01", "2026-02-01", "2026-03-01"]
    s = _samples_chip_predicts(dates)
    w = {"chip": 1.0, "struct": 0.0, "fund": 0.0}
    ics = bt.per_date_ic(s, w)
    assert len(ics) == 3            # 每個日期一個 IC
    assert all(ic > 0.8 for ic in ics)  # chip 主導 → 每天高 IC


def test_ic_stats_tvalue():
    st = bt.ic_stats([0.2, 0.2, 0.2, 0.2])
    assert st["n"] == 4
    assert round(st["mean"], 3) == 0.2
    assert st["pos_frac"] == 1.0
    assert st["t"] is None or st["t"] > 0  # 零變異 t 無定義或極大


def test_grid_search_ic_prefers_chip():
    dates = [f"2026-{m:02d}-01" for m in range(1, 7)]
    s = _samples_chip_predicts(dates)
    out = bt.grid_search_ic(s, step=0.5)
    assert out["best"]["w"]["chip"] >= out["best"]["w"]["struct"]
    assert "mean_ic" in out["best"] and "t" in out["best"] and "pos_frac" in out["best"]


def test_fold_means_splits_dates():
    dates = [f"2026-{m:02d}-01" for m in range(1, 9)]  # 8 個日期
    s = _samples_chip_predicts(dates)
    w = {"chip": 1.0, "struct": 0.0, "fund": 0.0}
    fm = bt.fold_means(s, w, k=4)
    assert len(fm) == 4              # 4 折各一個平均 IC
    assert all(x > 0.8 for x in fm)  # chip 主導 → 每折都高


# ===== 分數校準（分數帶 → 歷史命中率/平均報酬）=====

def test_score_calibration_bands():
    # 分數越高報酬越好：低帶多負、高帶多正
    scored = [(30, -0.05), (35, -0.02), (50, 0.01), (60, 0.03),
              (75, 0.08), (80, 0.06), (90, 0.10)]
    bands = bt.score_calibration(scored, edges=[40, 55, 70])
    assert len(bands) == 4                      # 4 帶
    assert bands[0]["hi"] == 40 and bands[-1]["lo"] == 70
    lo_band = bands[0]
    hi_band = bands[-1]
    assert lo_band["hit_rate"] == 0.0           # <40 全負
    assert hi_band["hit_rate"] == 1.0           # ≥70 全正
    assert hi_band["avg_ret"] > lo_band["avg_ret"]
    assert hi_band["n"] == 3
