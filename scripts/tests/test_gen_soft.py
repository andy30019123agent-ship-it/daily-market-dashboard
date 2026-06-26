import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.gen_soft_openai import _news_ok  # noqa: E402

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
