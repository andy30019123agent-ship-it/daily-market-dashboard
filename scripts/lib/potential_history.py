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
        stocks[code] = rec
    return {"last_date": date, "stocks": stocks}
