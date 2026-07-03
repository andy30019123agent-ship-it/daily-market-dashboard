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
