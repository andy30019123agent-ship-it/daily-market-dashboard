import io
import json as _json

from scripts.lib import potential


def _radar(stocks):
    return {"stocks": stocks}


# --- Task 1: aggregate_chips ---
def test_aggregate_chips_sums_inst_and_takes_latest_meta():
    days = [
        _radar([{"code": "1111", "name": "舊名", "pct": -1.0, "inst_net_yi": 0.5,
                 "value_yi": 3.0, "sector": "塑膠"}]),
        _radar([{"code": "1111", "name": "新名", "pct": 0.8, "inst_net_yi": 1.2,
                 "value_yi": 4.0, "sector": "塑膠"}]),
    ]
    agg = potential.aggregate_chips(days, window=5)
    assert agg["1111"]["inst_net_yi"] == 1.7
    assert agg["1111"]["name"] == "新名"
    assert agg["1111"]["pct"] == 0.8


# --- Task 2: pick_accumulators ---
def test_pick_accumulators_filters_and_ranks():
    agg = {
        "A": {"code": "A", "inst_net_yi": 5.0, "pct": 0.5},
        "B": {"code": "B", "inst_net_yi": 0.3, "pct": 0.5},
        "C": {"code": "C", "inst_net_yi": 9.0, "pct": 6.0},
        "D": {"code": "D", "inst_net_yi": 2.0, "pct": -1.0},
    }
    out = potential.pick_accumulators(agg, inst_min_yi=1.0, pct_max=3.0, cand_max=10)
    assert [s["code"] for s in out] == ["A", "D"]


# --- Task 3: low_base_metrics ---
def test_low_base_metrics_basic():
    rows = []
    for i in range(200):
        c = 100 - i * 0.25
        rows.append({"date": f"2025-{(i % 12) + 1:02d}-01", "close": c,
                     "max": c + 1, "min": c - 1})
    rows[-1]["close"] = 55.0
    m = potential.low_base_metrics(rows)
    assert m is not None
    assert 0.0 <= m["price_pos"] <= 0.4
    assert m["chg_6m"] < 0


def test_low_base_metrics_insufficient():
    assert potential.low_base_metrics([{"date": "2025-01-01", "close": 10,
                                        "max": 10, "min": 10}]) is None


# --- Task 4: finmind_history ---
def test_finmind_history_parses(monkeypatch):
    payload = {"data": [{"date": "2025-01-02", "open": 1, "max": 2,
                         "min": 0.5, "close": 1.5}]}

    class _Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(url, timeout=0):
        return _Resp(_json.dumps(payload).encode())

    monkeypatch.setattr(potential.urllib.request, "urlopen", fake_urlopen)
    rows = potential.finmind_history("1234", "2024-07-01")
    assert rows and rows[0]["close"] == 1.5


def test_finmind_history_tolerates_error(monkeypatch):
    def boom(url, timeout=0):
        raise OSError("quota")

    monkeypatch.setattr(potential.urllib.request, "urlopen", boom)
    assert potential.finmind_history("1234", "2024-07-01") == []


# --- Task 5: filter_low_base ---
def test_filter_low_base_keeps_only_low_base():
    cands = [{"code": "LOW", "inst_net_yi": 3.0},
             {"code": "HIGH", "inst_net_yi": 2.0},
             {"code": "MISS", "inst_net_yi": 1.0}]

    def fake_fetch(code, start):
        if code == "LOW":
            return [{"date": "2024-07-01", "close": 100, "max": 100, "min": 30}] + \
                   [{"date": f"2025-{(i % 12) + 1:02d}-15", "close": 40,
                     "max": 41, "min": 39} for i in range(30)]
        if code == "HIGH":
            return [{"date": f"2025-{(i % 12) + 1:02d}-15", "close": 95,
                     "max": 100, "min": 30} for i in range(30)]
        return []

    out = potential.filter_low_base(cands, "2024-07-01", pos_max=0.4,
                                    chg6m_max=0.15, fetch=fake_fetch, sleep_s=0)
    codes = [s["code"] for s in out]
    assert "LOW" in codes and "HIGH" not in codes and "MISS" not in codes
    low = next(s for s in out if s["code"] == "LOW")
    assert low["history"] == "ok" and "price_pos" in low


# --- Task 6: build_potential ---
def test_build_potential_end_to_end():
    days = [{"stocks": [
        {"code": "LOW", "name": "低基", "pct": 0.5, "inst_net_yi": 3.0,
         "value_yi": 5.0, "sector": "電機"},
        {"code": "HOT", "name": "熱門", "pct": 8.0, "inst_net_yi": 9.0,
         "value_yi": 5.0, "sector": "半導體"},
    ]}]

    def fake_fetch(code, start):
        # 由舊到新：先一筆去年高點，再一串今年低檔（收在區間下緣、半年下跌）
        return [{"date": "2024-07-01", "close": 100, "max": 100, "min": 30}] + \
               [{"date": f"2025-{(i % 12) + 1:02d}-15", "close": 40, "max": 41,
                 "min": 39} for i in range(30)]

    out = potential.build_potential(days, "2024-07-01", fetch=fake_fetch, sleep_s=0)
    assert out["window_days"] == potential.DEFAULTS["window"]
    codes = [s["code"] for s in out["stocks"]]
    assert "LOW" in codes and "HOT" not in codes


# ===== Phase A（2026-07-04 升級）=====

# --- Task 1: aggregate_chips buy_days ---
def test_aggregate_chips_counts_buy_days():
    days = [
        _radar([{"code": "2603", "name": "長榮", "pct": -1.0, "inst_net_yi": 0.5,
                 "value_yi": 3.0, "sector": "航運"}]),
        _radar([{"code": "2603", "name": "長榮", "pct": 0.0, "inst_net_yi": -0.2,
                 "value_yi": 3.0, "sector": "航運"}]),
        _radar([{"code": "2603", "name": "長榮", "pct": 0.3, "inst_net_yi": 1.1,
                 "value_yi": 4.0, "sector": "航運"}]),
    ]
    agg = potential.aggregate_chips(days, window=5)
    assert agg["2603"]["buy_days"] == 2  # 第1、3天買超


# --- Task 2: low_base_metrics 量能/季線/縮圖 ---
def test_low_base_metrics_adds_vol_ma_spark():
    rows = []
    for i in range(120):
        rows.append({"date": f"2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}",
                     "close": 100 + i * 0.1, "max": 101 + i * 0.1,
                     "min": 99 + i * 0.1,
                     "Trading_Volume": 1000 + (500 if i >= 115 else 0)})
    m = potential.low_base_metrics(rows)
    assert m["vol_ratio"] > 1.0          # 最後5天爆量
    assert m["above_ma60"] is True       # 緩漲、收盤在季線上
    assert 2 <= len(m["spark"]) <= 52
    assert m["spark"][-1] == rows[-1]["close"]


# --- Task 3: 籌碼分 / 價量結構分 ---
def test_chip_score_rewards_amount_and_persistence():
    strong = potential.chip_score({"inst_net_yi": 5.0, "buy_days": 5}, window=5)
    weak = potential.chip_score({"inst_net_yi": 0.3, "buy_days": 1}, window=5)
    assert strong > weak
    assert 0.0 <= weak <= strong <= 1.0


def test_structure_score_pushes_down_falling_stock():
    ready = potential.structure_score({"price_pos": 0.15, "vol_ratio": 1.8, "above_ma60": True})
    laggard = potential.structure_score({"price_pos": 0.15, "vol_ratio": 0.8, "above_ma60": False})
    assert ready > laggard
    assert 0.0 <= laggard <= ready <= 1.0
