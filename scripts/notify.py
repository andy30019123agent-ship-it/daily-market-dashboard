"""產生 Telegram 推播文字（摘要 + 連結）與失敗通知文字。

build_summary_text(day, url) -> str
build_failure_text(reason) -> str
"""
import json
import pathlib

SITE_URL = "https://andy30019123agent-ship-it.github.io/daily-market-dashboard/"
DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "public" / "data"
ACCURACY_PATH = DATA_DIR / "accuracy.json"


def _accuracy_line():
    """近 30 次研判命中率一行；accuracy.json 不存在或格式異常一律安靜跳過（不能讓推播炸掉）。"""
    try:
        acc = json.loads(ACCURACY_PATH.read_text(encoding="utf-8"))
        tw, us = acc.get("tw", {}), acc.get("us", {})
        tw_rate, tw_n = tw.get("recent30_rate"), tw.get("recent30_total") or 0
        us_rate, us_n = us.get("recent30_rate"), us.get("recent30_total") or 0
        if tw_rate is None and us_rate is None:
            return None
        tw_s = f"{tw_rate}%" if tw_rate is not None else "—"
        us_s = f"{us_rate}%" if us_rate is not None else "—"
        n = max(tw_n, us_n)  # 台美計分樣本數可能不同（中性研判不計分），取較大者代表區間規模
        return f"📊 近 30 日研判命中率：台股 {tw_s}／美股 {us_s}（樣本 {n}）"
    except Exception:
        return None


def _earnings_line(day: dict):
    """明日法說會一行（跨專案互串，來源讀不到/沒有場次就回 None，靜默跳過不影響其他推播內容）。"""
    events = day.get("earnings_tomorrow") or []
    if not events:
        return None
    shown = events[:5]
    parts = [f"{e.get('id', '')} {e.get('name', '')}" + (f"（{e['industry']}）" if e.get("industry") else "")
             for e in shown]
    line = "📅 明日法說會：" + "、".join(parts)
    if len(events) > 5:
        line += f"　等 {len(events)} 場"
    return line


def _pct(v):
    if not isinstance(v, (int, float)):
        return ""
    return f"{'+' if v >= 0 else ''}{v:.2f}%"


def build_summary_text(day: dict, url: str = SITE_URL) -> str:
    date = day.get("date", "")
    ov = day.get("overview", {})
    tw = ov.get("tw", {}).get("featured") or {}
    stats = ov.get("tw", {}).get("stats", []) or []
    us = ov.get("us", []) or []

    lines = [f"📊 每日台美股戰報 · {date}", ""]

    # 台股（每項一行，避免長行折行跑版）
    tw_lines = []
    if tw.get("close") is not None:
        pct = tw.get("change_pct") or 0
        arrow = "▲" if pct >= 0 else "▼"  # 箭頭已表方向，數字用絕對值，避免「▼-2.24%」雙重符號
        tw_lines.append(f"• 加權 {tw['close']:,.0f} {arrow}{abs(pct):.2f}%")
    for s in stats:
        if "外資" in s.get("name", "") and s.get("value"):
            tw_lines.append(f"• 外資 {s['value']}")
    if tw_lines:
        lines.append("🇹🇼 台股")
        lines += tw_lines
        lines.append("")

    # 美股（每檔一行）
    us_lines = [f"• {u['name']} {_pct(u.get('change_pct'))}"
                for u in us if u.get("name") in ("道瓊", "標普 500", "那斯達克", "費城半導體")]
    if us_lines:
        lines.append("🇺🇸 美股")
        lines += us_lines
        lines.append("")

    # 綜合多空研判（台美分列）
    vd = day.get("verdict", {}) or {}
    tw_v, us_v = vd.get("tw"), vd.get("us")
    if tw_v or us_v:
        lines.append("🧭 綜合研判")
        if tw_v and tw_v.get("stance"):
            lines.append(f"• 🇹🇼 台股：{tw_v['stance']}")
        if us_v and us_v.get("stance"):
            lines.append(f"• 🇺🇸 美股：{us_v['stance']}")
        lines.append("")
    elif vd.get("stance"):  # 舊版相容
        lines.append(f"🧭 綜合研判：{vd['stance']}")
        lines.append("")

    summary = day.get("summary", "").strip()
    if summary:
        lines.append(f"📝 {summary}")
        lines.append("")

    # 缺漏明示（⭐2）：抓不到的區塊要講出來，不靜默空白
    warns = day.get("_warnings") or []
    if warns:
        lines.append("⚠️ 今日缺（資料源異常）：" + "、".join(warns))
        lines.append("")

    acc_line = _accuracy_line()
    if acc_line:
        lines.append(acc_line)
        lines.append("")

    earn_line = _earnings_line(day)
    if earn_line:
        lines.append(earn_line)
        lines.append("")

    lines.append(f"🔗 完整儀表板：{url}")
    lines.append("※ AI 自動生成，僅供參考，非投資建議")
    return "\n".join(lines)


def build_failure_text(reason: str) -> str:
    return f"⚠️ 今天的台美股儀表板產製失敗\n\n原因：{reason}\n\n我會再嘗試或請你協助確認。"
