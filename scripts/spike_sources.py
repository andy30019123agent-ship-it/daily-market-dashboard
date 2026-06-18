"""一次性資料源探測腳本（Task 0 spike）。

用法：
    python scripts/spike_sources.py twse   # 台股加權與成交
    python scripts/spike_sources.py us     # 美股四大指數（stooq）
    python scripts/spike_sources.py fng     # 美股恐懼貪婪指數（CNN）
    python scripts/spike_sources.py all     # 全部
目的：實測每個免費端點是否拿得到、回應格式為何，結論寫進 docs/data-sources.md。
"""
import sys
import json
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def fetch(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", errors="replace")


def show(label, url, headers=None):
    print(f"\n{'='*70}\n[{label}] {url}")
    try:
        status, body = fetch(url, headers)
        print(f"HTTP {status} | {len(body)} bytes")
        print(body[:800])
    except urllib.error.HTTPError as e:
        print(f"HTTPError {e.code}: {e.reason}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")


def probe_twse():
    show("TWSE 大盤每日統計 MI_INDEX",
         "https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX")
    show("TWSE 個股當日成交 STOCK_DAY_ALL",
         "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL")
    show("TWSE 大盤指數歷史 FMTQIK（成交統計）",
         "https://openapi.twse.com.tw/v1/exchangeReport/FMTQIK")


def probe_us():
    for code in ("^dji", "^spx", "^ndq", "^sox"):
        show(f"stooq {code}",
             f"https://stooq.com/q/l/?s={code}&f=sd2t2ohlcv&h&e=csv")
    # 備援：Yahoo Finance chart
    show("Yahoo 備援 ^GSPC",
         "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?interval=1d&range=5d")


def probe_fng():
    show("CNN Fear & Greed",
         "https://production.dataviz.cnn.io/index/fearandgreed/graphdata")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    if target in ("twse", "all"):
        probe_twse()
    if target in ("us", "all"):
        probe_us()
    if target in ("fng", "all"):
        probe_fng()
