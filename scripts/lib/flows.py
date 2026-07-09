"""資金流衍生指標（純函式，方便單元測試；同 regime.py / potential.py 慣例）。

目前提供：
- inst_flow_streaks：三大法人「連續買超／賣超天數」，判斷資金是否有持續性方向。
"""

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
