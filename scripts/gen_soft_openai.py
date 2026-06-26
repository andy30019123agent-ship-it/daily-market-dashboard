"""用 OpenAI（有網路搜尋的模型）產出戰報的「軟情報」: 新聞、台指 VIX、台美多空研判、摘要、近期事件。

硬數據（指數、三大法人、類股、熱門股、美股 VIX）一律由 fetch_hard_data 的 partial 提供，
本模組只負責「上網查 + 判讀」，且嚴禁竄改硬數據裡的數字。

用法：
  OPENAI_API_KEY=... python scripts/gen_soft_openai.py            # 讀最新 partial，寫 <date>.soft.json
  gen_soft(partial) -> dict                                       # 供其他程式呼叫
"""
import datetime
import json
import os
import pathlib
import re
import urllib.request

DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "public" / "data"
MODEL = os.environ.get("OPENAI_SOFT_MODEL", "gpt-4o-search-preview")
API = "https://api.openai.com/v1/chat/completions"


def _hard_context(partial: dict) -> str:
    """把硬數據壓成精簡文字，餵給模型當「已知事實」（不可竄改）。"""
    ov = partial.get("overview", {})
    tw = ov.get("tw", {})
    feat = tw.get("featured", {})
    lines = [f"報告日期(最新交易日): {partial.get('date')}"]
    if feat:
        lines.append(
            f"台股加權: {feat.get('close')} ({feat.get('change_pct'):+}%)"
        )
    stats = "、".join(f"{s['name']} {s['value']}" for s in tw.get("stats", []))
    if stats:
        lines.append("台股: " + stats)
    us = "、".join(
        f"{i.get('name')} {i.get('change_pct'):+}%" for i in ov.get("us", []) if i.get("change_pct") is not None
    )
    if us:
        lines.append("美股(最新已收盤交易日，官方數據，請據此判讀美股多空): " + us)
    vus = ov.get("vix", {}).get("us") or {}
    if vus.get("value") is not None:
        lines.append(f"美股 VIX: {vus.get('value')} ({vus.get('change')})")
    sec = partial.get("sectors_tw") or {}
    if sec.get("in"):
        lines.append("台股強勢類股: " + "、".join(s.get("name", "") for s in sec["in"][:5]))
    if sec.get("out"):
        lines.append("台股弱勢類股: " + "、".join(s.get("name", "") for s in sec["out"][:5]))
    hot = partial.get("hot_stocks", {}).get("tw", [])
    if hot:
        lines.append(
            "台股熱門股: " + "、".join(f"{h.get('name')}({h.get('code')}) {h.get('change_pct')}%" for h in hot[:6])
        )
    return "\n".join(lines)


PROMPT = """你是台美股盤後戰報的研究員。以下是「報告日期當天已由官方來源抓好的硬數據」，是不可更動、不可矛盾的事實：

{hard}

【最重要】你的研判(verdict)與摘要(summary)必須與上面硬數據的方向完全一致，不得自相矛盾：
- 「外資買賣超」為正 = 外資買超 = 對台股偏利多；為負才是賣超。
- 加權指數上漲(change_pct 為正) = 當日偏多訊號；創新高更是強多。
- 美股各指數 change_pct 為正 = 當日收紅、偏多。
- 先讀懂上面數字代表的多空方向，再下判斷。若你查到的新聞與硬數據方向衝突，以硬數據為準。

請上網搜尋「報告日期當天或前一交易日(最近 24 小時內)」的相關新聞，輸出一個 JSON 物件（只輸出 JSON、不要任何其他文字、不要 markdown 圍欄），鍵如下：

{{
  "news": [ {{"tag":"pos|neg|neu","title":"...","impact":"一句影響","date":"YYYY-MM-DD(該篇報導的發布日期)","source_name":"正規新聞媒體名","source_url":"該篇文章的真實單篇網址"}} ],   // 4 則，台股盤後/美股/總經(Fed、關稅、AI、地緣)各有涵蓋
  "vix_us": {{"state":"短語","note":"一句"}},   // 只補美股VIX的文字狀態(數值已有)
  "verdict": {{
     "tw": {{"stance":"偏多|中性偏多|中性|中性偏空|偏空","score":0到100整數,"comment":"1~2句為何此判斷(須呼應硬數據)","bullish":["利多..."],"bearish":["利空..."],"risks":["隱憂..."]}},
     "us": {{"stance":"...","score":..,"comment":"..","bullish":[..],"bearish":[..],"risks":[..]}}
  }},
  "summary": "3~5句，台美兩地重點，給 Telegram 摘要用(須呼應硬數據方向)",
  "upcoming_events": [ {{"date":"YYYY-MM-DD","name":"事件","analysis":"一句"}} ],   // 本週未發生的重大日(FOMC/CPI/非農/台積電法說/四巫日等)，沒有就空陣列
  "past_events_review": [ {{"date":"YYYY-MM-DD","name":"事件","result":"事後結果一句"}} ]   // 近日已發生重大事件回顧，沒有就空陣列
}}

規則：
- score：0 極空、50 中性、100 極多；stance 與 score 要一致(偏多→score>60、偏空→score<40)。
- 台股看台股(指數/法人/類股)、美股看美股(指數/晶片/Fed/VIX)，分開判讀。
- bullish/bearish/risks 各 2~3 條精簡條列。
- 嚴禁更動或臆造硬數據裡的數字。
- 新聞鐵則（攸關正確性，務必嚴守）：
  ① 每則必附 date（該報導發布日期），且必須落在「報告日期當天或前一交易日（±1 天內）」；嚴禁放更早的舊聞、別天的新聞。
  ② source_url 必須是正規新聞媒體的「單篇文章」真實連結；嚴禁 YouTube／影片／Facebook／Threads／X／Instagram／論壇(PTT)／首頁／搜尋頁／杜撰。
  ③ 標題與當天行情方向一致：加權當日下跌就不可放「創新高／大漲」之類矛盾標題，反之亦然。
- 全程繁體中文，中文與英數間加半形空格。"""


