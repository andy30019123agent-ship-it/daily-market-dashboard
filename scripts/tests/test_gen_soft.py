import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.gen_soft_openai import _news_ok, _hard_context  # noqa: E402

RD = "2026-06-24"


def test_rejects_non_http():
    assert not _news_ok({"source_url": "javascript:alert(1)", "date": RD}, RD)


def test_rejects_youtube_and_social():
    for u in ("https://www.youtube.com/watch?v=x",
              "https://youtu.be/x",
              "https://x.com/foo/status/1",
              "https://www.facebook.com/foo",
              "https://www.ptt.cc/bbs/Stock/x.html"):
        assert not _news_ok({"source_url": u, "date": RD}, RD), u


def test_rejects_stale_other_day_news():
    # 一週前的舊新聞（別天）→ 剔除
    assert not _news_ok(
        {"source_url": "https://news.cnyes.com/news/id/1", "date": "2026-06-17"}, RD
    )


def test_accepts_same_day_reputable_article():
    assert _news_ok(
        {"source_url": "https://news.cnyes.com/news/id/123", "date": RD}, RD
    )


def test_accepts_prev_trading_day_within_window():
    assert _news_ok(
        {"source_url": "https://www.cna.com.tw/news/afe/1.aspx", "date": "2026-06-23"}, RD
    )


def test_keeps_when_date_missing_but_source_ok():
    # 沒給 date 時不因日期剔除（仍須通過來源檢查）
    assert _news_ok({"source_url": "https://udn.com/news/story/1/2"}, RD)


# --- _hard_context 帶入市場寬度/融資餘額（2026-07-03 新增），供 AI 研判多一維度 ---

def test_hard_context_includes_breadth_and_margin_when_present():
    partial = {
        "date": "2026-07-02",
        "overview": {"tw": {"featured": {"close": 22000, "change_pct": 1.0}, "stats": []}, "us": [], "vix": {}},
        "breadth": {"up": 649, "up_limit": 54, "down": 323, "down_limit": 1, "flat": 75},
        "margin": {"listed": {"balance_yi": 6208.4, "change_yi": 113.3},
                   "otc": {"balance_yi": 2103.4, "change_yi": 19.2},
                   "total_yi": 8311.8, "total_change_yi": 132.5},
    }
    ctx = _hard_context(partial)
    assert "市場寬度" in ctx and "上漲 649" in ctx and "下跌 323" in ctx
    assert "融資餘額" in ctx and "8,311.8" in ctx


def test_hard_context_omits_breadth_and_margin_when_absent():
    # 舊版 partial 沒有這兩個新欄位時，_hard_context 不能出錯、也不應出現這些字樣
    partial = {"date": "2026-07-02",
               "overview": {"tw": {"featured": {"close": 22000, "change_pct": 1.0}, "stats": []}, "us": [], "vix": {}}}
    ctx = _hard_context(partial)
    assert "市場寬度" not in ctx
    assert "融資餘額" not in ctx


# --- annotate_potential（低基期潛力 AI 標註）---
from scripts.gen_soft_openai import annotate_potential


def test_annotate_potential_fallback_no_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    stocks = [{"code": "1234", "name": "某某", "sector": "電機"}]
    annotate_potential(stocks)
    assert stocks[0]["theme"] == "電機"
    assert stocks[0]["catalyst"] == ""


def test_annotate_potential_empty_ok():
    annotate_potential([])
