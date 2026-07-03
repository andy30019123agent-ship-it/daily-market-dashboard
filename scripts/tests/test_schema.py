import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.lib.schema import validate_day  # noqa: E402


def test_fixture_passes_schema():
    data = json.loads((ROOT / "public/data/2026-06-18.json").read_text(encoding="utf-8"))
    assert validate_day(data) == []


def test_missing_key_reported():
    errs = validate_day({"date": "2026-06-18"})
    assert any("overview" in e for e in errs)


def test_news_requires_source_url():
    data = {
        "date": "2026-06-18", "updated_at": "x",
        "overview": {"tw": {"featured": {}, "stats": []}, "us": [], "vix": {"tw": {}, "us": {}}},
        "sectors": {"tw": {"in": [], "out": []}, "us": {"in": [], "out": []}},
        "hot_stocks": {"tw": [], "us": []},
        "news": [{"title": "無來源新聞"}],
        "upcoming_events": [], "past_events_review": [],
        "verdict": {"bullish": [], "bearish": [], "risks": []},
        "summary": "x",
    }
    errs = validate_day(data)
    assert any("source_url" in e for e in errs)


def test_validate_day_accepts_potential():
    data = json.loads((ROOT / "public/data/2026-06-18.json").read_text(encoding="utf-8"))
    data["potential"] = {"window_days": 5, "stocks": [
        {"code": "1234", "name": "x", "pct": 0.1, "inst_net_yi": 1.0,
         "price_pos": 0.2, "chg_6m": 0.0, "theme": "重電",
         "catalyst": "", "sector": "電機", "history": "ok"}]}
    assert validate_day(data) == []


def test_validate_day_rejects_bad_potential():
    data = json.loads((ROOT / "public/data/2026-06-18.json").read_text(encoding="utf-8"))
    data["potential"] = {"window_days": 5, "stocks": "oops"}
    assert any("potential.stocks" in e for e in validate_day(data))


def test_validate_day_accepts_regime():
    data = json.loads((ROOT / "public/data/2026-06-18.json").read_text(encoding="utf-8"))
    data["regime"] = {"light": "green", "score": 4, "components": {
        "trend": {"score": 2, "missing": False, "detail": {}},
        "breadth": {"score": 1, "missing": False, "detail": {}},
        "vix": {"score": 0, "missing": False, "detail": {}},
        "chips": {"score": 1, "missing": False, "detail": {}},
    }}
    assert validate_day(data) == []


def test_validate_day_rejects_bad_regime_light():
    data = json.loads((ROOT / "public/data/2026-06-18.json").read_text(encoding="utf-8"))
    data["regime"] = {"light": "purple", "score": 1, "components": {}}
    assert any("regime.light" in e for e in validate_day(data))


def test_validate_day_missing_regime_is_fine():
    # 舊資料檔沒有 regime 欄，schema 不應報錯（optional）
    data = json.loads((ROOT / "public/data/2026-06-18.json").read_text(encoding="utf-8"))
    assert "regime" not in data
    assert validate_day(data) == []
