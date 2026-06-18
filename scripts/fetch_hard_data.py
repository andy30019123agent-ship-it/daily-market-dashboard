"""抓取當日硬數據，輸出 public/data/<date>.partial.json。

只負責「能用免費 API 穩定取得」的硬數據（Task 0 結論）：
- 台股加權、成交金額、漲幅榜熱門股：TWSE OpenAPI
- 美股 道瓊/標普/那斯達克、CBOE VIX：FRED
缺口（費半 SOX、台指 VIX、外資買賣超、櫃買指數）填 None 並列入 _meta.missing，
由 AI 分身每日跑 RUNBOOK 時以 WebSearch 補上（見 Task 5）。

用法：python scripts/fetch_hard_data.py [YYYY-MM-DD]
"""
import sys
import json
import pathlib
import datetime
import time
import subprocess
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scripts.lib.parsers import (  # noqa: E402
    parse_twse_index, parse_fmtqik, twse_top_gainers, parse_fred_csv,
)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
OUT_DIR = pathlib.Path(__file__).resolve().parents[1] / "public" / "data"

TWSE = "https://openapi.twse.com.tw/v1/exchangeReport"
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="
FRED_IDS = {"道瓊": "DJIA", "標普 500": "SP500", "那斯達克": "NASDAQCOM"}


def _try_urllib(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=12) as r:
        return r.read().decode("utf-8")


def _try_curl(url):
    out = subprocess.run(
        ["curl", "-s", "--http1.1", "-4", "-L", "--max-time", "30", "-A", UA, url],
        capture_output=True, text=True, timeout=40,
    )
    if out.returncode != 0 or not out.stdout:
        raise RuntimeError(f"curl rc={out.returncode}")
    return out.stdout


def get_text(url, retries=3):
    """curl 優先（跨環境最穩），urllib 後備；整體重試含退避，對抗暫時性網路抖動。"""
    last = None
    for i in range(retries):
        for fn in (_try_curl, _try_urllib):
            try:
                return fn(url)
            except Exception as e:
                last = e
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"取得失敗（{retries} 次）：{last}")


def get_json(url):
    return json.loads(get_text(url))


def taipei_today():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d")


def fetch_hard_data(date: str) -> dict:
    errors = []
    missing = []

    # ---- 台股加權 + 成交量走勢 ----
    tw_featured = None
    spark = []
    try:
        mi = get_json(f"{TWSE}/MI_INDEX")
        idx = parse_twse_index(mi, "發行量加權股價指數")
        tw_featured = {"name": idx["name"], "close": idx["close"],
                       "change": idx["change"], "change_pct": idx["change_pct"], "note": "較昨收"}
    except Exception as e:
        errors.append(f"TWSE MI_INDEX: {e}")

    trade_value_yi = None
    try:
        fm = parse_fmtqik(get_json(f"{TWSE}/FMTQIK"))
        trade_value_yi = fm["trade_value_yi"]
        spark = [v for v in fm["spark"] if v is not None]
        if tw_featured and tw_featured.get("close") is None:
            tw_featured["close"] = fm["taiex"]
    except Exception as e:
        errors.append(f"TWSE FMTQIK: {e}")
    if tw_featured is not None:
        tw_featured["spark"] = spark

    # ---- 台股漲幅榜熱門股 ----
    hot_tw = []
    try:
        hot_tw = twse_top_gainers(get_json(f"{TWSE}/STOCK_DAY_ALL"), n=5)
        for s in hot_tw:
            s["reason"] = ""  # 緣由由分身補
    except Exception as e:
        errors.append(f"TWSE STOCK_DAY_ALL: {e}")

    # ---- 台股子數據 ----
    stats = []
    missing.append("櫃買 OTC 指數（TPEX 端點待確認）")
    if trade_value_yi is not None:
        stats.append({"name": "成交金額", "value": f"{trade_value_yi:,} 億"})
    else:
        missing.append("成交金額")
    missing.append("外資買賣超（TWSE 三大法人端點待確認）")

    # ---- 美股指數（FRED）----
    us = []
    for name, fid in FRED_IDS.items():
        try:
            d = parse_fred_csv(get_text(FRED + fid))
            us.append({"name": name, "close": d["close"], "change_pct": d["change_pct"], "spark": d["spark"]})
        except Exception as e:
            errors.append(f"FRED {fid}: {e}")
        time.sleep(0.8)  # 對來源友善、避免被限流
    missing.append("費城半導體 SOX（無免費 API，分身 WebSearch 補）")

    # ---- VIX ----
    vix_us = None
    try:
        d = parse_fred_csv(get_text(FRED + "VIXCLS"))
        vix_us = {"value": d["close"], "change": d["change_pct"],
                  "state": "", "note": "", "gauge": min(1.0, d["close"] / 50)}
    except Exception as e:
        errors.append(f"FRED VIXCLS: {e}")
    missing.append("台指 VIX（無免費 API，分身 WebSearch 補）")

    partial = {
        "date": date,
        "overview": {
            "tw": {"featured": tw_featured, "stats": stats},
            "us": us,
            "vix": {"tw": None, "us": vix_us},
        },
        "hot_stocks": {"tw": hot_tw, "us": []},
        "_meta": {"errors": errors, "missing": missing, "fetched_at": taipei_today()},
    }
    return partial


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else taipei_today()
    partial = fetch_hard_data(date)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{date}.partial.json"
    out.write_text(json.dumps(partial, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 已寫出 {out}")
    print(f"加權：{partial['overview']['tw']['featured']}")
    print(f"美股：{[(u['name'], u['close'], u['change_pct']) for u in partial['overview']['us']]}")
    print(f"VIX：{partial['overview']['vix']['us']}")
    print(f"熱門股：{partial['hot_stocks']['tw']}")
    print(f"errors：{partial['_meta']['errors'] or '（無）'}")
    print(f"missing：{partial['_meta']['missing']}")


if __name__ == "__main__":
    main()
