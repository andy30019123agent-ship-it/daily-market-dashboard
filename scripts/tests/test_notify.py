import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.notify import build_summary_text, build_failure_text  # noqa: E402


def _day():
    return {
        "date": "2026-06-18",
        "overview": {
            "tw": {"featured": {"close": 46465.2, "change_pct": 1.28}},
            "us": [{"name": "標普 500", "change_pct": -1.21},
                   {"name": "那斯達克", "change_pct": -1.34}],
        },
        "summary": "台股創高、美股收黑。",
    }


def test_summary_has_link_and_content():
    txt = build_summary_text(_day(), "https://x.io/d/")
    assert "https://x.io/d/" in txt
    assert "台股創高" in txt
    assert "46,465" in txt
    assert "2026-06-18" in txt


def test_summary_default_url():
    assert "github.io" in build_summary_text(_day())


def test_failure_text():
    assert "失敗" in build_failure_text("FRED 連線逾時")
    assert "FRED 連線逾時" in build_failure_text("FRED 連線逾時")
