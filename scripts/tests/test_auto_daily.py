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


def test_preserve_published_keeps_old_when_regressed(tmp_path, monkeypatch):
    import json as _j
    monkeypatch.setattr(ad, "DATA_DIR", tmp_path)
    (tmp_path / "2026-06-25.json").write_text(_j.dumps({
        "overview": {"tw": {"stats": [{"name": "成交金額"}, {"name": "外資"},
                                       {"name": "投信"}, {"name": "自營"}]}},
        "inst_top": {"foreign": {"buy": [{"code": "2330"}], "sell": []},
                     "trust": {"buy": [], "sell": []}, "dealer": {"buy": [], "sell": []}},
        "hot_stocks": {"tw": [{"code": "1101"}]},
        "sectors": {"tw": {"in": [{"name": "半導體"}]}},
    }), encoding="utf-8")
    day = {"overview": {"tw": {"stats": [{"name": "成交金額"}]}},
           "inst_top": {g: {"buy": [], "sell": []} for g in ("foreign", "trust", "dealer")},
           "hot_stocks": {"tw": []},
           "sectors": {"tw": {"in": []}}}
    ad._preserve_published(day, "2026-06-25")
    assert len(day["overview"]["tw"]["stats"]) == 4   # 三大法人大盤沿用舊版
    assert ad._inst_count(day["inst_top"]) == 1        # 個股法人沿用舊版
    assert day["hot_stocks"]["tw"]                      # 熱門股沿用舊版
    assert day["sectors"]["tw"]["in"]                  # 類股沿用舊版
