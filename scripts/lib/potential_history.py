"""低基期潛力股進榜歷史與發動偵測（純函式，不做 IO）。

history 結構：
  {"last_date": "YYYY-MM-DD" | None,
   "stocks": {code: {name, streak, first_date, last_date, last_score, alerted_date?}}}
"""
from __future__ import annotations

import datetime as _dt


def update_history(history: dict, today_stocks: list[dict], date: str) -> dict:
    """更新進榜歷史：今日在榜且上次也在榜→streak+1，否則 streak=1、first_date=date。
    同一 date 重覆呼叫為冪等（不重覆累加）。回傳新 history。"""
    prev_date = (history or {}).get("last_date")
    stocks = dict((history or {}).get("stocks") or {})
    if date == prev_date:
        return {"last_date": date, "stocks": stocks}  # 同日冪等
    for s in today_stocks:
        code = s.get("code")
        if not code:
            continue
        rec = stocks.get(code)
        if rec and rec.get("last_date") == prev_date:
            rec = {**rec, "streak": rec.get("streak", 0) + 1}
        else:
            rec = {"name": s.get("name"), "streak": 1, "first_date": date}
        rec["name"] = s.get("name") or rec.get("name")
        rec["last_date"] = date
        rec["last_score"] = s.get("score")
        # 保留子分（前瞻追蹤用）：日後可對照真實報酬，驗證權重是否有效
        if s.get("score_parts"):
            rec["last_parts"] = s.get("score_parts")
        stocks[code] = rec
    return {"last_date": date, "stocks": stocks}


def _within(days_str: str, date: str, n: int) -> bool:
    try:
        a = _dt.date.fromisoformat(days_str)
        b = _dt.date.fromisoformat(date)
        return 0 <= (b - a).days <= n
    except Exception:
        return False


def detect_breakouts(history: dict, radar_stocks: list[dict], date: str,
                     cfg: dict) -> list[dict]:
    """近 track_days 內曾在榜、且今日漲幅 ≥ breakout_pct 的股＝發動；同一波只提醒一次。
    原地在 history.stocks[code] 標記 alerted_date（呼叫端負責存檔）。"""
    stocks = (history or {}).get("stocks") or {}
    by_code = {s.get("code"): s for s in radar_stocks}
    out = []
    for code, rec in stocks.items():
        if not _within(rec.get("last_date", ""), date, cfg["track_days"]):
            continue
        if rec.get("alerted_date") == date:
            continue
        q = by_code.get(code)
        if q and (q.get("pct") or 0) >= cfg["breakout_pct"]:
            rec["alerted_date"] = date
            out.append({"code": code, "name": rec.get("name"), "pct": q.get("pct")})
    return out
