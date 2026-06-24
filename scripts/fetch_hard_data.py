"""抓取當日硬數據，輸出 public/data/<date>.partial.json。

只負責「能用免費 API 穩定取得」的硬數據（Task 0 結論）：
- 台股加權、成交金額、漲幅榜熱門股：TWSE OpenAPI
- 美股 道瓊/標普/那斯達克、CBOE VIX：FRED
缺口（費半 SOX、台指 VIX、外資買賣超、櫃買指數）填 None 並列入 _meta.missing，
由 AI 分身每日跑 RUNBOOK 時以 WebSearch 補上（見 Task 5）。

用法：python scripts/fetch_hard_data.py [YYYY-MM-DD]
"""
import os
import sys
import json
import pathlib
import datetime
import time
import csv
import io
import subprocess
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scripts.lib.parsers import (  # noqa: E402
    parse_bfi82u, parse_t86_top,
    parse_rwd_index, parse_rwd_fmtqik, parse_rwd_gainers, parse_rwd_sectors,
    build_sector_constituents,
)
from scripts.lib.us_holdings import US_HOLD  # noqa: E402

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
OUT_DIR = pathlib.Path(__file__).resolve().parents[1] / "public" / "data"

# 用 TWSE 官網 RWD（afterTrading/fund）：OpenAPI 有約 1~2 日延遲，RWD 是最新交易日
TWSE_AT = "https://www.twse.com.tw/rwd/zh/afterTrading"
TWSE_RWD = "https://www.twse.com.tw/rwd/zh/fund"
# 美股指數/VIX 已改由 auto_daily 用 Yahoo 抓（FRED 在 CI timeout），這裡不再用 FRED

# Alpha Vantage（費半 SOX 用 SOXX ETF 代理 + 美股重點股動向）
AV = "https://www.alphavantage.co/query"
AV_SLEEP = 13  # 免費版 5 次/分
US_WATCH = [("NVDA", "輝達"), ("TSM", "台積電 ADR"), ("AVGO", "博通"),
            ("AMD", "超微"), ("AAPL", "蘋果"), ("TSLA", "特斯拉")]
# 美股 11 大類股 SPDR ETF（用當日漲跌幅代表類股表現）
US_SECTORS = [("XLK", "科技"), ("XLF", "金融"), ("XLV", "醫療保健"), ("XLY", "非必需消費"),
              ("XLC", "通訊服務"), ("XLI", "工業"), ("XLP", "必需消費"), ("XLE", "能源"),
              ("XLU", "公用事業"), ("XLRE", "房地產"), ("XLB", "原物料")]


def av_key():
    return os.environ.get("AV_API_KEY") or _secret("alpha_vantage")


def _secret(name):
    p = pathlib.Path(__file__).resolve().parent / "secrets.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8")).get(name)
    return None


def av_quote(symbol, key):
    q = json.loads(get_text(f"{AV}?function=GLOBAL_QUOTE&symbol={symbol}&apikey={key}")).get("Global Quote", {})
    if not q.get("05. price"):
        raise RuntimeError(f"AV 無 {symbol} 報價（可能限流）")
    return {"price": float(q["05. price"]),
            "pct": round(float(q["10. change percent"].rstrip("%")), 2)}


def fmt_yi(v):
    """金額（億）格式化為帶正負號字串，回傳 (value_str, dir)。"""
    if v is None:
        return None, None
    sign = "+" if v >= 0 else "−"
    return f"{sign}{abs(v):,.1f} 億", ("up" if v >= 0 else "down")


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


def get_table(url):
    """抓 RWD 表格端點，回 {fields, data}。

    STOCK_DAY_ALL 端點會時而回 JSON、時而回 CSV（同一組參數），兩者都容忍，
    避免端點格式漂移時整批個股/類股成分股靜默變空。
    """
    text = get_text(url)
    if text.lstrip()[:1] in ("{", "["):
        return json.loads(text)
    rows = [r for r in csv.reader(io.StringIO(text)) if r]
    if len(rows) < 2:
        raise ValueError(f"CSV 回應無資料列：{url}")
    return {"fields": rows[0], "data": rows[1:], "stat": "OK"}


def taipei_today():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d")


