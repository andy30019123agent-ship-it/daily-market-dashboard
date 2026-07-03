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


# --- 明日法說會（跨專案互串，2026-07-03 新增）---

def test_earnings_line_appears_when_present():
    day = _day()
    day["earnings_tomorrow"] = [{"id": "2330", "name": "台積電", "industry": "半導體"}]
    txt = build_summary_text(day)
    assert "📅 明日法說會" in txt
    assert "2330 台積電（半導體）" in txt


def test_earnings_line_caps_at_five_and_shows_remainder():
    day = _day()
    day["earnings_tomorrow"] = [{"id": str(i), "name": f"公司{i}", "industry": ""} for i in range(7)]
    txt = build_summary_text(day)
    assert "等 7 場" in txt
    assert "公司6" not in txt  # 只列前 5 筆


# --- 市場紅綠燈首行（regime，元件 A，2026-07-03 新增）---

def test_regime_line_appears_and_is_first_section():
    day = _day()
    day["regime"] = {"light": "yellow", "score": 3, "components": {}}
    txt = build_summary_text(day)
    assert "🚦 市場紅綠燈：🟡 3/6 分" in txt
    # 順序：標題後第一段就是紅綠燈，早於「台股創高」(台股概況)
    assert txt.index("🚦 市場紅綠燈") < txt.index("台股創高")


def test_regime_line_absent_when_missing():
    txt = build_summary_text(_day())  # 無 regime 欄（舊資料）
    assert "紅綠燈" not in txt


def test_regime_line_green_red_emoji():
    day = _day()
    day["regime"] = {"light": "green", "score": 5}
    assert "🟢" in build_summary_text(day)
    day["regime"] = {"light": "red", "score": -2}
    assert "🔴" in build_summary_text(day)


# --- 機會股 Top 5（跨專案 opportunities.json，元件 C，2026-07-03 新增）---

def _opp_day():
    day = _day()
    day["opportunities"] = {"date": "2026-06-18", "picks": [
        {"id": "2330", "name": "台積電", "score": 8, "reasons": ["外資連買", "均線多頭"]},
        {"id": "2454", "name": "聯發科", "score": 6, "reasons": ["法人買超"]},
    ]}
    return day


def test_opportunities_section_lists_picks_with_reason():
    txt = build_summary_text(_opp_day())
    assert "🎯 機會股 Top 5" in txt
    assert "• 2330 台積電｜8 分｜外資連買" in txt
    assert "• 2454 聯發科｜6 分｜法人買超" in txt


def test_opportunities_section_caps_at_five():
    day = _day()
    day["opportunities"] = {"date": "x", "picks": [
        {"id": str(i), "name": f"股{i}", "score": i, "reasons": []} for i in range(7)
    ]}
    txt = build_summary_text(day)
    assert "股6" not in txt
    assert "股4" in txt


def test_opportunities_section_absent_when_missing_or_empty():
    txt = build_summary_text(_day())  # 無 opportunities 欄
    assert "機會股" not in txt
    day = _day()
    day["opportunities"] = {"date": "x", "picks": []}
    txt2 = build_summary_text(day)
    assert "機會股" not in txt2
    day2 = _day()
    day2["opportunities"] = None
    txt3 = build_summary_text(day2)
    assert "機會股" not in txt3


# --- 元件 C 整體順序：紅綠燈 → 台美概況/研判 → 機會股 → 法說會 → 命中率 ---

def test_component_c_overall_ordering(tmp_path, monkeypatch):
    acc_path = tmp_path / "accuracy.json"
    acc_path.write_text(json.dumps({
        "tw": {"recent30_rate": 55.0, "recent30_total": 9},
        "us": {"recent30_rate": 40.0, "recent30_total": 7},
    }), encoding="utf-8")
    monkeypatch.setattr(notify, "ACCURACY_PATH", acc_path)

    day = _opp_day()
    day["regime"] = {"light": "green", "score": 4}
    day["earnings_tomorrow"] = [{"id": "2330", "name": "台積電", "industry": "半導體"}]
    txt = build_summary_text(day)
    i_regime = txt.index("🚦 市場紅綠燈")
    i_tw = txt.index("台股創高")
    i_opp = txt.index("🎯 機會股 Top 5")
    i_earn = txt.index("📅 明日法說會")
    i_acc = txt.index("近 30 日研判命中率")
    assert i_regime < i_tw < i_opp < i_earn < i_acc


def test_earnings_line_absent_when_missing_or_empty():
    # 沒有 earnings_tomorrow 欄位（舊版 day.json）不應出錯，也不出現該行
    txt = build_summary_text(_day())
    assert "法說會" not in txt
    # 有欄位但空陣列（抓不到/明日無場次）同樣靜默跳過
    day = _day()
    day["earnings_tomorrow"] = []
    txt2 = build_summary_text(day)
    assert "法說會" not in txt2
