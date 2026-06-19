"""把硬數據（fetch_hard_data 的 partial）與軟情報（分身產出）合併成符合 schema 的完整當日 JSON，並更新日期索引。

merge_day(partial, soft, date, updated_at) -> dict
update_index(date) -> None
"""
import json
import pathlib

DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "public" / "data"
INDEX_PATH = DATA_DIR / "index.json"


def merge_day(partial: dict, soft: dict, date: str, updated_at: str = "") -> dict:
    """硬數據優先帶入指數/VIX 數值，軟情報補上文字解讀與缺口。"""
    pov = partial.get("overview", {})
    sov = soft.get("overview", {})

    # 台股子數據：硬數據（成交金額）+ 軟情報（櫃買、外資）依 soft 指定順序
    tw_stats = soft.get("tw_stats")
    if tw_stats is None:
        tw_stats = pov.get("tw", {}).get("stats", [])

    # 美股：硬數據三大指數 + 軟情報補費半 SOX
    us = list(pov.get("us", []))
    if soft.get("us_sox"):
        us.append(soft["us_sox"])

    # VIX：美股用硬數據數值 + 軟情報文字；台股全來自軟情報
    vix_us = pov.get("vix", {}).get("us") or {}
    if soft.get("vix_us"):
        vix_us = {**vix_us, **soft["vix_us"]}

    # 熱門股：硬數據（漲幅榜）補上軟情報的「緣由」
    hot_tw = list(partial.get("hot_stocks", {}).get("tw", []))
    reasons = soft.get("hot_tw_reasons", {})
    for s in hot_tw:
        if not s.get("reason"):
            s["reason"] = reasons.get(s["code"], "")

    return {
        "date": date,
        "updated_at": updated_at or partial.get("_meta", {}).get("fetched_at", date),
        "overview": {
            "tw": {"featured": pov.get("tw", {}).get("featured"), "stats": tw_stats},
            "us": us,
            "vix": {"tw": soft.get("vix_tw"), "us": vix_us},
        },
        "sectors": {
            # 台股類股用硬數據（真實漲跌幅）；美股仍由軟情報補
            "tw": partial.get("sectors_tw") or soft.get("sectors", {}).get("tw", {"in": [], "out": []}),
            "us": partial.get("sectors_us") or soft.get("sectors", {}).get("us", {"in": [], "out": []}),
        },
        "hot_stocks": {
            "tw": hot_tw,
            # 美股熱門用硬數據（AV 重點股動向）；無則退軟情報
            "us": partial.get("hot_stocks", {}).get("us") or soft.get("hot_us", []),
        },
        "inst_top": partial.get("inst_top", {"foreign": [], "trust": [], "dealer": []}),
        "news": soft.get("news", []),
        "upcoming_events": soft.get("upcoming_events", []),
        "past_events_review": soft.get("past_events_review", []),
        "verdict": soft.get("verdict", {
            "tw": {"bullish": [], "bearish": [], "risks": []},
            "us": {"bullish": [], "bearish": [], "risks": []},
        }),
        "summary": soft.get("summary", ""),
    }


def update_index(date: str) -> None:
    dates = []
    if INDEX_PATH.exists():
        dates = json.loads(INDEX_PATH.read_text(encoding="utf-8")).get("dates", [])
    if date not in dates:
        dates.append(date)
    INDEX_PATH.write_text(
        json.dumps({"dates": sorted(set(dates))}, ensure_ascii=False) + "\n", encoding="utf-8"
    )
