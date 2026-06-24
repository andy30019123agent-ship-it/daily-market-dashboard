"""發布前防護（2026-06-24 加，源於漲跌符號反向事故）。

兩層、分級處理：
- check_consistency(day)：抓「自相矛盾」的硬錯誤（如漲跌點數與漲跌幅正負不一致）。
  非空＝資料壞掉，呼叫端應擋下不發布並發失敗通知。
- collect_warnings(day)：盤點「缺漏」（某區塊抓不到）。資料沒壞、照常發布，
  但要在推播明示「今日缺」，避免靜默空白讓人誤以為正常。
"""


def _same_sign(a, b):
    """兩值是否同號（任一為 0 視為相容、不算矛盾）。"""
    if a is None or b is None or a == 0 or b == 0:
        return True
    return (a > 0) == (b > 0)


def check_consistency(day):
    """回傳一致性問題清單；非空＝資料自相矛盾，應擋下不發布。"""
    errs = []
    ov = day.get("overview", {}) or {}
    tw = (ov.get("tw", {}) or {}).get("featured") or {}
    chg, pct, close = tw.get("change"), tw.get("change_pct"), tw.get("close")
    spark = tw.get("spark") or []

    # 1) 漲跌點數與漲跌幅正負必須一致（本次事故的攔截點）
    if not _same_sign(chg, pct):
        errs.append(f"台股加權：漲跌點數({chg})與漲跌幅({pct}%)正負不一致")

    # 2) 由收盤走勢推算的漲跌幅，方向需與宣稱漲跌幅一致
    if pct is not None and len(spark) >= 2 and spark[-1] and spark[-2]:
        calc = round((spark[-1] - spark[-2]) / spark[-2] * 100, 2)
        if not _same_sign(calc, pct) and abs(calc) > 0.05 and abs(pct) > 0.05:
            errs.append(f"台股加權：宣稱漲跌幅({pct}%)與走勢推算({calc}%)方向相反")

    # 3) 收盤 − 漲跌點數 ≈ 前一日收盤（容差 1%）
    if close is not None and chg is not None and len(spark) >= 2 and spark[-2]:
        implied_prev = round(close - chg, 2)
        if abs(implied_prev - spark[-2]) > max(2.0, abs(spark[-2]) * 0.01):
            errs.append(
                f"台股加權：收盤({close})−漲跌({chg})={implied_prev} 與前日收盤({spark[-2]})不符"
            )
    return errs


def collect_warnings(day):
    """回傳「缺漏」項目清單（照常發布、但要在推播明示）。"""
    warns = []
    ov = day.get("overview", {}) or {}
    tw = ov.get("tw", {}) or {}
    if not (tw.get("featured") or {}).get("close"):
        warns.append("台股加權指數")
    hot = day.get("hot_stocks", {})
    if isinstance(hot, dict) and not hot.get("tw"):
        warns.append("台股熱門個股")
    sectors_tw = (day.get("sectors", {}) or {}).get("tw", {}) or {}
    if not sectors_tw.get("in"):
        warns.append("台股類股資金流向")
    if len(ov.get("us", []) or []) < 4:
        warns.append("美股指數")
    return warns
