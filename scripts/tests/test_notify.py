import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import scripts.notify as notify  # noqa: E402
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


def test_summary_has_disclaimer():
    assert "僅供參考" in build_summary_text(_day())
    assert "非投資建議" in build_summary_text(_day())


def test_accuracy_line_appears_when_file_exists(tmp_path, monkeypatch):
    acc_path = tmp_path / "accuracy.json"
    acc_path.write_text(json.dumps({
        "tw": {"recent30_rate": 55.0, "recent30_total": 9},
        "us": {"recent30_rate": 40.0, "recent30_total": 7},
    }), encoding="utf-8")
    monkeypatch.setattr(notify, "ACCURACY_PATH", acc_path)
    txt = build_summary_text(_day())
    assert "近 30 日研判命中率" in txt
    assert "台股 55.0%" in txt
    assert "美股 40.0%" in txt
    assert "樣本 9" in txt


def test_accuracy_line_silently_skipped_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(notify, "ACCURACY_PATH", tmp_path / "missing.json")
    txt = build_summary_text(_day())
    assert "命中率" not in txt
    # 缺檔不應讓推播組字失敗，其餘內容仍正常
    assert "台股創高" in txt
