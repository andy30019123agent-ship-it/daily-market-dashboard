"""財經行事曆輔助：提供可確定計算的重大日期（四巫日）。

其餘浮動日期（FOMC、CPI、非農、台積電法說）由分身每日 WebSearch 確認，
本模組只負責「演算法可確定」的部分，避免寫死過時資料。
"""
import datetime


def third_friday(year: int, month: int) -> datetime.date:
    """該月第 3 個週五。"""
    d = datetime.date(year, month, 1)
    # weekday(): Mon=0..Sun=6；Fri=4
    offset = (4 - d.weekday()) % 7
    first_friday = d + datetime.timedelta(days=offset)
    return first_friday + datetime.timedelta(days=14)


def is_quadruple_witching(d: datetime.date) -> bool:
    """四巫日＝3/6/9/12 月的第 3 個週五（股指期權、個股期權同時結算）。"""
    return d.month in (3, 6, 9, 12) and d == third_friday(d.year, d.month)


def upcoming_known(today: datetime.date, days_ahead: int = 7) -> list:
    """回傳未來 days_ahead 天內、可確定計算的重大日（目前：四巫日）。"""
    out = []
    for i in range(days_ahead + 1):
        d = today + datetime.timedelta(days=i)
        if is_quadruple_witching(d):
            out.append({"date": d.isoformat(), "name": "四巫日（三巫到期）",
                        "analysis": "股指期貨、股指選擇權、個股選擇權同時結算，盤中波動可能放大"})
    return out
