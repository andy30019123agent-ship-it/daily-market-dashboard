import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import scripts.accuracy as acc  # noqa: E402


def _day(date, tw_pct, tw_stance, us_pct, us_stance):
    return {
        "date": date,
        "overview": {
            "tw": {"featured": {"close": 100, "change_pct": tw_pct}},
            "us": [{"name": "標普 500", "change_pct": us_pct}],
        },
        "verdict": {
            "tw": {"stance": tw_stance},
            "us": {"stance": us_stance},
        },
    }


def _write_days(tmp_path, monkeypatch, days):
    monkeypatch.setattr(acc, "DATA_DIR", tmp_path)
    for d in days:
        (tmp_path / f"{d['date']}.json").write_text(json.dumps(d), encoding="utf-8")


def test_predicts_up_and_down_correctly(tmp_path, monkeypatch):
    # 注意：某天的 tw_pct/us_pct 是「拿來當下一天預測的比對基準（實際漲跌）」，
    # 該天自己的 stance 才是「對下一天的預測」——兩者互不相干，測試時要分開設。
    # day1(偏多，預測漲) 對照 day2 實際漲(2.0) -> hit
    # day2(偏空，預測跌) 對照 day3 實際漲(3.0) -> miss
    days = [
        _day("2026-06-18", 1.0, "偏多", 1.0, "偏多"),
        _day("2026-06-19", 2.0, "偏空", 2.0, "中性偏多"),
        _day("2026-06-22", 3.0, "偏多", 3.0, "偏空"),
    ]
    _write_days(tmp_path, monkeypatch, days)
    out = acc.build_accuracy()
    assert out["tw"]["total"] == 2
    assert out["tw"]["hit"] == 1  # day1 命中、day2 未命中
    assert out["tw"]["detail"][0]["hit"] is True
    assert out["tw"]["detail"][1]["hit"] is False


def test_neutral_stance_not_scored(tmp_path, monkeypatch):
    days = [
        _day("2026-06-18", 1.0, "中性", 1.0, "中性"),
        _day("2026-06-19", 1.0, "偏多", 1.0, "偏多"),
    ]
    _write_days(tmp_path, monkeypatch, days)
    out = acc.build_accuracy()
    assert out["tw"]["total"] == 0  # 唯一一天是中性，不計分
    assert out["us"]["total"] == 0


def test_last_day_has_no_next_to_compare(tmp_path, monkeypatch):
    days = [_day("2026-06-18", 1.0, "偏多", 1.0, "偏多")]
    _write_days(tmp_path, monkeypatch, days)
    out = acc.build_accuracy()
    assert out["tw"]["total"] == 0
    assert out["us"]["total"] == 0


def test_zero_pct_actual_not_scored(tmp_path, monkeypatch):
    days = [
        _day("2026-06-18", 1.0, "偏多", 1.0, "偏多"),
        _day("2026-06-19", 0.0, "偏多", 0.0, "偏多"),
    ]
    _write_days(tmp_path, monkeypatch, days)
    out = acc.build_accuracy()
    assert out["tw"]["total"] == 0  # 下一天實際漲跌恰為 0，方向不明不計分


# --- 市場紅綠燈成績單（regime，元件 A，2026-07-03 新增）---

def _regime_day(date, close, light=None):
    d = _day(date, 0.0, "中性", 0.0, "中性")  # tw/us stance 皆中性、不干擾既有 tw/us 計分
    d["overview"]["tw"]["featured"]["close"] = close
    if light is not None:
        d["regime"] = {"light": light, "score": 3 if light == "green" else -1}
    return d


def test_regime_green_hit_when_price_rises_after(tmp_path, monkeypatch):
    # day0 綠燈，5 個資料檔後(day5)指數比 day0 漲 -> 命中
    days = [_regime_day(f"2026-06-{18+i:02d}", 100, "green" if i == 0 else None) for i in range(6)]
    days[5]["overview"]["tw"]["featured"]["close"] = 110  # 上漲
    _write_days(tmp_path, monkeypatch, days)
    out = acc.build_accuracy()
    assert out["regime"]["total"] == 1
    assert out["regime"]["hit"] == 1
    assert out["regime"]["detail"][0]["light"] == "green"
    assert out["regime"]["detail"][0]["predicted"] == "up"


def test_regime_red_hit_when_price_falls_after(tmp_path, monkeypatch):
    days = [_regime_day(f"2026-06-{18+i:02d}", 100, "red" if i == 0 else None) for i in range(6)]
    days[5]["overview"]["tw"]["featured"]["close"] = 90  # 下跌
    _write_days(tmp_path, monkeypatch, days)
    out = acc.build_accuracy()
    assert out["regime"]["total"] == 1
    assert out["regime"]["hit"] == 1


def test_regime_red_miss_when_price_rises_after(tmp_path, monkeypatch):
    days = [_regime_day(f"2026-06-{18+i:02d}", 100, "red" if i == 0 else None) for i in range(6)]
    days[5]["overview"]["tw"]["featured"]["close"] = 110  # 紅燈卻上漲 -> 未命中
    _write_days(tmp_path, monkeypatch, days)
    out = acc.build_accuracy()
    assert out["regime"]["total"] == 1
    assert out["regime"]["hit"] == 0


def test_regime_yellow_not_scored(tmp_path, monkeypatch):
    days = [_regime_day(f"2026-06-{18+i:02d}", 100, "yellow" if i == 0 else None) for i in range(6)]
    days[5]["overview"]["tw"]["featured"]["close"] = 110
    _write_days(tmp_path, monkeypatch, days)
    out = acc.build_accuracy()
    assert out["regime"]["total"] == 0


def test_regime_missing_light_not_scored(tmp_path, monkeypatch):
    days = [_regime_day(f"2026-06-{18+i:02d}", 100) for i in range(6)]  # 全無 regime 欄
    _write_days(tmp_path, monkeypatch, days)
    out = acc.build_accuracy()
    assert out["regime"]["total"] == 0


def test_regime_not_enough_future_days_not_scored(tmp_path, monkeypatch):
    # 只有 3 天資料，不足 REGIME_WINDOW(5) 個之後的資料檔可比對
    days = [_regime_day(f"2026-06-{18+i:02d}", 100, "green" if i == 0 else None) for i in range(3)]
    _write_days(tmp_path, monkeypatch, days)
    out = acc.build_accuracy()
    assert out["regime"]["total"] == 0
    assert out["regime"]["window_days"] == 5


def test_rate_and_recent30(tmp_path, monkeypatch):
    # day1(偏多) 對照 day2 實際漲(1.0) -> hit；day2(偏多) 對照 day3 實際漲(2.0) -> hit
    days = [
        _day("2026-06-18", 0.0, "偏多", 0.0, "偏多"),
        _day("2026-06-19", 1.0, "偏多", 1.0, "偏多"),
        _day("2026-06-22", 2.0, "偏空", 2.0, "偏空"),
    ]
    _write_days(tmp_path, monkeypatch, days)
    out = acc.build_accuracy()
    assert out["tw"]["hit_rate"] == 100.0
    assert out["tw"]["recent30_total"] == 2
    assert out["us"]["index_used"] == "標普 500"
