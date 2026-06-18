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