def fetch_hard_data(date: str) -> dict:
    errors = []
    missing = []

    # ---- 台股加權 + 成交量 + 交易日（RWD，最新交易日）----
    tw_featured = None
    trade_value_yi = None
    trade_ymd = taipei_today().replace("-", "")
    spark = []
    try:
        fm = parse_rwd_fmtqik(get_json(f"{TWSE_AT}/FMTQIK?date={trade_ymd}&response=json"))
        trade_ymd = fm["date_ymd"]          # 真正最新交易日
        trade_value_yi = fm["trade_value_yi"]
        spark = [v for v in fm["spark"] if v is not None]
    except Exception as e:
        errors.append(f"RWD FMTQIK: {e}")

    sectors_tw = {"in": [], "out": []}
    try:
        mi = get_json(f"{TWSE_AT}/MI_INDEX?date={trade_ymd}&type=IND&response=json")
        idx = parse_rwd_index(mi)
        tw_featured = {"name": idx["name"], "close": idx["close"],
                       "change": idx["change"], "change_pct": idx["change_pct"],
                       "note": "較昨收", "spark": spark}
        sectors_tw = parse_rwd_sectors(mi, n=5)   # 同一支取真實類股漲跌
    except Exception as e:
        errors.append(f"RWD MI_INDEX: {e}")

    # ---- 台股漲幅榜熱門股 ----
    hot_tw = []
    sda = None
    try:
        sda = get_table(f"{TWSE_AT}/STOCK_DAY_ALL?date={trade_ymd}&response=json")
        hot_tw = parse_rwd_gainers(sda, n=5)
        for s in hot_tw:
            s["reason"] = ""  # 緣由由分身補
    except Exception as e:
        errors.append(f"RWD STOCK_DAY_ALL: {e}")

    # ---- 三大法人大盤買賣超（外資/投信/自營）----
    inst_net = {}
    try:
        bfi = get_json(f"{TWSE_RWD}/BFI82U?type=day&response=json&dayDate={trade_ymd}")
        inst_net = parse_bfi82u(bfi)
    except Exception as e:
        errors.append(f"BFI82U 三大法人: {e}")

    # ---- 三大法人個股買超前 5 ----
    inst_top = {"foreign": [], "trust": [], "dealer": []}
    try:
        t86 = get_json(f"{TWSE_RWD}/T86?date={trade_ymd}&selectType=ALLBUT0999&response=json")
        inst_top = parse_t86_top(t86, n=5)
    except Exception as e:
        errors.append(f"T86 個股法人: {e}")

    # ---- 台股子數據（成交金額 + 三大法人）----
    stats = []
    if trade_value_yi is not None:
        stats.append({"name": "成交金額", "value": f"{trade_value_yi:,} 億"})
    else:
        missing.append("成交金額")
    for label, key in [("外資買賣超", "外資"), ("投信買賣超", "投信"), ("自營買賣超", "自營")]:
        if key in inst_net:
            val, d = fmt_yi(inst_net[key])
            stats.append({"name": label, "value": val, "dir": d})
        else:
            missing.append(label)

    # ---- 美股指數 ----
    # 註：FRED 在 GitHub Actions 會 read timeout（每檔重試數分鐘），且只給延遲值。
    # 美股指數改由 auto_daily 用 Yahoo chart API 抓真實點數，此處不再呼叫 FRED。
    us = []

    # ---- 費半 SOX（Alpha Vantage，SOXX ETF 代理）+ 美股重點股動向 ----
    us_hot = []
    key = av_key()
    if key:
        try:
            q = av_quote("SOXX", key)
            us.append({"name": "費城半導體", "close": round(q["price"], 2),
                       "change_pct": q["pct"], "proxy": "SOXX", "spark": []})
        except Exception as e:
            errors.append(f"AV SOXX: {e}")
            missing.append("費城半導體 SOX")
        movers = []
        for sym, name in US_WATCH:
            time.sleep(AV_SLEEP)
            try:
                q = av_quote(sym, key)
                movers.append({"code": sym, "name": name, "change_pct": q["pct"], "reason": ""})
            except Exception as e:
                errors.append(f"AV {sym}: {e}")
        movers.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
        us_hot = movers[:5]
        if not us_hot:
            missing.append("美股熱門個股")
    else:
        missing.append("費城半導體 SOX（缺 AV 金鑰）")
        missing.append("美股熱門個股（缺 AV 金鑰）")

    # ---- 美股類股表現（11 大 SPDR ETF 漲跌幅）----
    sectors_us = {"in": [], "out": []}
    if key:
        secs = []
        for sym, name in US_SECTORS:
            time.sleep(AV_SLEEP)
            try:
                q = av_quote(sym, key)
                secs.append({"name": name, "pct": q["pct"]})
            except Exception as e:
                errors.append(f"AV {sym}: {e}")
        if secs:
            mx = max((abs(s["pct"]) for s in secs), default=1) or 1
            def _row(s):
                return {"name": s["name"],
                        "amount": f"{'+' if s['pct'] >= 0 else ''}{s['pct']:.2f}%",
                        "weight": round(abs(s["pct"]) / mx, 2)}
            up = sorted(secs, key=lambda x: x["pct"], reverse=True)[:5]
            down = sorted(secs, key=lambda x: x["pct"])[:5]
            sectors_us = {"in": [_row(s) for s in up], "out": [_row(s) for s in down]}
        else:
            missing.append("美股類股表現")
    else:
        missing.append("美股類股表現（缺 AV 金鑰）")

    # ---- VIX ----
    # 美股 VIX 同樣改由 auto_daily 用 Yahoo（^VIX）抓，FRED VIXCLS 在 CI 會 timeout。
    vix_us = None
    missing.append("台指 VIX（無免費 API，分身 WebSearch 補）")

    # ---- 類股成分股（台股真實 / 美股 ETF 主要成分）----
    try:
        basic = get_json("https://openapi.twse.com.tw/v1/opendata/t187ap03_L")
        tw_names = [s["name"] for s in sectors_tw["in"] + sectors_tw["out"]]
        if sda:
            cons = build_sector_constituents(tw_names, sda, basic, n=12)
            for s in sectors_tw["in"] + sectors_tw["out"]:
                s["constituents"] = cons.get(s["name"], [])
    except Exception as e:
        errors.append(f"類股成分(TW): {e}")
    for s in sectors_us["in"] + sectors_us["out"]:
        s["constituents"] = [{"code": c, "name": n} for c, n in US_HOLD.get(s["name"], [])]

    # 報告日期＝最新「有資料」的台股交易日（trade_ymd），非日曆今天。
    # 沒開盤/資料未發布時，trade_ymd 仍是前一交易日 → 自然沿用前收，不會生出帶舊數據的新日期。
    report_date = (f"{trade_ymd[:4]}-{trade_ymd[4:6]}-{trade_ymd[6:8]}"
                   if trade_ymd and len(trade_ymd) == 8 and trade_ymd.isdigit() else date)

    partial = {
        "date": report_date,
        "overview": {
            "tw": {"featured": tw_featured, "stats": stats},
            "us": us,
            "vix": {"tw": None, "us": vix_us},
        },
        "hot_stocks": {"tw": hot_tw, "us": us_hot},
        "sectors_tw": sectors_tw,
        "sectors_us": sectors_us,
        "inst_top": inst_top,
        "_meta": {"errors": errors, "missing": missing, "fetched_at": taipei_today(), "trade_date": trade_ymd},
    }
    return partial


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    date = args[0] if args else taipei_today()
    force = "--force" in sys.argv
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{date}.partial.json"
    # 防重觸發燒 Alpha Vantage 額度：當天已成功抓過（partial 已存在且 _meta.errors 為空）
    # 就跳過重抓、沿用既有結果；要強制重抓請加 --force。
    if out.exists() and not force:
        try:
            existing = json.loads(out.read_text(encoding="utf-8"))
            if not existing.get("_meta", {}).get("errors"):
                print(f"⏭️  {date} 今日已成功抓過（{out.name}，無 errors），跳過重抓以省 Alpha Vantage 額度。要強制重抓請加 --force。")
                return
        except Exception:
            pass  # partial 壞掉/讀不動 → 當作沒有，照常重抓
    partial = fetch_hard_data(date)
    out.write_text(json.dumps(partial, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 已寫出 {out}")
    print(f"加權：{partial['overview']['tw']['featured']}")
    print(f"美股：{[(u['name'], u['close'], u['change_pct']) for u in partial['overview']['us']]}")
    print(f"VIX：{partial['overview']['vix']['us']}")
    print(f"熱門股：{[(s['name'], s['change_pct']) for s in partial['hot_stocks']['tw']]}")
    print(f"三大法人(stats)：{[(s['name'], s.get('value')) for s in partial['overview']['tw']['stats']]}")
    print(f"法人買超前5 外資：{[(s['name'], s['zhang']) for s in partial['inst_top']['foreign']['buy']]}")
    print(f"法人賣超前5 外資：{[(s['name'], s['zhang']) for s in partial['inst_top']['foreign']['sell']]}")
    print(f"類股漲幅前5：{[(s['name'], s['amount']) for s in partial['sectors_tw']['in']]}")
    print(f"errors：{partial['_meta']['errors'] or '（無）'}")
    print(f"missing：{partial['_meta']['missing']}")


if __name__ == "__main__":
    main()
