"""研判命中率回測：讀 public/data/*.json 全部歷史，把「當日 stance」拿去對照
「下一個有資料檔日期」的實際漲跌，算出命中率。輸出 public/data/accuracy.json。

用法：
  python scripts/accuracy.py            # 讀全部歷史、寫 accuracy.json
  build_accuracy() -> dict              # 供 auto_daily 等其他程式呼叫

時間對齊邏輯（重要，先想清楚再比對）：
- 台股：day D 產製時（台北 18:36 後）台股當天已收盤，overview.tw.featured 就是 D 當天的
  真實收盤結果（已發生的事實，不是預測）。所以拿「day D 的 stance」去對照「下一個資料檔」
  （即 D 之後最近一筆有 json 的交易日，因為只有交易日才有檔案，非交易日自然被跳過）的
  台股 change_pct，等於是在檢驗：D 收盤後做出的研判，能不能猜中下一個交易日的漲跌方向。
- 美股：day D 產製當下（台北時間）美股大多還沒開盤或沒收盤，overview.us 裡的 change_pct
  其實是「最新已收盤交易日」的美股數據（詳見 gen_soft_openai.py 的 hard context 註記：
  「美股(最新已收盤交易日...)」）。也就是說 day D 檔案裡存的美股數字，本身也已經是
  「已發生的既定事實」，跟台股同一個道理——所以沿用同一套「跟下一個資料檔比」的規則，
  不需要額外位移一天：用 day D 的 us stance 對照「下一個資料檔」裡的美股 change_pct，
  檢驗的是「這份最新美股收盤資訊所形成的研判，能不能猜中下一批美股收盤（下一個交易日）
  的方向」。兩邊用同一套規則，對齊邏輯一致好維護，不必為美股另外處理位移。
- 美股代表指數：檔案裡 us 是 4 檔（道瓊/標普500/那斯達克/費半），選「標普 500」作為
  大盤代表指數（最常被拿來當美股整體多空基準的指數）。

分類規則：
- stance ∈ {偏多, 中性偏多} → 視為預測「漲」
- stance ∈ {偏空, 中性偏空} → 視為預測「跌」
- stance == 中性（或缺值）  → 不計分，直接跳過
- 實際 change_pct > 0 → 漲；< 0 → 跌；恰好 0（現實中極罕見）→ 方向不明，不計分
"""
import datetime
import json
import pathlib
import re

DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "public" / "data"
OUT_PATH = DATA_DIR / "accuracy.json"
US_INDEX = "標普 500"

_BULL_STANCES = {"偏多", "中性偏多"}
_BEAR_STANCES = {"偏空", "中性偏空"}


def _load_days():
    """讀全部 <YYYY-MM-DD>.json（排除 .partial/.soft/index/notify_state/accuracy 等），依日期排序。"""
    files = sorted(p for p in DATA_DIR.glob("*.json")
                    if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.json", p.name))
    days = []
    for p in files:
        try:
            days.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    days.sort(key=lambda d: d.get("date", ""))
    return days


def _predict(stance):
    if stance in _BULL_STANCES:
        return "up"
    if stance in _BEAR_STANCES:
        return "down"
    return None


def _direction(pct):
    if not isinstance(pct, (int, float)):
        return None
    if pct > 0:
        return "up"
    if pct < 0:
        return "down"
    return None  # 恰好 0：方向不明，不計分


def _tw_pct(day):
    return (day.get("overview", {}).get("tw", {}) or {}).get("featured", {}).get("change_pct")


def _us_pct(day):
    for u in day.get("overview", {}).get("us", []) or []:
        if u.get("name") == US_INDEX:
            return u.get("change_pct")
    return None


def _score(days, stance_fn, pct_fn):
    """逐日比對 stance vs 下一筆資料的實際漲跌，回傳逐日明細（只含有計分的天）。"""
    detail = []
    for i in range(len(days) - 1):  # 最後一天沒有「下一筆」可比，排除
        day, nxt = days[i], days[i + 1]
        pred = _predict(stance_fn(day))
        if pred is None:
            continue
        actual_pct = pct_fn(nxt)
        actual = _direction(actual_pct)
        if actual is None:
            continue
        detail.append({
            "date": day.get("date"),
            "next_date": nxt.get("date"),
            "stance": stance_fn(day),
            "predicted": pred,
            "actual_pct": actual_pct,
            "actual": actual,
            "hit": pred == actual,
        })
    return detail


def _rate(hit, total):
    return round(hit / total * 100, 1) if total else None


def _summarize(detail):
    hit = sum(1 for d in detail if d["hit"])
    total = len(detail)
    recent = detail[-30:]  # 近 30 筆「有計分」的交易日（非日曆 30 天）
    r_hit = sum(1 for d in recent if d["hit"])
    return {
        "hit_rate": _rate(hit, total),
        "hit": hit,
        "total": total,
        "recent30_rate": _rate(r_hit, len(recent)),
        "recent30_total": len(recent),
        "detail": detail,
    }


def build_accuracy() -> dict:
    days = _load_days()
    tw_detail = _score(days, lambda d: (d.get("verdict", {}).get("tw", {}) or {}).get("stance"), _tw_pct)
    us_detail = _score(days, lambda d: (d.get("verdict", {}).get("us", {}) or {}).get("stance"), _us_pct)
    tw = _summarize(tw_detail)
    us = _summarize(us_detail)
    us["index_used"] = US_INDEX
    return {
        "generated_at": datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=8))
        ).strftime("%Y-%m-%d %H:%M"),
        "tw": tw,
        "us": us,
    }


def main():
    acc = build_accuracy()
    OUT_PATH.write_text(json.dumps(acc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"命中率：台股 {acc['tw']['hit_rate']}%（{acc['tw']['hit']}/{acc['tw']['total']}），"
          f"美股 {acc['us']['hit_rate']}%（{acc['us']['hit']}/{acc['us']['total']}），"
          f"已寫入 {OUT_PATH.name}")


if __name__ == "__main__":
    main()
