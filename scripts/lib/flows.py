"""資金流衍生指標（純函式，方便單元測試；同 regime.py / potential.py 慣例）。

目前提供：
- inst_flow_streaks：三大法人「連續買超／賣超天數」，判斷資金是否有持續性方向。
- buy_concentration：法人買超集中度（前 N 大佔全市場買超比重）。
"""
from __future__ import annotations

INSTS = ("外資", "投信", "自營")


def inst_flow_streaks(daily_nets: list[dict]) -> dict:
    """三大法人各自的「連續同方向天數」。

    daily_nets：由舊到新排列，每元素形如 {"外資": -255.0, "投信": 69.1, "自營": -97.2}
    （單位億元，即各日檔的 inst_net_yi）。

    回 {inst: {"streak": n, "side": "buy"|"sell"|None, "today_yi": x|None}}，
    streak＝從最近一天往回數、方向不變（且非 0）的連續天數；遇到 0/缺值/反向即停。
    """
    out = {}
    for inst in INSTS:
        vals = [d.get(inst) for d in daily_nets]
        streak, side = 0, None
        for v in reversed(vals):
            if not isinstance(v, (int, float)) or v == 0:
                break
            s = "buy" if v > 0 else "sell"
            if side is None:
                side, streak = s, 1
            elif s == side:
                streak += 1
            else:
                break
        out[inst] = {"streak": streak, "side": side,
                     "today_yi": vals[-1] if vals else None}
    return out


def buy_concentration(stocks: list[dict], top_n: int = 10) -> dict | None:
    """法人買超集中度：前 N 大買超個股的法人淨買超金額 ÷ 全部買超個股合計。

    stocks：radar.stocks（每檔含 inst_net_yi，單位億元）。
    ratio 高＝買盤集中在少數個股（多為權值股撐盤）、低＝廣泛買盤。
    回 {"top_yi", "total_yi", "ratio"(%), "n"}；無任何買超時回 None。
    """
    buys = sorted(
        (s["inst_net_yi"] for s in (stocks or [])
         if isinstance(s.get("inst_net_yi"), (int, float)) and s["inst_net_yi"] > 0),
        reverse=True,
    )
    total = sum(buys)
    if total <= 0:
        return None
    top = sum(buys[:top_n])
    return {"top_yi": round(top, 1), "total_yi": round(total, 1),
            "ratio": round(top / total * 100), "n": min(top_n, len(buys))}


def volume_anomalies(today_stocks, hist_value_by_code, *,
                     min_ratio=2.0, min_days=3, min_value_yi=2.0, top=8):
    """今日成交值相對近期均值明顯放大的個股（爆量）。

    today_stocks：今日 radar.stocks（含 code/name/value_yi/pct）。
    hist_value_by_code：{code: [過去各日 value_yi]}（不含今日）。
    ratio = 今日成交值 ÷ 近期均值；>= min_ratio 才算爆量。
    direction：up=價漲量增(轉強)、down=價跌量增(出貨/恐慌)、flat=量增價平。
    回依 ratio 由高到低、限 top 檔。
    """
    out = []
    for s in today_stocks or []:
        code, v, pct = s.get("code"), s.get("value_yi"), s.get("pct")
        if not code or not isinstance(v, (int, float)) or v < min_value_yi:
            continue
        hist = [h for h in hist_value_by_code.get(code, [])
                if isinstance(h, (int, float)) and h > 0]
        if len(hist) < min_days:
            continue
        avg = sum(hist) / len(hist)
        if avg <= 0:
            continue
        ratio = v / avg
        if ratio < min_ratio:
            continue
        direction = ("up" if isinstance(pct, (int, float)) and pct > 0.5
                     else "down" if isinstance(pct, (int, float)) and pct < -0.5
                     else "flat")
        out.append({"code": code, "name": s.get("name"), "ratio": round(ratio, 1),
                    "pct": pct, "value_yi": round(v, 1), "direction": direction})
    out.sort(key=lambda x: x["ratio"], reverse=True)
    return out[:top]


def trend_signal_backtest(closes, horizon=5, ma_period=20):
    """回測「加權收盤 vs MA」趨勢訊號的 N 日後方向命中率（紅綠燈的趨勢分邏輯）。

    closes：由舊到新的收盤價 list。對每個有足夠歷史且有 horizon 日後資料的點：
    站上均線→看多、跌破→看空；命中＝N 日後收盤方向與訊號一致（平盤不計）。
    回 {total, hit, rate(%), horizon, ma}；樣本不足回 None。
    """
    vals = [c for c in closes if isinstance(c, (int, float))]
    n = len(vals)
    if n < ma_period + horizon:
        return None
    total = hit = 0
    for i in range(ma_period - 1, n - horizon):
        ma = sum(vals[i - ma_period + 1:i + 1]) / ma_period
        sig = 1 if vals[i] > ma else -1
        fwd = vals[i + horizon] - vals[i]
        if fwd == 0:
            continue
        total += 1
        if (sig > 0 and fwd > 0) or (sig < 0 and fwd < 0):
            hit += 1
    if total == 0:
        return None
    return {"total": total, "hit": hit, "rate": round(hit / total * 100, 1),
            "horizon": horizon, "ma": ma_period}
