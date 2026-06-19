"""產生 Telegram 推播文字（摘要 + 連結）與失敗通知文字。

build_summary_text(day, url) -> str
build_failure_text(reason) -> str
"""

SITE_URL = "https://andy30019123agent-ship-it.github.io/daily-market-dashboard/"


def _pct(v):
    if not isinstance(v, (int, float)):
        return ""
    return f"{'+' if v >= 0 else ''}{v:.2f}%"


def build_summary_text(day: dict, url: str = SITE_URL) -> str:
    date = day.get("date", "")
    ov = day.get("overview", {})
    tw = ov.get("tw", {}).get("featured") or {}
    us = ov.get("us", []) or []

    lines = [f"📊 每日台美股戰報 · {date}", ""]

    # 台股加權
    if tw.get("close") is not None:
        arrow = "▲" if (tw.get("change_pct") or 0) >= 0 else "▼"
        lines.append(f"🇹🇼 加權 {tw['close']:,.0f} {arrow} {_pct(tw.get('change_pct'))}")

    # 美股重點（標普 / 那斯達克）
    pick = [u for u in us if u.get("name") in ("標普 500", "那斯達克", "費城半導體")]
    if pick:
        seg = "　".join(f"{u['name']} {_pct(u.get('change_pct'))}" for u in pick)
        lines.append(f"🇺🇸 {seg}")

    if lines[-1] != "":
        lines.append("")

    summary = day.get("summary", "").strip()
    if summary:
        lines.append(summary)
        lines.append("")

    lines.append(f"🔗 完整儀表板：{url}")
    return "\n".join(lines)


def build_failure_text(reason: str) -> str:
    return f"⚠️ 今天的台美股儀表板產製失敗\n\n原因：{reason}\n\n我會再嘗試或請你協助確認。"
