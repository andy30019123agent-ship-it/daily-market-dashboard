import json

from scripts.lib import twse_hist as th


def test_parse_t86_filters_and_parses():
    payload = {"stat": "OK",
               "fields": ["代號", "名稱"] + ["x"] * 16 + ["淨額"],
               "data": [
                   ["2330", "台積電"] + ["0"] * 16 + ["1,234,000"],
                   ["00403A", "某ETF"] + ["0"] * 16 + ["999"],  # 非4碼→濾掉
               ]}
    out = th.parse_t86(payload)
    assert out == {"2330": 1234000}


def test_parse_t86_non_trading_day():
    assert th.parse_t86({"stat": "很抱歉，沒有符合條件的資料!"}) == {}


def test_fetch_t86_cached_hit(tmp_path):
    (tmp_path / "t86-20260703.json").write_text(json.dumps({"2330": 500}), encoding="utf-8")

    def _boom(url):
        raise AssertionError("快取命中時不該連網")

    got = th.fetch_t86_cached("20260703", tmp_path, get=_boom)
    assert got == {"2330": 500}


def test_fetch_t86_cached_miss_writes(tmp_path):
    payload = {"stat": "OK", "fields": ["代號", "名稱"] + ["x"] * 16 + ["淨額"],
               "data": [["2317", "鴻海"] + ["0"] * 16 + ["10,000"]]}
    got = th.fetch_t86_cached("20260701", tmp_path, get=lambda url: json.dumps(payload))
    assert got == {"2317": 10000}
    assert (tmp_path / "t86-20260701.json").exists()


def test_fetch_t86_network_failure_not_cached(tmp_path):
    def _fail(url):
        raise OSError("network")

    got = th.fetch_t86_cached("20260702", tmp_path, get=_fail)
    assert got == {}
    # 網路失敗不得寫快取（否則永久把真交易日誤存成空）
    assert not (tmp_path / "t86-20260702.json").exists()


def test_fetch_t86_non_trading_cached(tmp_path):
    # 官方回「非交易日」→ 可解析回應 → 應快取為空（正確）
    got = th.fetch_t86_cached("20260627", tmp_path,
                              get=lambda url: '{"stat":"很抱歉，沒有符合條件的資料!"}')
    assert got == {}
    assert (tmp_path / "t86-20260627.json").exists()
