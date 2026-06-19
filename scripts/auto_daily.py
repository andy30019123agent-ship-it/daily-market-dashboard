"""戰報每日總協調（接在 fetch_hard_data 之後）：
   選最新 partial → OpenAI 產軟情報 → 合併 → schema 驗證 → 寫 <date>.json + 更新索引
   → 只在「出現新交易日資料」時推一次 Telegram。

用法：
  python scripts/auto_daily.py            # 完整跑（會發 TG）
  python scripts/auto_daily.py --dry-run  # 組裝+寫檔但不發 TG、不動 notify_state（本機驗證）
環境變數：OPENAI_API_KEY（軟情報）、TG_BOT_TOKEN（推播）、TG_CHAT_ID（可選）
"""
import argparse
import datetime
import json
import os
import urllib.parse
import urllib.request

from scripts.gen_soft_openai import gen_soft
from scripts.merge_day import DATA_DIR, merge_day, update_index
from scripts.lib.schema import validate_day
from scripts.notify import build_summary_text

STATE = DATA_DIR / "notify_state.json"
CHAT = os.environ.get("TG_CHAT_ID", "-5127072553")


def pick_partial():
    """選 _meta.trade_date 最新的 partial（避開殘留的舊/錯日期檔）。"""
    best = None
    for p in DATA_DIR.glob("*.partial.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        td = d.get("_meta", {}).get("trade_date", "")
        if best is None or td > best[0]:
            best = (td, d)
    if best is None:
        raise SystemExit("找不到 partial.json，請先跑 fetch_hard_data.py")
    return best


def report_date(trade_date, partial):
    if trade_date and len(trade_date) == 8:
        return f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"
    return partial["date"]


US_MAJORS = ["道瓊", "標普 500", "那斯達克", "費城半導體"]


def _canon_us(name):
    n = (name or "").replace(" ", "")
    if "道瓊" in n or "dow" in n.lower():
        return "道瓊"
    if "標普" in n or "s&p" in n.lower() or "500" in n:
        return "標普 500"
    if "那斯" in n or "那指" in n or "nasdaq" in n.lower():
        return "那斯達克"
    if "費" in n or "半導體" in n or "sox" in n.lower():
        return "費城半導體"
    return name


def _override_us(day, partial, us_fix):
    """美股四大指數以 OpenAI 查到的最新收盤為準（免費源 FRED 常延遲/缺漏），spark 沿用 partial。"""
    prev = {i.get("name"): i for i in (partial.get("overview", {}).get("us") or [])}
    fix = {}
    for it in (us_fix or []):
        cp = it.get("change_pct")
        if cp is not None and abs(cp) < 20:
            fix[_canon_us(it.get("name"))] = it
    out = []
    for name in US_MAJORS:
        base = dict(prev.get(name, {}))
        base["name"] = name
        f = fix.get(name)
        if f:
            if f.get("close"):
                base["close"] = f["close"]
            base["change_pct"] = f["change_pct"]
        if base.get("change_pct") is not None:  # 有值才放，避免殘缺
            out.append(base)
    if out:
        day["overview"]["us"] = out


def send_tg(text):
    token = os.environ.get("TG_BOT_TOKEN")
    if not token:
        raise SystemExit("缺少 TG_BOT_TOKEN")
    data = urllib.parse.urlencode(
        {"chat_id": CHAT, "text": text, "disable_web_page_preview": "true"}
    ).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage", data=data
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.load(r)
    if not resp.get("ok"):
        raise SystemExit(f"Telegram 發送失敗：{resp}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    td, partial = pick_partial()
    date = report_date(td, partial)
    partial["date"] = date  # 校正成真正的交易日

    soft = gen_soft(partial)
    now = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=8))
    ).strftime("%Y-%m-%d %H:%M")
    day = merge_day(partial, soft, date, updated_at=now)
    _override_us(day, partial, soft.get("us_indices"))

    errs = validate_day(day)
    if errs:
        raise SystemExit("schema 驗證未過：" + "；".join(errs))

    (DATA_DIR / f"{date}.json").write_text(
        json.dumps(day, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    update_index(date)
    print(f"已產出 {date}.json（news {len(day['news'])} 則，"
          f"台股研判 {day['verdict']['tw']['stance']}）")

    last = None
    if STATE.exists():
        try:
            last = json.loads(STATE.read_text(encoding="utf-8")).get("last_notified")
        except Exception:
            last = None

    if args.dry_run:
        print(f"[dry-run] 不發 TG。資料日期={date} 上次推={last}")
        print("--- 摘要預覽 ---\n" + build_summary_text(day))
        return

    if last and date <= last:
        print(f"資料日期 {date} 未更新（上次已推 {last}），不重複推播。")
        return

    send_tg(build_summary_text(day))
    STATE.write_text(json.dumps({"last_notified": date}, ensure_ascii=False),
                     encoding="utf-8")
    print(f"已推播戰報並更新 state：last_notified={date}")


if __name__ == "__main__":
    main()
