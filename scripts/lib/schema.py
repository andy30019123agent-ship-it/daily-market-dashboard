"""當日資料 schema 驗證（對齊 v2 設計）。

validate_day(data) -> list[str]：回傳錯誤訊息清單，空清單代表通過。
"""

REQUIRED = [
    "date", "updated_at", "overview", "sectors", "hot_stocks",
    "news", "upcoming_events", "past_events_review", "verdict", "summary",
]


def validate_day(data: dict) -> list[str]:
    errs = [f"缺少欄位 {k}" for k in REQUIRED if k not in data]

    ov = data.get("overview")
    if isinstance(ov, dict):
        for k in ("tw", "us", "vix"):
            if k not in ov:
                errs.append(f"overview 缺少 {k}")
        tw = ov.get("tw")
        if isinstance(tw, dict):
            if "featured" not in tw:
                errs.append("overview.tw 缺少 featured")
            if "stats" not in tw:
                errs.append("overview.tw 缺少 stats")
        if "us" in ov and not isinstance(ov["us"], list):
            errs.append("overview.us 應為陣列")
        vix = ov.get("vix")
        if isinstance(vix, dict):
            for k in ("tw", "us"):
                if k not in vix:
                    errs.append(f"overview.vix 缺少 {k}")
    elif ov is not None:
        errs.append("overview 應為物件")

    sec = data.get("sectors")
    if isinstance(sec, dict):
        for mkt in ("tw", "us"):
            m = sec.get(mkt)
            if not isinstance(m, dict):
                errs.append(f"sectors.{mkt} 缺少或型別錯誤")
                continue
            for side in ("in", "out"):
                if side not in m:
                    errs.append(f"sectors.{mkt} 缺少 {side}")

    hs = data.get("hot_stocks")
    if isinstance(hs, dict):
        for mkt in ("tw", "us"):
            if mkt not in hs:
                errs.append(f"hot_stocks 缺少 {mkt}")

    vd = data.get("verdict")
    if isinstance(vd, dict):
        # 新版台美分列 {tw, us}；相容舊版單一
        markets = [vd.get("tw"), vd.get("us")] if ("tw" in vd or "us" in vd) else [vd]
        for m in markets:
            if isinstance(m, dict):
                for k in ("bullish", "bearish", "risks"):
                    if k not in m:
                        errs.append(f"verdict 缺少 {k}")

    for src in data.get("news", []) if isinstance(data.get("news"), list) else []:
        if isinstance(src, dict) and not src.get("source_url"):
            errs.append(f"news「{src.get('title', '?')}」缺少 source_url")

    return errs
