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
