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
