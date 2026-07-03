"""市場紅綠燈（元件 A）：規則計分純函式。

規則門檻依設計規格 `股票投顧方案_設計規格_2026-07-03.md` 元件 A，全部集中在本檔常數區，
若要微調規則一律改這裡（並同步回規格文件），不要散落魔術數字。

    趨勢：TAIEX 收盤 > MA20（+1）、MA20 > MA60（+1）、收盤 > MA60（+1）
    寬度：上漲家數/(上漲+下跌) > 55%（+1）、< 45%（−1）
    波動：台指 VIX < 20（+1）、> 28（−1）
    籌碼：三大法人近 5 日合計淨買超 > 0（+1）、< 0（−1）
    總分 ≥3 → 🟢 green、0~2 → 🟡 yellow、<0 → 🔴 red

全部函式為純函式（不發網路請求、不讀檔）：呼叫端（如 auto_daily.py）負責把台股收盤序列、
市場寬度、VIX、三大法人歷史從既有資料聚合好再傳進來。任何分項資料缺失 → 該項記 0 分、
components 裡標 missing=True，不丟例外（規格：不炸）。

compute_regime(closes, breadth, vix_tw, chips_entries) -> {light, score, components}
"""
from __future__ import annotations

# ---- 規則門檻常數（可調，調整請同步規格文件）----
MA_SHORT = 20          # 短均線天數
MA_LONG = 60           # 長均線天數
BREADTH_BULL = 0.55    # 上漲家數佔比門檻（多）
BREADTH_BEAR = 0.45    # 上漲家數佔比門檻（空）
VIX_BULL = 20          # 台指 VIX 低於此值視為波動偏低（多）
VIX_BEAR = 28          # 台指 VIX 高於此值視為波動偏高（空）
CHIPS_WINDOW = 5       # 三大法人合計淨買超回顧天數
GREEN_MIN = 3          # 總分門檻：>= 此值 綠燈
# 0~2 分黃燈；< 0 分（即 <= -1）紅燈


def sma(closes: list, n: int):
    """簡單移動平均；資料不足 n 天回 None。closes 需由舊到新排序，最後一筆為最新。"""
    if not closes or len(closes) < n:
        return None
    window = [c for c in closes[-n:] if isinstance(c, (int, float))]
    if len(window) < n:
        return None
    return sum(window) / n


def score_trend(closes: list) -> dict:
    """趨勢三分項：收盤>MA20、MA20>MA60、收盤>MA60。closes 由舊到新，最後一筆為最新收盤。"""
    if not closes:
        return {"score": 0, "missing": True, "detail": {}}
    close = closes[-1]
    ma20 = sma(closes, MA_SHORT)
    ma60 = sma(closes, MA_LONG)
    detail = {"close": close, "ma20": ma20, "ma60": ma60}
    if not isinstance(close, (int, float)) or ma20 is None or ma60 is None:
        detail["days_available"] = len(closes)
        return {"score": 0, "missing": True, "detail": detail}
    score = 0
    if close > ma20:
        score += 1
    if ma20 > ma60:
        score += 1
    if close > ma60:
        score += 1
    detail.update({
        "close_gt_ma20": close > ma20,
        "ma20_gt_ma60": ma20 > ma60,
        "close_gt_ma60": close > ma60,
    })
    return {"score": score, "missing": False, "detail": detail}


def score_breadth(breadth: dict | None) -> dict:
    """市場寬度：上漲家數佔比。breadth = {"up":.., "down":.., ...}（見 schema）。"""
    up = (breadth or {}).get("up")
    down = (breadth or {}).get("down")
    if not isinstance(up, (int, float)) or not isinstance(down, (int, float)) or (up + down) <= 0:
        return {"score": 0, "missing": True, "detail": {}}
    ratio = up / (up + down)
    score = 1 if ratio > BREADTH_BULL else (-1 if ratio < BREADTH_BEAR else 0)
    return {"score": score, "missing": False,
            "detail": {"ratio": round(ratio, 4), "up": up, "down": down}}


def score_vix(vix_tw: dict | None) -> dict:
    """波動：台指 VIX 數值。vix_tw = {"value": .., ...}。"""
    v = (vix_tw or {}).get("value")
    if not isinstance(v, (int, float)):
        return {"score": 0, "missing": True, "detail": {}}
    score = 1 if v < VIX_BULL else (-1 if v > VIX_BEAR else 0)
    return {"score": score, "missing": False, "detail": {"value": v}}


def net_yi_sum(entry: dict | None):
    """單日三大法人淨買超合計（億）：entry = {"外資":x,"投信":y,"自營":z}（來自 inst_net_yi）。
    entry 為 None 或全無數值 → None（該天無可用資料）。"""
    if not entry:
        return None
    vals = [entry.get(k) for k in ("外資", "投信", "自營")]
    vals = [v for v in vals if isinstance(v, (int, float))]
    if not vals:
        return None
    return sum(vals)


def aggregate_recent_chips(entries: list, n: int = CHIPS_WINDOW):
    """近 n 個交易日三大法人淨買超合計。entries 由舊到新（可能含 None/缺值天），
    取最後 n 筆中「有資料」的加總；回 (net_yi 或 None, 實際採用天數)。"""
    sums = [s for s in (net_yi_sum(e) for e in (entries or [])[-n:]) if s is not None]
    if not sums:
        return None, 0
    return round(sum(sums), 1), len(sums)


def score_chips(entries: list, n: int = CHIPS_WINDOW) -> dict:
    """籌碼：三大法人近 n 日合計淨買超（entries 由舊到新，見 aggregate_recent_chips）。"""
    net_yi, days_used = aggregate_recent_chips(entries, n)
    if net_yi is None:
        return {"score": 0, "missing": True, "detail": {"days_used": days_used}}
    score = 1 if net_yi > 0 else (-1 if net_yi < 0 else 0)
    return {"score": score, "missing": False,
            "detail": {"net_yi": net_yi, "days_used": days_used}}


def compute_regime(closes: list, breadth: dict | None, vix_tw: dict | None,
                    chips_entries: list) -> dict:
    """組出市場紅綠燈總結果。

    closes: 台股加權收盤序列，由舊到新排序，最後一筆為最新一日收盤。
    breadth: 當日市場寬度 {"up":.., "down":..}（見 schema，可能為 None）。
    vix_tw: 當日台指 VIX {"value":..}（可能為 None）。
    chips_entries: 近幾個交易日的三大法人淨買超（每筆 {"外資":..,"投信":..,"自營":..}
                   或 None），由舊到新排序、含當日。
    """
    trend = score_trend(closes)
    breadth_c = score_breadth(breadth)
    vix_c = score_vix(vix_tw)
    chips_c = score_chips(chips_entries)
    total = trend["score"] + breadth_c["score"] + vix_c["score"] + chips_c["score"]
    if total >= GREEN_MIN:
        light = "green"
    elif total < 0:
        light = "red"
    else:
        light = "yellow"
    return {
        "light": light,
        "score": total,
        "components": {
            "trend": trend,
            "breadth": breadth_c,
            "vix": vix_c,
            "chips": chips_c,
        },
    }
