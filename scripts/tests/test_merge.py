import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.merge_day import merge_day, update_index  # noqa: E402
from scripts.lib.schema import validate_day  # noqa: E402


def _partial():
    return {
        "overview": {
            "tw": {"featured": {"name": "加權", "close": 1, "change": 1, "change_pct": 1, "spark": [1]},
                   "stats": [{"name": "成交金額", "value": "100 億"}]},
            "us": [{"name": "標普 500", "close": 5000, "change_pct": 0.2}],
            "vix": {"tw": None, "us": {"value": 14.2, "change": -0.5, "gauge": 0.3}},
        },
        "hot_stocks": {"tw": [{"code": "2330", "name": "台積電", "change_pct": 2.1, "reason": ""}], "us": []},
        "_meta": {"fetched_at": "2026-06-18"},
    }


def _soft():
    return {
        "tw_stats": [{"name": "成交金額", "value": "100 億"}, {"name": "外資買賣超", "value": "+128 億", "dir": "up"}],
        "us_sox": {"name": "費城半導體", "close": 5602, "change_pct": 1.34},
        "vix_us": {"state": "低波動", "note": "情緒平穩"},
        "vix_tw": {"value": 18.5, "change": -0.8, "state": "波動偏低", "note": "平穩", "gauge": 0.26},
        "hot_tw_reasons": {"2330": "外資買超"},
        "sectors": {"tw": {"in": [], "out": []}, "us": {"in": [], "out": []}},
        "hot_us": [],
        "news": [{"tag": "pos", "title": "x", "impact": "y", "source_name": "路透", "source_url": "https://r.com"}],
        "upcoming_events": [], "past_events_review": [],
        "verdict": {"bullish": ["a"], "bearish": ["b"], "risks": ["c"]},
        "summary": "測試摘要",
    }


def test_merge_produces_valid_day():
    day = merge_day(_partial(), _soft(), "2026-06-18", "2026-06-18 18:43")
    assert validate_day(day) == []


def test_merge_fills_sox_and_reasons():
    day = merge_day(_partial(), _soft(), "2026-06-18")
    assert any(u["name"] == "費城半導體" for u in day["overview"]["us"])
    assert day["hot_stocks"]["tw"][0]["reason"] == "外資買超"
    assert day["overview"]["vix"]["us"]["value"] == 14.2  # 硬數據數值保留
    assert day["overview"]["vix"]["us"]["state"] == "低波動"  # 軟情報文字併入


def test_update_index_dedup(tmp_path, monkeypatch):
    idx = tmp_path / "index.json"
    idx.write_text('{"dates":["2026-06-18"]}')
    monkeypatch.setattr("scripts.merge_day.INDEX_PATH", idx)
    update_index("2026-06-18")
    update_index("2026-06-19")
    dates = json.loads(idx.read_text())["dates"]
    assert dates.count("2026-06-18") == 1 and "2026-06-19" in dates
