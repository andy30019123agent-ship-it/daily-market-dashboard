import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.lib import index_history as ih  # noqa: E402


def test_parse_fmtqik_month_extracts_all_rows():
    payload = {
        "fields": ["日期", "成交股數", "成交金額", "成交筆數", "發行量加權股價指數", "漲跌點數"],
        "data": [
            ["115/06/01", "1", "2", "3", "45,337.91", "604.97"],
            ["115/06/02", "1", "2", "3", "45,557.31", "219.40"],
        ],
    }
    out = ih.parse_fmtqik_month(payload)
    assert out == [
        {"date": "2026-06-01", "close": 45337.91},
        {"date": "2026-06-02", "close": 45557.31},
    ]


def test_parse_fmtqik_month_skips_bad_rows():
    payload = {
        "fields": ["日期", "發行量加權股價指數"],
        "data": [["115/06/01", "45,337.91"], ["bad", "x"]],
    }
    out = ih.parse_fmtqik_month(payload)
    assert out == [{"date": "2026-06-01", "close": 45337.91}]


def test_parse_fmtqik_month_missing_columns_returns_empty():
    assert ih.parse_fmtqik_month({"fields": ["日期"], "data": [["115/06/01"]]}) == []


def test_merge_entries_dedupes_by_date_new_overwrites_old():
    history = [{"date": "2026-06-01", "close": 100}]
    new = [{"date": "2026-06-01", "close": 101}, {"date": "2026-06-02", "close": 102}]
    out = ih.merge_entries(history, new)
    assert out == [{"date": "2026-06-01", "close": 101}, {"date": "2026-06-02", "close": 102}]


def test_merge_entries_skips_invalid():
    out = ih.merge_entries([], [{"date": None, "close": 1}, {"date": "2026-06-01", "close": None},
                                 {"date": "2026-06-02", "close": 100}])
    assert out == [{"date": "2026-06-02", "close": 100}]


def test_merge_entries_caps_to_max():
    history = [{"date": f"2026-01-{d:02d}", "close": d} for d in range(1, 11)]
    out = ih.merge_entries(history, [], max_entries=3)
    assert len(out) == 3
    assert out[-1]["date"] == "2026-01-10"  # 保留最新的


def test_load_history_missing_file_returns_empty(tmp_path):
    assert ih.load_history(tmp_path / "nope.json") == []


def test_load_history_bad_json_returns_empty(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json{", encoding="utf-8")
    assert ih.load_history(p) == []


def test_save_and_load_roundtrip(tmp_path):
    p = tmp_path / "sub" / "index-history.json"
    entries = [{"date": "2026-06-01", "close": 100.5}]
    ih.save_history(entries, p)
    assert ih.load_history(p) == entries


def test_backfill_merges_multiple_months():
    calls = []

    def fake_get_json(url):
        calls.append(url)
        # 每次回一個月只有一天的資料，月份用 url 裡的 YYYYMM 反推
        ymd = url.split("date=")[1].split("&")[0]
        yyyymm = ymd[:6]
        roc_y = int(yyyymm[:4]) - 1911
        return {"fields": ["日期", "發行量加權股價指數"],
                "data": [[f"{roc_y}/{yyyymm[4:]}/15", "45000.00"]]}

    out = ih.backfill(fake_get_json, months_back=3, sleep_s=0, from_date=__import__("datetime").date(2026, 7, 3))
    assert len(calls) == 3
    assert len(out) == 3
    assert out[0]["date"] < out[-1]["date"]  # 已排序


def test_backfill_one_month_failure_does_not_abort_others():
    def flaky(url):
        if "202606" in url:
            raise RuntimeError("boom")
        ymd = url.split("date=")[1].split("&")[0]
        return {"fields": ["日期", "發行量加權股價指數"], "data": [[f"{int(ymd[:4]) - 1911}/{ymd[4:6]}/01", "1.0"]]}

    out = ih.backfill(flaky, months_back=3, sleep_s=0, from_date=__import__("datetime").date(2026, 7, 3))
    assert len(out) == 2  # 06 月失敗，其餘 2 個月仍拿到
