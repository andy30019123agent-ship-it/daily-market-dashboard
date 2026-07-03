"""低基期潛力雷達：籌碼近N日聚合 → 吸籌候選 → FinMind 低基期 → 組裝。

此模組獨立於主戰報，呼叫端須自行 try/except，失敗不得影響主報告。
"""
from __future__ import annotations

import datetime as _dt
import json
import time
import urllib.request

DEFAULTS = {
    "window": 10,       # 籌碼累積天數（由 5 拉長，看得出趨勢）
    "inst_min_yi": 0.5, # 近N日法人淨買超門檻（億）。放低才抓得到「小量、悄悄」的吸籌
    "pct_max": 3.0,     # 當日/最新漲幅上限（%），還沒起漲
    "cand_max": 80,     # 吸籌候選上限。放大才不會被大買熱門股佔滿、擠掉低基期名單
    "pos_max": 0.40,    # 低基期 gate：股價位置上限（0~1，越低越低基期）
    "chip_sat": 5.0,    # 淨買超飽和點（億）
    "vol_hi": 1.8,      # 量增給滿倍數
    "pos_ref": 0.5,     # 位置分基準
    "score_min": 40,    # 進榜分數下限
    "w_chip": 0.35, "w_struct": 0.40, "w_theme": 0.25,  # Phase A 權重（可調）
}

FINMIND_API = "https://api.finmindtrade.com/api/v4/data"


def aggregate_chips(days: list[dict], window: int) -> dict[str, dict]:
    """days 由舊到新；取最後 window 天，法人淨買超加總、買超天數計數、其餘欄位取最新。"""
    recent = [d for d in days if d][-window:]
    agg: dict[str, dict] = {}
    for d in recent:
        for s in d.get("stocks", []):
            code = s.get("code")
            if not code:
                continue
            a = agg.setdefault(code, {"code": code, "inst_net_yi": 0.0, "buy_days": 0})
            net = s.get("inst_net_yi") or 0
            a["inst_net_yi"] = round(a["inst_net_yi"] + net, 2)
            if net > 0:
                a["buy_days"] += 1
            a["name"] = s.get("name")
            a["pct"] = s.get("pct")
            a["value_yi"] = s.get("value_yi")
            a["sector"] = s.get("sector")
    return agg


def pick_accumulators(agg: dict, inst_min_yi: float, pct_max: float,
                      cand_max: int) -> list[dict]:
    cands = [
        s for s in agg.values()
        if (s.get("inst_net_yi") or 0) >= inst_min_yi
        and (s.get("pct") if s.get("pct") is not None else 999) <= pct_max
    ]
    cands.sort(key=lambda s: s["inst_net_yi"], reverse=True)
    return cands[:cand_max]


