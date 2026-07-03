"""台股加權指數（TAIEX）歷史收盤序列，供 regime.py 算 MA20/MA60 用。

既有每日 day.json 只從 2026-06-18 起（不足 60 個交易日），另存一份獨立的輕量歷史檔
`public/data/index-history.json`（只存 date/close，不隨每日 day.json 增肥）：

    { "history": [ {"date": "2026-01-05", "close": 44120.3}, ... ] }   // 由舊到新

- 回填：`fetch_taiex_month` 用 TWSE 官方 RWD `afterTrading/FMTQIK` 端點——同一支端點只要帶
  月份中任一天的 date 參數，就會回傳「整個月」的每日 TAIEX 收盤（fetch_hard_data.py 抓當日
  spark 走勢已在用這支端點，此處延伸取全部列、不只取最後 N 筆）。逐月往回抓即可湊出所需交易日數，
  比逐日一支請求快很多、對 TWSE 也禮貌。
- 每日流程：抓到當日收盤後呼叫 `merge_entries` 把當天併入（已存在同日期就覆蓋，不重複）。
- 抓失敗一律不拋例外中斷主流程（呼叫端 try/except），沿用既有歷史檔即可。
"""
from __future__ import annotations

import datetime
import json
import pathlib
import time

HISTORY_PATH = pathlib.Path(__file__).resolve().parents[2] / "public" / "data" / "index-history.json"

# 保留筆數上限（交易日）：MA60 只需 60 筆，多留一些餘裕供未來擴充用、避免檔案無限長大。
MAX_ENTRIES = 300


def load_history(path: pathlib.Path = HISTORY_PATH) -> list[dict]:
    """讀歷史檔；不存在或壞掉一律回空清單（不拋例外，呼叫端不用另外 try/except）。"""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        h = data.get("history", [])
        return h if isinstance(h, list) else []
    except Exception:
        return []


def save_history(history: list[dict], path: pathlib.Path = HISTORY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"history": history}, ensure_ascii=False, indent=1), encoding="utf-8")


def merge_entries(history: list[dict], new_entries: list[dict], max_entries: int = MAX_ENTRIES) -> list[dict]:
    """依 date 去重合併（新值覆蓋舊值，同日期取後到者），依日期排序後只留最近 max_entries 筆。"""
    by_date = {}
    for e in list(history) + list(new_entries):
        d = e.get("date")
        c = e.get("close")
        if not d or not isinstance(c, (int, float)):
            continue
        by_date[d] = {"date": d, "close": c}
    out = [by_date[d] for d in sorted(by_date)]
    return out[-max_entries:] if max_entries else out


def parse_fmtqik_month(payload: dict) -> list[dict]:
    """解析 RWD FMTQIK 回應的整個月列 -> [{"date": ISO, "close": float}, ...]（由舊到新）。

    與 parsers.parse_rwd_fmtqik 不同：這裡要「整個月全部列」（回填用），
    parse_rwd_fmtqik 是取「最後 spark_n 筆」給每日走勢圖用，用途不同故獨立實作，不动既有函式。
    """
    fields = payload.get("fields", [])
    rows = payload.get("data", [])

    def _col(keys):
        for i, f in enumerate(fields):
            if any(k in f for k in keys):
                return i
        return None

    ci_date = _col(["日期"])
    ci_idx = _col(["發行量加權股價指數"])
    if ci_date is None or ci_idx is None:
        return []
    out = []
    for r in rows:
        try:
            raw_date = str(r[ci_date]).strip()
            y, m, d = raw_date.split("/")
            iso = f"{int(y) + 1911:04d}-{int(m):02d}-{int(d):02d}"
        except Exception:
            continue
        try:
            close = float(str(r[ci_idx]).replace(",", ""))
        except (TypeError, ValueError):
            continue
        out.append({"date": iso, "close": close})
    return out


def _months_back(n: int, from_date: datetime.date | None = None) -> list[str]:
    """回傳 [from_date 所在月, 往前 1 個月, ..., 共 n 個]，格式 YYYYMM01（FMTQIK date 參數）。"""
    base = from_date or datetime.date.today()
    out = []
    y, m = base.year, base.month
    for _ in range(n):
        out.append(f"{y}{m:02d}01")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return out


def backfill(get_json_fn, months_back: int = 8,
             sleep_s: float = 0.5, from_date: datetime.date | None = None) -> list[dict]:
    """逐月往回抓 FMTQIK 共 months_back 個月（每月約 20 個交易日，預設 8 個月 ≈ 130+ 個交易日，
    滿足 MA60 需求並留餘裕）。

    get_json_fn(url) -> dict：注入抓取函式，方便單元測試不真的發網路請求。
    """
    entries: dict[str, dict] = {}
    for ymd in _months_back(months_back, from_date):
        try:
            url = f"https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK?date={ymd}&response=json"
            payload = get_json_fn(url)
            for e in parse_fmtqik_month(payload):
                entries[e["date"]] = e
        except Exception:
            continue  # 單月抓失敗不影響其他月份，盡量湊出能拿到的部分
        if sleep_s:
            time.sleep(sleep_s)
    # min_days 只用來決定 months_back 該抓多少個月（呼叫端可視需要調大 months_back），
    # 這裡不做提早中止判斷：月初/假日多的月份交易日較少，抓完排定的月份份數最穩妥。
    return sorted(entries.values(), key=lambda e: e["date"])