# 非正規新聞來源（影片／社群／論壇／首頁搜尋）一律過濾，確保「消息」品質
_BAD_HOSTS = (
    "youtube.com", "youtu.be", "facebook.com", "fb.com", "twitter.com",
    "x.com", "threads.net", "tiktok.com", "instagram.com", "ptt.cc",
    "reddit.com", "google.com/search",
)


def _news_ok(n: dict, report_date: str) -> bool:
    """新聞過濾：只留 http(s)、正規媒體單篇文章、且發布日期落在報告日 ±2 天內。"""
    url = str(n.get("source_url", ""))
    if not url.startswith(("http://", "https://")):
        return False
    if any(b in url.lower() for b in _BAD_HOSTS):
        return False
    nd = str(n.get("date", "")).strip()
    if report_date and re.fullmatch(r"\d{4}-\d{2}-\d{2}", nd):
        try:
            gap = abs((datetime.date.fromisoformat(nd)
                       - datetime.date.fromisoformat(report_date)).days)
            if gap > 2:   # 別天的舊新聞（如一週前的）直接剔除
                return False
        except ValueError:
            pass
    return True


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    # 取第一個 { 到最後一個 }
    i, j = text.find("{"), text.rfind("}")
    if i == -1 or j == -1:
        raise ValueError(f"模型回傳不含 JSON: {text[:300]}")
    return json.loads(text[i : j + 1])


def _carry_vix_tw(report_date):
    """台指 VIX(VIXTWN) 無法在 CI 純程式抓取（JS 渲染）→ 沿用前一日 day.json 的值。
    note 一律由程式重新組字，不沿用任何舊的自由敘述，避免過期說法（如「端午節休市」）卡死往後傳。"""
    days = sorted(p for p in DATA_DIR.glob("*.json")
                  if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.json", p.name) and p.stem <= report_date)
    if not days:
        return None
    prev = json.loads(days[-1].read_text(encoding="utf-8"))
    v = (prev.get("overview", {}).get("vix", {}) or {}).get("tw")
    if not v:
        return None
    v = dict(v)
    # source_date＝該數值真正量測日：有就沿用，否則以前一份檔名日為準（不臆造）
    src = v.get("source_date")
    if src:
        v["note"] = f"台指 VIX 沿用 {src} 收盤值（無免費即時源，非當日即時，需人工更新）"
    else:
        v["note"] = "台指 VIX 為沿用值、非當日即時（無免費即時源，需人工更新）"
    return v


def gen_soft(partial: dict) -> dict:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise SystemExit("缺少環境變數 OPENAI_API_KEY")
    body = {
        "model": MODEL,
        "web_search_options": {},
        "messages": [
            {"role": "user", "content": PROMPT.format(hard=_hard_context(partial))}
        ],
    }
    req = urllib.request.Request(
        API,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.load(r)
    content = resp["choices"][0]["message"]["content"]
    soft = _extract_json(content)
    # 新聞過濾：http(s) + 正規媒體單篇 + 發布日期落在報告日 ±2 天（擋注入、影片/社群、別天舊聞）
    soft["news"] = [n for n in soft.get("news", []) if _news_ok(n, partial.get("date", ""))]
    # 台指 VIX：硬數據(TAIFEX 官方)有抓到就用它；只有 fetch 失敗時才沿用前值（不讓模型臆造）。
    if ((partial.get("overview", {}).get("vix", {}) or {}).get("tw")) is None:
        carried = _carry_vix_tw(partial.get("date", ""))
        if carried:
            soft["vix_tw"] = carried
    return soft


def main():
    partials = sorted(DATA_DIR.glob("*.partial.json"))
    if not partials:
        raise SystemExit("找不到 partial.json，請先跑 fetch_hard_data.py")
    partial = json.loads(partials[-1].read_text(encoding="utf-8"))
    soft = gen_soft(partial)
    out = DATA_DIR / f"{partial['date']}.soft.json"
    out.write_text(json.dumps(soft, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已產出軟情報 {out.name}（news {len(soft.get('news', []))} 則）")


if __name__ == "__main__":
    main()
