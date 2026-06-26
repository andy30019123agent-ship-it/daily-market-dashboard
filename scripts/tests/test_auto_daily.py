import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import scripts.auto_daily as ad  # noqa: E402


def test_skips_unsettled_intraday_day(monkeypatch):
    """盤中未結算（加權 close=None）時，_run 應乾淨返回、不呼叫 OpenAI（不花錢、不產殘缺報告）。"""
    partial = {"date": "2026-06-26",
               "overview": {"tw": {"featured": {"close": None}}},
               "_meta": {"trade_date": "20260626"}}
    monkeypatch.setattr(ad, "pick_partial", lambda: ("20260626", partial))

    called = {"gen": False}

    def _boom(_):
        called["gen"] = True
        raise AssertionError("不該呼叫 gen_soft")

    monkeypatch.setattr(ad, "gen_soft", _boom)
    ad._run(dry_run=False)
    assert called["gen"] is False
