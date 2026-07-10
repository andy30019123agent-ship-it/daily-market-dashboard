import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.lib.flows import inst_flow_streaks, buy_concentration, volume_anomalies  # noqa: E402


def test_streak_basic_directions():
    nets = [
        {"外資": -10, "投信": 5, "自營": 1},
        {"外資": -20, "投信": 8, "自營": -1},
        {"外資": -30, "投信": 12, "自營": -2},
    ]
    out = inst_flow_streaks(nets)
    assert out["外資"] == {"streak": 3, "side": "sell", "today_yi": -30}
    assert out["投信"] == {"streak": 3, "side": "buy", "today_yi": 12}
    # 自營最近兩天賣、更早一天買 → 只算最近的連 2 賣
    assert out["自營"] == {"streak": 2, "side": "sell", "today_yi": -2}


def test_streak_breaks_on_zero_and_missing():
    nets = [
        {"外資": 5},
        {"外資": 0},          # 0 中斷
        {"外資": 3},
        {"外資": 4},
    ]
    out = inst_flow_streaks(nets)
    assert out["外資"]["streak"] == 2 and out["外資"]["side"] == "buy"
    # 投信整段缺值 → streak 0、side None
    assert out["投信"] == {"streak": 0, "side": None, "today_yi": None}


def test_streak_empty():
    out = inst_flow_streaks([])
    assert out["外資"] == {"streak": 0, "side": None, "today_yi": None}


def test_buy_concentration():
    # 買超：100,50,30,20（合計 200），賣超與 0 不計
    stocks = [
        {"inst_net_yi": 100}, {"inst_net_yi": 50}, {"inst_net_yi": 30},
        {"inst_net_yi": 20}, {"inst_net_yi": -40}, {"inst_net_yi": 0},
    ]
    out = buy_concentration(stocks, top_n=2)
    assert out == {"top_yi": 150.0, "total_yi": 200.0, "ratio": 75, "n": 2}


def test_buy_concentration_none_when_no_buys():
    assert buy_concentration([{"inst_net_yi": -5}, {"inst_net_yi": 0}]) is None
    assert buy_concentration([]) is None


def test_volume_anomalies_flags_and_direction():
    today = [
        {"code": "2330", "name": "台積電", "value_yi": 300, "pct": 3.0},   # 均值100→3x, 漲
        {"code": "2317", "name": "鴻海", "value_yi": 250, "pct": -2.0},    # 均值100→2.5x, 跌
        {"code": "1101", "name": "台泥", "value_yi": 120, "pct": 1.0},     # 均值100→1.2x, 未達門檻
        {"code": "9999", "name": "新股", "value_yi": 500, "pct": 5.0},     # 無歷史→不計
        {"code": "0050", "name": "ETF", "value_yi": 1, "pct": 1.0},        # 成交值過低→濾
    ]
    hist = {
        "2330": [100, 100, 100],
        "2317": [100, 100, 100, 100],
        "1101": [100, 100, 100],
        "9999": [],
    }
    out = volume_anomalies(today, hist, min_ratio=2.0, min_days=3, min_value_yi=2.0)
    codes = [s["code"] for s in out]
    assert codes == ["2330", "2317"]           # 依 ratio 由高到低
    assert out[0]["ratio"] == 3.0 and out[0]["direction"] == "up"
    assert out[1]["direction"] == "down"


def test_volume_anomalies_empty():
    assert volume_anomalies([], {}) == []
