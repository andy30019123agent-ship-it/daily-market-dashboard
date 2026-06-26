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


# 強多 / 強空字眼：用來抓「新聞方向」與「當日加權方向」明顯矛盾（如大跌日卻說創新高）
_BULL_WORDS = ("創新高", "創高", "歷史新高", "再創高", "收最高", "刷新高", "大漲", "飆漲", "噴出")
_BEAR_WORDS = ("創新低", "歷史新低", "崩跌", "暴跌", "雪崩", "重摔")


def check_news_consistency(day):
    """抓『台股新聞方向』與『當日加權指數方向』明顯矛盾。
    回傳問題清單；非空＝方向矛盾（多半是混進了別天的舊新聞），應擋下不發。
    僅在加權當日漲跌幅明確（>0.5%）且新聞含『台股/加權』時才判定，避免誤殺。"""
    errs = []
    pct = ((day.get("overview", {}) or {}).get("tw", {}) or {}).get("featured", {}).get("change_pct")
    if pct is None:
        return errs
    for n in day.get("news", []) or []:
        if not isinstance(n, dict):
            continue
        blob = f"{n.get('title', '')} {n.get('impact', '')}"
        if "台股" not in blob and "加權" not in blob:
            continue  # 只比對台股相關新聞 vs 加權方向
        title = (n.get("title", "") or "")[:16]
        if pct < -0.5 and any(w in blob for w in _BULL_WORDS):
            errs.append(f"加權當日下跌({pct}%)，台股新聞卻稱「{title}…」(強多字眼)，方向矛盾")
        if pct > 0.5 and any(w in blob for w in _BEAR_WORDS):
            errs.append(f"加權當日上漲({pct}%)，台股新聞卻稱「{title}…」(強空字眼)，方向矛盾")
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