def low_base_metrics(rows: list[dict]) -> dict | None:
    """rows：FinMind 日 K（由舊到新，含 date/close/max/min）。回低基期指標或 None。"""
    rows = [r for r in rows if r.get("close") is not None][-260:]
    if len(rows) < 20:
        return None
    highs = [r["max"] for r in rows if r.get("max") is not None]
    lows = [r["min"] for r in rows if r.get("min") is not None]
    if not highs or not lows:
        return None
    hi, lo = max(highs), min(lows)
    if hi == lo:
        return None
    close = rows[-1]["close"]
    price_pos = round((close - lo) / (hi - lo), 3)

    def _d(s):
        try:
            return _dt.date.fromisoformat(s)
        except Exception:
            return None

    last_d = _d(rows[-1]["date"])
    ref = None
    if last_d:
        target = last_d - _dt.timedelta(days=182)
        ref = min(
            (r for r in rows if _d(r["date"])),
            key=lambda r: abs((_d(r["date"]) - target).days),
            default=None,
        )
    base = ref["close"] if ref and ref["close"] else rows[0]["close"]
    chg_6m = round(close / base - 1, 4) if base else 0.0

    # 量能比：近5日均量 / 前20日均量（缺量或分母 0 時給 1.0 中性）
    vols = [r.get("Trading_Volume") for r in rows
            if isinstance(r.get("Trading_Volume"), (int, float))]
    vol_ratio = 1.0
    if len(vols) >= 25:
        recent5 = sum(vols[-5:]) / 5
        prev20 = sum(vols[-25:-5]) / 20
        vol_ratio = round(recent5 / prev20, 2) if prev20 else 1.0

    # 站上季線：收盤 ≥ 近60日均價
    closes = [r["close"] for r in rows if r.get("close") is not None]
    ma60 = sum(closes[-60:]) / len(closes[-60:]) if len(closes) >= 20 else close
    above_ma60 = close >= ma60

    # 走勢縮圖：收盤序列降採樣至 ≤52 點、保底含最後一點
    step = max(1, (len(closes) + 51) // 52)
    spark = closes[::step]
    if spark[-1] != closes[-1]:
        spark.append(closes[-1])

    return {"price_pos": price_pos, "chg_6m": chg_6m,
            "vol_ratio": vol_ratio, "above_ma60": above_ma60,
            "spark": [round(c, 2) for c in spark]}


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def chip_score(cand: dict, window: int, chip_sat: float = 5.0) -> float:
    """籌碼分：淨買超金額（飽和）0.6 + 買超天數佔比 0.4。"""
    amount = _clamp01((cand.get("inst_net_yi") or 0) / chip_sat)
    persistence = _clamp01((cand.get("buy_days") or 0) / max(1, window))
    return round(0.6 * amount + 0.4 * persistence, 3)


def structure_score(metrics: dict, vol_hi: float = 1.8, pos_ref: float = 0.5) -> float:
    """價量結構分：位置低 0.4 + 量增 0.4 + 站季線 0.2。落難股（無量、破季線）分低。"""
    pos_comp = _clamp01(1 - (metrics.get("price_pos") or 1) / pos_ref)
    vol_comp = _clamp01(((metrics.get("vol_ratio") or 1) - 0.8) / (vol_hi - 0.8))
    ma_comp = 1.0 if metrics.get("above_ma60") else 0.0
    return round(0.4 * pos_comp + 0.4 * vol_comp + 0.2 * ma_comp, 3)


def finmind_history(code: str, start_date: str) -> list[dict]:
    """打 FinMind TaiwanStockPrice；任何錯誤回 []（不拋例外）。"""
    url = (f"{FINMIND_API}?dataset=TaiwanStockPrice"
           f"&data_id={code}&start_date={start_date}")
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.load(r)
        return data.get("data") or []
    except Exception:
        return []


def filter_low_base(cands: list[dict], start_date: str, pos_max: float,
                    chg6m_max: float, fetch=finmind_history,
                    sleep_s: float = 0.3) -> list[dict]:
    out = []
    for c in cands:
        rows = fetch(c["code"], start_date)
        if sleep_s:
            time.sleep(sleep_s)
        if not rows:
            continue
        m = low_base_metrics(rows)
        if not m:
            continue
        if m["price_pos"] <= pos_max and m["chg_6m"] <= chg6m_max:
            out.append({**c, **m, "history": "ok"})
    return out


def build_potential(days: list[dict], start_date: str, cfg: dict | None = None,
                    fetch=finmind_history, sleep_s: float = 0.3) -> dict:
    cfg = {**DEFAULTS, **(cfg or {})}
    agg = aggregate_chips(days, cfg["window"])
    cands = pick_accumulators(agg, cfg["inst_min_yi"], cfg["pct_max"],
                              cfg["cand_max"])
    stocks = filter_low_base(cands, start_date, cfg["pos_max"], cfg["chg6m_max"],
                             fetch=fetch, sleep_s=sleep_s)
    return {"window_days": cfg["window"], "stocks": stocks}
