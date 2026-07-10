import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.lib.flows import inst_flow_streaks, buy_concentration  # noqa: E402


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
