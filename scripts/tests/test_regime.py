import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts import regime as rg  # noqa: E402


# --- score_trend ---

def test_trend_all_bullish_scores_3():
    # 60 天遞增序列：收盤(最新)最大，故 close>ma20>ma60 全成立
    closes = [100 + i for i in range(60)]
    out = rg.score_trend(closes)
    assert out["score"] == 3
    assert out["missing"] is False


def test_trend_all_bearish_scores_0():
    # 60 天遞減序列：最新收盤最小 -> 三分項全不成立
    closes = [200 - i for i in range(60)]
    out = rg.score_trend(closes)
    assert out["score"] == 0


def test_trend_missing_when_not_enough_history():
    out = rg.score_trend([100] * 30)  # 不足 60 天 -> MA60 算不出來
    assert out["missing"] is True
    assert out["score"] == 0


def test_trend_missing_when_empty():
    out = rg.score_trend([])
    assert out["missing"] is True
    assert out["score"] == 0


# --- score_breadth ---

def test_breadth_bull_above_55_pct():
    out = rg.score_breadth({"up": 560, "down": 440})  # 56% > 55%
    assert out["score"] == 1
    assert out["missing"] is False


def test_breadth_bear_below_45_pct():
    out = rg.score_breadth({"up": 440, "down": 560})  # 44% < 45%
    assert out["score"] == -1


def test_breadth_neutral_between_thresholds():
    out = rg.score_breadth({"up": 500, "down": 500})  # 50%，介於門檻間
    assert out["score"] == 0
    assert out["missing"] is False


def test_breadth_exact_boundary_not_counted():
    # 55% 剛好等於門檻，規則是「> 55%」不含等於 -> 不加分
    out = rg.score_breadth({"up": 55, "down": 45})
    assert out["score"] == 0


def test_breadth_missing_when_absent():
    out = rg.score_breadth(None)
    assert out["missing"] is True
    assert out["score"] == 0


# --- score_vix ---

def test_vix_bull_below_20():
    assert rg.score_vix({"value": 19.9})["score"] == 1


def test_vix_bear_above_28():
    assert rg.score_vix({"value": 28.1})["score"] == -1


def test_vix_neutral_between():
    assert rg.score_vix({"value": 24})["score"] == 0


def test_vix_boundary_values_not_counted():
    assert rg.score_vix({"value": 20})["score"] == 0   # 剛好 20，不算 <20
    assert rg.score_vix({"value": 28})["score"] == 0   # 剛好 28，不算 >28


def test_vix_missing_when_absent():
    out = rg.score_vix(None)
    assert out["missing"] is True


# --- net_yi_sum / aggregate_recent_chips / score_chips ---

def test_net_yi_sum_combines_three():
    assert rg.net_yi_sum({"外資": 10, "投信": -2, "自營": 1}) == 9


def test_net_yi_sum_none_when_no_entry():
    assert rg.net_yi_sum(None) is None
    assert rg.net_yi_sum({}) is None


def test_aggregate_recent_chips_sums_available_days():
    entries = [{"外資": 1, "投信": 1, "自營": 1}, None, {"外資": 2, "投信": 0, "自營": 0}]
    net, days_used = rg.aggregate_recent_chips(entries, n=5)
    assert net == 5.0
    assert days_used == 2  # 只有 2 天有資料


def test_aggregate_recent_chips_none_when_no_data():
    net, days_used = rg.aggregate_recent_chips([None, None], n=5)
    assert net is None
    assert days_used == 0


def test_score_chips_positive_net_scores_1():
    assert rg.score_chips([{"外資": 5, "投信": 0, "自營": 0}])["score"] == 1


def test_score_chips_negative_net_scores_neg1():
    assert rg.score_chips([{"外資": -5, "投信": 0, "自營": 0}])["score"] == -1


def test_score_chips_missing_when_no_data():
    out = rg.score_chips([None, None])
    assert out["missing"] is True
    assert out["score"] == 0


# --- compute_regime（整合，含燈號分級門檻）---

def _bull_closes():
    return [100 + i for i in range(60)]


def test_compute_regime_green_when_score_ge_3():
    out = rg.compute_regime(
        _bull_closes(), {"up": 560, "down": 440}, {"value": 15},
        [{"外資": 1, "投信": 0, "自營": 0}],
    )
    assert out["score"] >= 3
    assert out["light"] == "green"


def test_compute_regime_red_when_score_negative():
    bear_closes = [200 - i for i in range(60)]
    out = rg.compute_regime(
        bear_closes, {"up": 440, "down": 560}, {"value": 30},
        [{"外資": -1, "投信": 0, "自營": 0}],
    )
    assert out["score"] < 0
    assert out["light"] == "red"


def test_compute_regime_yellow_when_score_0_to_2():
    # 趨勢全空(0)、寬度中性(0)、波動中性(0)、籌碼正(+1) -> 總分 1，落在 0~2 黃燈區間
    bear_closes = [200 - i for i in range(60)]
    out = rg.compute_regime(
        bear_closes, {"up": 500, "down": 500}, {"value": 24},
        [{"外資": 1, "投信": 0, "自營": 0}],
    )
    assert out["score"] == 1
    assert out["light"] == "yellow"


def test_compute_regime_all_missing_does_not_raise():
    out = rg.compute_regime([], None, None, [])
    assert out["score"] == 0
    assert out["light"] == "yellow"  # 0~2 區間
    for comp in out["components"].values():
        assert comp["missing"] is True


def test_compute_regime_components_shape():
    out = rg.compute_regime(_bull_closes(), {"up": 1, "down": 1}, {"value": 24}, [])
    assert set(out["components"].keys()) == {"trend", "breadth", "vix", "chips"}
    assert out["light"] in ("green", "yellow", "red")
