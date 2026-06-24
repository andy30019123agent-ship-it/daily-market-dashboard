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
from scripts.lib.sanity import check_consistency, collect_warnings
from scripts.notify import build_summary_text, build_failure_text

STATE = DATA_DIR / "notify_state.json"
CHAT = os.environ.get("TG_CHAT_ID", "-5127072553")

# 美股指數：FRED 在 GitHub Actions 會 timeout，改用 Yahoo（CI 連得到、回真實指數點數）
YAHOO_US = {
    "道瓊": "%5EDJI",
    "標普 500": "%5EGSPC",
    "那斯達克": "%5EIXIC",
    "費城半導體": "%5ESOX",
}


def _yahoo_quote(sym):
    """回 (最新收盤, 當日漲跌%)，取日線最後兩根收盤計算。"""
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
           "?interval=1d&range=7d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                d = json.load(r)
            res = d["chart"]["result"][0]
            closes = [c for c in res["indicators"]["quote"][0]["close"] if c]
            if len(closes) >= 2:
                cur, prev = closes[-1], closes[-2]
                return round(cur, 2), round((cur - prev) / prev * 100, 2)
        except Exception:
            continue
    return None


def yahoo_us():
    """美股四大指數 + VIX（Yahoo）。回 (us_list, vix_dict)。"""
    us = []
    for name, sym in YAHOO_US.items():
        q = _yahoo_quote(sym)
        if q:
            us.append({"name": name, "close": q[0], "change_pct": q[1]})
    vix = None
    q = _yahoo_quote("%5EVIX")
    if q:
        v = q[0]
        vix = {"value": v, "change": q[1],
               "gauge": max(0.0, min(1.0, 1 - (v - 10) / 30))}
    return us, vix


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


def _prev_day_us(date):
    """前一份 day.json 的美股（FRED 偶爾在 CI 缺漏時用來補，不留空殘缺）。"""
    import re
    days = sorted(p for p in DATA_DIR.glob("*.json")
                  if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.json", p.name) and p.stem < date)
    if not days:
        return {}
    prev = json.loads(days[-1].read_text(encoding="utf-8"))
    return {i.get("name"): i for i in (prev.get("overview", {}).get("us") or [])}


def _ensure_us(day, date):
    """美股一律用官方硬數據(FRED/AV)。若 FRED 在 CI 缺某指數，沿用前一日該指數值並標註，避免殘缺。"""
    have = {i.get("name"): i for i in day.get("overview", {}).get("us", [])}
    prev = None
    out = []
    for name in US_MAJORS:
        cur = have.get(name)
        if cur and cur.get("change_pct") is not None:
            out.append(cur)
            continue
        if prev is None:
            prev = _prev_day_us(date)
        p = prev.get(name)
        if p and p.get("change_pct") is not None:
            p = dict(p)
            p["note"] = "（沿用前值）"
            out.append(p)
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


def _run(dry_run):
    td, partial = pick_partial()
    date = report_date(td, partial)
    partial["date"] = date  # 校正成真正的交易日

    # 美股指數改用 Yahoo（FRED 在 CI 會 timeout）。在 gen_soft 前注入，讓研判也據此判讀。
    us, vix_us = yahoo_us()
    if us:
        partial.setdefault("overview", {})["us"] = us
        print("Yahoo 美股：" + "、".join(f"{i['name']} {i['change_pct']:+}%" for i in us))
    else:
        print("⚠️ Yahoo 美股取得失敗，將沿用前值")

    soft = gen_soft(partial)
    now = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=8))
    ).strftime("%Y-%m-%d %H:%M")
    day = merge_day(partial, soft, date, updated_at=now)
    _ensure_us(day, date)
    if vix_us:
        cur = day["overview"]["vix"].get("us") or {}
        cur.update(vix_us)  # 數值/gauge 用 Yahoo，state/note 保留軟情報
        day["overview"]["vix"]["us"] = cur

    errs = validate_day(day)
    if errs:
        raise SystemExit("schema 驗證未過：" + "；".join(errs))

    # ⭐1 發布前一致性自檢：資料自相矛盾就擋下不發（main 會發失敗通知）
    incons = check_consistency(day)
    if incons:
        raise SystemExit("一致性自檢未過（資料自相矛盾，已擋下不發布）：" + "；".join(incons))

    # ⭐2 缺漏盤點：照常發布，但記進 day 供推播明示，不靜默空白
    day["_warnings"] = collect_warnings(day)

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

    if dry_run:
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    try:
        _run(args.dry_run)
    except Exception as e:
        # 不靜默：非 dry-run 時把失敗發到 Telegram，再拋出讓 workflow 標記失敗
        if not args.dry_run:
            try:
                send_tg(build_failure_text(f"戰報自動更新失敗：{e}"))
            except Exception:
                pass
        raise


if __name__ == "__main__":
    main()
