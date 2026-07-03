import json
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


# --- 硬數據不齊不定版 ---
from scripts.auto_daily import _is_complete


def test_is_complete_true_with_radar_stocks():
    assert _is_complete({"radar": {"stocks": [{"code": "1"}]}}) is True


def test_is_complete_false_without_radar():
    assert _is_complete({"radar": None}) is False
    assert _is_complete({"radar": {"stocks": []}}) is False
    assert _is_complete({}) is False


# --- 明日法說會（跨專案互串，2026-07-03 新增）：失敗安全測試 ---

class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        import json as _j
        return _j.dumps(self._payload).encode()


def test_fetch_earnings_tomorrow_filters_by_date_and_type(monkeypatch):
    monkeypatch.setattr(ad, "_taipei_tomorrow", lambda: "2026-07-04")
    payload = {"events": [
        {"id": "2330", "name": "台積電", "industry": "半導體", "date": "2026-07-04", "type": "法說會"},
        {"id": "1101", "name": "台泥", "industry": "水泥", "date": "2026-07-04", "type": "除權息"},  # 型別不符→濾掉
        {"id": "2317", "name": "鴻海", "industry": "電子", "date": "2026-07-05", "type": "法說會"},  # 別天→濾掉
    ]}
    monkeypatch.setattr(ad.urllib.request, "urlopen", lambda req, timeout=10: _FakeResp(payload))
    out = ad.fetch_earnings_tomorrow()
    assert out == [{"id": "2330", "name": "台積電", "industry": "半導體"}]


def test_fetch_earnings_tomorrow_network_failure_returns_empty(monkeypatch):
    def _boom(req, timeout=10):
        raise TimeoutError("連線逾時")
    monkeypatch.setattr(ad.urllib.request, "urlopen", _boom)
    assert ad.fetch_earnings_tomorrow() == []


def test_fetch_earnings_tomorrow_bad_json_returns_empty(monkeypatch):
    class _BadResp(_FakeResp):
        def read(self):
            return b"not json{"
    monkeypatch.setattr(ad.urllib.request, "urlopen", lambda req, timeout=10: _BadResp({}))
    assert ad.fetch_earnings_tomorrow() == []


def test_fetch_earnings_tomorrow_missing_events_key_returns_empty(monkeypatch):
    monkeypatch.setattr(ad.urllib.request, "urlopen", lambda req, timeout=10: _FakeResp({"foo": "bar"}))
    assert ad.fetch_earnings_tomorrow() == []


# --- 機會股 Top 5（跨專案互串 opportunities.json，元件 C，2026-07-03 新增）：失敗安全測試 ---

def test_fetch_opportunities_returns_picks_when_ok(monkeypatch):
    payload = {"date": "2026-06-18", "picks": [{"id": "2330", "name": "台積電", "score": 8}]}
    monkeypatch.setattr(ad.urllib.request, "urlopen", lambda req, timeout=10: _FakeResp(payload))
    out = ad.fetch_opportunities()
    assert out == payload


def test_fetch_opportunities_network_failure_returns_none(monkeypatch):
    def _boom(req, timeout=10):
        raise TimeoutError("連線逾時")
    monkeypatch.setattr(ad.urllib.request, "urlopen", _boom)
    assert ad.fetch_opportunities() is None


def test_fetch_opportunities_empty_picks_returns_none(monkeypatch):
    monkeypatch.setattr(ad.urllib.request, "urlopen",
                        lambda req, timeout=10: _FakeResp({"date": "x", "picks": []}))
    assert ad.fetch_opportunities() is None


def test_fetch_opportunities_bad_json_returns_none(monkeypatch):
    class _BadResp(_FakeResp):
        def read(self):
            return b"not json{"
    monkeypatch.setattr(ad.urllib.request, "urlopen", lambda req, timeout=10: _BadResp({}))
    assert ad.fetch_opportunities() is None


def test_fetch_opportunities_not_yet_deployed_404_returns_none(monkeypatch):
    # 對方 repo 尚未上線該檔（404）也算連線類錯誤，一樣失敗安全回 None
    def _404(req, timeout=10):
        import urllib.error
        raise urllib.error.HTTPError(req.full_url if hasattr(req, "full_url") else "x",
                                     404, "Not Found", {}, None)
    monkeypatch.setattr(ad.urllib.request, "urlopen", _404)
    assert ad.fetch_opportunities() is None


# --- 市場紅綠燈（regime，元件 A，2026-07-03 新增）：auto_daily 接線測試 ---

def test_attach_regime_writes_regime_key(tmp_path, monkeypatch):
    monkeypatch.setattr(ad, "DATA_DIR", tmp_path)
    monkeypatch.setattr("scripts.lib.index_history.HISTORY_PATH", tmp_path / "index-history.json")
    monkeypatch.setattr(ad, "load_history", lambda: [{"date": f"2026-01-{i:02d}", "close": 100 + i}
                                                      for i in range(1, 61)])
    day = {"date": "2026-07-03", "breadth": {"up": 600, "down": 400},
           "overview": {"vix": {"tw": {"value": 18}}},
           "inst_net_yi": {"外資": 5, "投信": 0, "自營": 0}}
    ad._attach_regime(day, "2026-07-03")
    assert day["regime"]["light"] in ("green", "yellow", "red")
    assert set(day["regime"]["components"].keys()) == {"trend", "breadth", "vix", "chips"}


def test_attach_regime_failure_does_not_raise(tmp_path, monkeypatch):
    monkeypatch.setattr(ad, "load_history", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    day = {"date": "2026-07-03"}
    ad._attach_regime(day, "2026-07-03")  # 不應丟例外
    assert "regime" not in day  # 失敗時乾脆不寫入，不留半殘資料


def test_recent_inst_entries_orders_oldest_to_newest_and_includes_today(tmp_path, monkeypatch):
    monkeypatch.setattr(ad, "DATA_DIR", tmp_path)
    (tmp_path / "2026-07-01.json").write_text(
        json.dumps({"date": "2026-07-01", "inst_net_yi": {"外資": 1}}), encoding="utf-8")
    (tmp_path / "2026-07-02.json").write_text(
        json.dumps({"date": "2026-07-02", "inst_net_yi": {"外資": 2}}), encoding="utf-8")
    today = {"date": "2026-07-03", "inst_net_yi": {"外資": 3}}
    entries = ad._recent_inst_entries(today, "2026-07-03", n=5)
    assert entries == [{"外資": 1}, {"外資": 2}, {"外資": 3}]
