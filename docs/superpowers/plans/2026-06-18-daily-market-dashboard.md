# 每日台美股戰略儀表板 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 一個獨立網站，每天台北 18:43 由 AI 分身自動更新台美股戰略儀表板，Telegram 推送摘要+連結，並可日期回看歷史。

**Architecture:** 純靜態前端（Vite + React）讀取每日 JSON 渲染 6 模組與日期選單；Python 腳本抓硬數據並與 AI 分身產出的軟情報合併成當日 JSON；GitHub Pages 託管；Claude cloud 排程每日喚醒分身執行完整流程並發 Telegram。

**Tech Stack:** Python 3（資料抓取/合併）、Node + Vite + React 18（前端）、pytest、GitHub Pages、Claude cloud 排程、Telegram plugin。

## Global Constraints

- 時區一律台北（Asia/Taipei, UTC+8）；排程觸發時間 18:43。
- 與 `tw-stock-screener` 完全獨立，不共用 repo、不互相讀寫。
- 軟情報每條必附來源連結。
- 市場範圍：台股加權；美股道瓊、標普、那斯達克、費半（SOX）。
- 中文排版：中文與英數之間加半形空格；保留專業術語英文原文。
- 所有資料源以實測驗證為準；資料源失敗時 Telegram 通知，不靜默失敗。
- 不做盤中即時、不做登入/多使用者、不做手動立即重抓按鈕。

---

### Task 0: 資料源驗證 Spike

**目的**：在寫任何抓取程式前，先實測每個免費資料源是否真的拿得到、回應格式為何。這是全案最大風險，先驗證。

**Files:**
- Create: `docs/data-sources.md`（記錄可用端點、範例回應、欄位對應）
- Create: `scripts/spike_sources.py`（一次性探測腳本，可保留）

**Interfaces:**
- Produces: `docs/data-sources.md` 中每個資料源的「URL + 取用方式 + 回應範例 + 欄位位置」，供 Task 2 抓取腳本直接引用。

- [ ] **Step 1: 探測台股加權指數與成交量**

用 TWSE 證交所 OpenAPI 探測大盤指數與每日成交資訊。於 `scripts/spike_sources.py` 內以 `requests` 取下列候選並印出回應前 500 字：
- 大盤統計：`https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX`（每日大盤）
- 個股當日成交：`https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL`

Run: `python scripts/spike_sources.py twse`
Expected: 印出 JSON，能看到加權指數收盤、漲跌、成交金額欄位。

- [ ] **Step 2: 探測美股指數（道瓊/標普/那斯達克/SOX）**

以 stooq 免費 CSV 探測（代碼：`^dji` 道瓊、`^spx` 標普、`^ndq` 那斯達克、`^sox` 費半）。範例：
`https://stooq.com/q/l/?s=^spx&f=sd2t2ohlcv&h&e=csv`

Run: `python scripts/spike_sources.py us`
Expected: 每個指數一行 CSV，含收盤價與日期；若被擋或欄位空，於 `docs/data-sources.md` 記錄並列出備援（如 Yahoo Finance `query1.finance.yahoo.com/v8/finance/chart/%5EGSPC`）。

- [ ] **Step 3: 探測恐懼貪婪指數**

美股 CNN Fear & Greed 公開資料端點：
`https://production.dataviz.cnn.io/index/fearandgreed/graphdata`（需帶 `User-Agent` 標頭）。

Run: `python scripts/spike_sources.py fng`
Expected: 印出 JSON，含 `fear_and_greed.score` 與 `rating`。記錄到 `docs/data-sources.md`。

- [ ] **Step 4: 記錄結論與台股情緒替代方案**

把每個資料源的可用 URL、取用方式、欄位位置寫進 `docs/data-sources.md`。台股無官方 F&G，記錄替代呈現：用 TWSE 漲跌家數（上漲/下跌家數比）做為情緒近似，標註「非官方、近似指標」。

- [ ] **Step 5: Commit**

```bash
git add scripts/spike_sources.py docs/data-sources.md
git commit -m "spike: 驗證台美股與恐懼貪婪指數免費資料源"
```

---

### Task 1: 資料模型與範例 fixture

**目的**：先把「一天的儀表板」資料長什麼樣定死，前端與抓取腳本都依此契約開發，可平行進行。

**Files:**
- Create: `schema/day-schema.md`（欄位說明）
- Create: `public/data/2026-06-18.json`（手填的範例 fixture，供前端開發）
- Create: `public/data/index.json`（日期索引）
- Create: `scripts/lib/schema.py`（schema 驗證函式）
- Test: `scripts/tests/test_schema.py`

**Interfaces:**
- Produces:
  - 當日資料檔結構（鍵）：`date`, `overview`, `sectors_and_hot`, `news`, `upcoming_events`, `past_events_review`, `verdict`, `summary`。
  - `validate_day(data: dict) -> list[str]`：回傳錯誤訊息清單，空清單代表通過。
  - `index.json` 結構：`{"dates": ["2026-06-18", ...]}`（新到舊排序由前端處理）。

- [ ] **Step 1: 寫 schema 文件**

於 `schema/day-schema.md` 定義每個模組欄位。要點：
- `overview.tw`：`{ name, close, change_pct, volume }`（加權）
- `overview.us`：`[{ name, close, change_pct }]`（道瓊/標普/那斯達克/SOX）
- `overview.fng`：`{ us_score:int, us_rating:str, tw_advance:int, tw_decline:int }`
- `sectors_and_hot`：`{ sectors:[{name, flow, note}], hot_stocks:[{code, name, change_pct, reason}] }`
- `news`：`[{ title, impact, source_url }]`（impact 為一句影響說明）
- `upcoming_events`：`[{ date, name, analysis }]`
- `past_events_review`：`[{ date, name, result }]`
- `verdict`：`{ bullish:[str], bearish:[str], risks:[str] }`
- `summary`：`str`（Telegram 用 3~5 句）

- [ ] **Step 2: 寫 fixture 與 index**

依 schema 手填 `public/data/2026-06-18.json`（內容可為合理假資料，每個 news 帶真實格式的 source_url），並建 `public/data/index.json` = `{"dates":["2026-06-18"]}`。

- [ ] **Step 3: 寫失敗測試**

```python
# scripts/tests/test_schema.py
import json, pathlib
from scripts.lib.schema import validate_day

def test_fixture_passes_schema():
    data = json.loads(pathlib.Path("public/data/2026-06-18.json").read_text())
    assert validate_day(data) == []

def test_missing_key_reported():
    assert "overview" in " ".join(validate_day({"date": "2026-06-18"}))
```

- [ ] **Step 4: 跑測試確認失敗**

Run: `python -m pytest scripts/tests/test_schema.py -v`
Expected: FAIL（`schema` 模組不存在）。

- [ ] **Step 5: 實作 validate_day**

```python
# scripts/lib/schema.py
REQUIRED = ["date","overview","sectors_and_hot","news",
            "upcoming_events","past_events_review","verdict","summary"]

def validate_day(data: dict) -> list[str]:
    errs = [f"缺少欄位 {k}" for k in REQUIRED if k not in data]
    if "overview" in data:
        ov = data["overview"]
        for k in ("tw","us","fng"):
            if k not in ov:
                errs.append(f"overview 缺少 {k}")
    return errs
```

- [ ] **Step 6: 跑測試確認通過**

Run: `python -m pytest scripts/tests/test_schema.py -v`
Expected: PASS。

- [ ] **Step 7: Commit**

```bash
git add schema scripts public/data
git commit -m "feat: 定義每日資料 schema 與範例 fixture"
```

---

### Task 2: 硬數據抓取腳本

**目的**：把 Task 0 驗證過的資料源寫成可重跑的抓取，輸出當日 JSON 的硬數據部分。

**Files:**
- Create: `scripts/fetch_hard_data.py`
- Create: `scripts/lib/parsers.py`（純解析函式，可測）
- Test: `scripts/tests/test_parsers.py`

**Interfaces:**
- Consumes: `docs/data-sources.md`（端點）、`validate_day`。
- Produces:
  - `parse_us_csv(csv_text:str) -> dict`：stooq CSV → `{name, close, change_pct}`（change_pct 需另抓前收或由 open/close 推算，依 Task 0 結論）。
  - `parse_fng(json_obj:dict) -> dict`：CNN JSON → `{us_score:int, us_rating:str}`。
  - `fetch_hard_data(date:str) -> dict`：回傳含 `overview` 與 `sectors_and_hot.hot_stocks`（市場熱門：當日漲幅榜前 N）的部分 dict。

- [ ] **Step 1: 寫解析函式失敗測試**

```python
# scripts/tests/test_parsers.py
from scripts.lib.parsers import parse_us_csv, parse_fng

def test_parse_us_csv():
    csv = "Symbol,Date,Time,Open,High,Low,Close,Volume\n^SPX,2026-06-18,22:00:00,5000,5050,4990,5040,0"
    out = parse_us_csv(csv)
    assert out["close"] == 5040.0

def test_parse_fng():
    out = parse_fng({"fear_and_greed":{"score":68.2,"rating":"greed"}})
    assert out["us_score"] == 68 and out["us_rating"] == "greed"
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest scripts/tests/test_parsers.py -v`
Expected: FAIL（模組不存在）。

- [ ] **Step 3: 實作 parsers**

```python
# scripts/lib/parsers.py
import csv, io

def parse_us_csv(csv_text: str) -> dict:
    row = list(csv.DictReader(io.StringIO(csv_text)))[0]
    return {"name": row["Symbol"], "close": float(row["Close"])}

def parse_fng(json_obj: dict) -> dict:
    fg = json_obj["fear_and_greed"]
    return {"us_score": int(round(fg["score"])), "us_rating": fg["rating"]}
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest scripts/tests/test_parsers.py -v`
Expected: PASS。

- [ ] **Step 5: 實作 fetch_hard_data 並實跑**

於 `scripts/fetch_hard_data.py` 用 `requests`（帶 User-Agent）抓 TWSE、stooq、CNN，組成 `overview` 與市場熱門個股（取 TWSE 個股當日漲幅前 10），寫出 `public/data/<date>.partial.json`。對每個來源做 try/except，失敗則該區塊填 `null` 並記錄 `errors` 清單。

Run: `python scripts/fetch_hard_data.py`
Expected: 產生 `public/data/<今日>.partial.json`，台股美股數字與 F&G 有值；終端印出 `errors`（理想為空）。

- [ ] **Step 6: Commit**

```bash
git add scripts/fetch_hard_data.py scripts/lib/parsers.py scripts/tests/test_parsers.py
git commit -m "feat: 硬數據抓取（台美股指數、F&G、市場熱門股）"
```

---

### Task 3: 前端骨架與日期回看

**目的**：用 Task 1 的 fixture 做出可看的網頁雛形，先讓 Andy 看到長相。

**Files:**
- Create: `package.json`, `vite.config.js`, `index.html`, `src/main.jsx`, `src/App.jsx`
- Create: `src/lib/loadDay.js`、`src/lib/tests/loadDay.test.js`
- Create: 各模組元件 `src/components/Overview.jsx`, `SectorsHot.jsx`, `News.jsx`, `UpcomingEvents.jsx`, `PastReview.jsx`, `Verdict.jsx`, `DatePicker.jsx`

**Interfaces:**
- Consumes: `public/data/index.json`、`public/data/<date>.json`。
- Produces: `loadIndex() -> Promise<string[]>`（日期，新到舊）、`loadDay(date) -> Promise<object>`。

- [ ] **Step 1: 建 Vite + React 專案骨架**

`package.json` 依賴 `react`, `react-dom`, `vite`, `@vitejs/plugin-react`, `gh-pages`, `vitest`。`vite.config.js` 設 `base: '/daily-market-dashboard/'`（GitHub Pages 子路徑）。

Run: `npm install && npm run build`
Expected: build 成功，產出 `dist/`。

- [ ] **Step 2: 寫 loadDay 失敗測試**

```js
// src/lib/tests/loadDay.test.js
import { describe, it, expect, vi } from 'vitest'
import { sortDatesDesc } from '../loadDay.js'

describe('sortDatesDesc', () => {
  it('新到舊排序', () => {
    expect(sortDatesDesc(['2026-06-17','2026-06-18']))
      .toEqual(['2026-06-18','2026-06-17'])
  })
})
```

- [ ] **Step 3: 跑測試確認失敗**

Run: `npx vitest run`
Expected: FAIL（`sortDatesDesc` 不存在）。

- [ ] **Step 4: 實作 loadDay.js**

```js
// src/lib/loadDay.js
const base = import.meta.env.BASE_URL
export const sortDatesDesc = (d) => [...d].sort().reverse()
export async function loadIndex() {
  const r = await fetch(`${base}data/index.json`)
  return sortDatesDesc((await r.json()).dates)
}
export async function loadDay(date) {
  const r = await fetch(`${base}data/${date}.json`)
  return r.json()
}
```

- [ ] **Step 5: 跑測試確認通過**

Run: `npx vitest run`
Expected: PASS。

- [ ] **Step 6: 實作 App 與 6 模組元件**

`App.jsx`：載入 index → 預設最新日期 → `DatePicker` 切換 → 依序渲染 Overview / SectorsHot / News / UpcomingEvents / PastReview / Verdict。每個元件接對應 prop、用語意化標題。News 的 source_url 渲染成可點連結。漲跌與情緒分數用顏色（紅綠/分數色階）。

- [ ] **Step 7: build + 截圖自我驗證**

Run:
```bash
npm run build && npm run preview &
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --screenshot=/tmp/dash.png --window-size=1280,2000 http://localhost:4173/daily-market-dashboard/
```
Expected: `/tmp/dash.png` 顯示 6 模組與日期選單；用 Read 檢視截圖確認版面正常（注意用 `--headless=new`，舊版會裁圖）。

- [ ] **Step 8: Commit**

```bash
git add package.json vite.config.js index.html src
git commit -m "feat: 前端骨架、6 模組與日期回看（用 fixture）"
```

---

### Task 4: 視覺設計與手機 RWD

**目的**：套用設計技能讓儀表板專業、手機好讀（盤後常用手機看）。

**Files:**
- Modify: `src/App.css`（或各元件樣式）、各 `src/components/*.jsx`

**Interfaces:**
- Consumes: Task 3 的元件結構。Produces: 無新介面，純樣式。

- [ ] **Step 1: 套用設計技能規劃視覺**

依使用者偏好，同時參考 `frontend-design` 與 `ui-ux-pro-max` 兩套技能，為「資訊密度高的金融儀表板」定調：配色（深色為主、紅綠漲跌、情緒色階）、字級階層、卡片式模組、間距。

- [ ] **Step 2: 實作桌機樣式**

把 6 模組做成卡片網格，今日總覽置頂大數字，情緒指數用色塊/儀表呈現。

- [ ] **Step 3: 實作手機 RWD（≤720px）**

單欄堆疊、字級與觸控目標放大、長表改卡片列。

- [ ] **Step 4: 桌機 + 手機截圖驗證**

Run 兩次截圖（`--window-size=1280,2000` 與 `--window-size=390,2400`），用 Read 檢視 `/tmp/dash-desktop.png`、`/tmp/dash-mobile.png` 確認無錯位、無溢出。

- [ ] **Step 5: Commit**

```bash
git add src
git commit -m "style: 儀表板視覺設計與手機 RWD"
```

---

### Task 5: 軟情報生成與當日資料合併

**目的**：定義 AI 分身每天要做的事（軟情報蒐集判讀），並把硬數據 + 軟情報合併成完整當日 JSON、更新 index。

**Files:**
- Create: `RUNBOOK.md`（分身每日執行手冊）
- Create: `scripts/merge_day.py`
- Create: `scripts/lib/events.py`（已知財經行事曆表）
- Test: `scripts/tests/test_merge.py`

**Interfaces:**
- Consumes: `<date>.partial.json`（硬數據）、`validate_day`。
- Produces:
  - `merge_day(partial:dict, soft:dict, date:str) -> dict`：合併成符合 schema 的完整 dict。
  - `update_index(date:str) -> None`：把 date 併入 `public/data/index.json`（去重）。
  - `RUNBOOK.md`：分身產生 `soft` 內容（news/sectors 解讀/verdict/summary/事件分析）的步驟與「每條附 source_url」規則。

- [ ] **Step 1: 寫 merge 與 index 失敗測試**

```python
# scripts/tests/test_merge.py
import json, pathlib
from scripts.merge_day import merge_day, update_index
from scripts.lib.schema import validate_day

def test_merge_produces_valid_day():
    partial = {"overview":{"tw":{},"us":[],"fng":{}},
               "sectors_and_hot":{"hot_stocks":[]}}
    soft = {"news":[], "sectors":[], "upcoming_events":[],
            "past_events_review":[], "verdict":{"bullish":[],"bearish":[],"risks":[]},
            "summary":"測試"}
    day = merge_day(partial, soft, "2026-06-18")
    assert validate_day(day) == []

def test_update_index_dedup(tmp_path, monkeypatch):
    idx = tmp_path/"index.json"; idx.write_text('{"dates":["2026-06-18"]}')
    monkeypatch.setattr("scripts.merge_day.INDEX_PATH", idx)
    update_index("2026-06-18"); update_index("2026-06-19")
    assert json.loads(idx.read_text())["dates"].count("2026-06-18") == 1
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest scripts/tests/test_merge.py -v`
Expected: FAIL。

- [ ] **Step 3: 實作 merge_day 與 update_index**

```python
# scripts/merge_day.py
import json, pathlib
INDEX_PATH = pathlib.Path("public/data/index.json")

def merge_day(partial: dict, soft: dict, date: str) -> dict:
    return {
        "date": date,
        "overview": partial["overview"],
        "sectors_and_hot": {
            "sectors": soft.get("sectors", []),
            "hot_stocks": partial["sectors_and_hot"]["hot_stocks"],
        },
        "news": soft.get("news", []),
        "upcoming_events": soft.get("upcoming_events", []),
        "past_events_review": soft.get("past_events_review", []),
        "verdict": soft.get("verdict", {"bullish":[],"bearish":[],"risks":[]}),
        "summary": soft.get("summary", ""),
    }

def update_index(date: str) -> None:
    dates = json.loads(INDEX_PATH.read_text())["dates"] if INDEX_PATH.exists() else []
    if date not in dates:
        dates.append(date)
    INDEX_PATH.write_text(json.dumps({"dates": sorted(set(dates))}, ensure_ascii=False))
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest scripts/tests/test_merge.py -v`
Expected: PASS。

- [ ] **Step 5: 寫 RUNBOOK 與已知行事曆**

`RUNBOOK.md` 列分身每天步驟：①跑 `fetch_hard_data.py` ②上網蒐集當日川普/影響股市消息、判斷資金板塊流向、熱門股緣由，產出 `soft`（每條 news 附 source_url）③用 `events.py` 比對本週重大日程→寫 upcoming_events 影響分析、昨日已過→past_events_review ④寫 verdict（利多/利空/隱憂）與 summary ⑤`merge_day` + `update_index` ⑥build ⑦部署 ⑧Telegram。`scripts/lib/events.py` 放已知固定日程（四巫日、FOMC、CPI/非農慣例週次）供比對。

- [ ] **Step 6: Commit**

```bash
git add RUNBOOK.md scripts/merge_day.py scripts/lib/events.py scripts/tests/test_merge.py
git commit -m "feat: 軟情報合併、日期索引與每日執行手冊"
```

---

### Task 6: 部署 GitHub Pages

**目的**：把網站推上線，拿到固定連結。

**Files:**
- Modify: `package.json`（deploy script）
- Create: `.github/`（若用 Actions 部署；此處採 gh-pages 套件手動部署）

**Interfaces:**
- Consumes: build 產物 `dist/`。Produces: 線上 URL `https://<user>.github.io/daily-market-dashboard/`。

- [ ] **Step 1: 建遠端 repo 並設 deploy**

```bash
gh repo create daily-market-dashboard --public --source=. --remote=origin --push
```
`package.json` 加 `"deploy": "vite build && gh-pages -d dist"`。

- [ ] **Step 2: 首次部署**

Run: `npm run deploy`
Expected: 推上 `gh-pages` 分支；GitHub Pages 設定指向該分支。

- [ ] **Step 3: 線上驗證**

開 `https://<user>.github.io/daily-market-dashboard/`，確認 fixture 內容與日期選單正常。

- [ ] **Step 4: Commit**

```bash
git add package.json && git commit -m "chore: GitHub Pages 部署設定"
```

---

### Task 7: 雲端排程、Telegram 推送與失敗處理

**目的**：每天台北 18:43 自動執行整條流程並推 Telegram；失敗也通知。

**Files:**
- Create: `scripts/notify.py`（產生 Telegram 摘要文字 + 連結）
- Create: 排程設定（透過 `schedule` skill 建立 routine）
- Modify: `RUNBOOK.md`（補排程與通知細節）

**Interfaces:**
- Consumes: 當日 `summary`、線上 URL。
- Produces: `build_summary_text(day:dict, url:str) -> str`（3~5 句 + 連結）。

- [ ] **Step 1: 寫摘要文字失敗測試**

```python
# scripts/tests/test_notify.py
from scripts.notify import build_summary_text

def test_summary_has_link():
    txt = build_summary_text({"summary":"台股收紅 0.8%"}, "https://x.io/d/")
    assert "https://x.io/d/" in txt and "台股收紅" in txt
```

- [ ] **Step 2: 跑測試確認失敗 → 實作 → 確認通過**

```python
# scripts/notify.py
def build_summary_text(day: dict, url: str) -> str:
    return f"📊 今日台美股戰略儀表板\n\n{day['summary']}\n\n🔗 {url}"
```
Run: `python -m pytest scripts/tests/test_notify.py -v` → PASS。

- [ ] **Step 3: 建立雲端排程**

用 `schedule` skill 建立每日台北 18:43 的 routine，內容引用 `RUNBOOK.md`：執行完整流程（抓數據→軟情報→merge→build→deploy→用 Telegram plugin 發 `build_summary_text` 結果給 Andy 的 chat_id `542348223`）。

- [ ] **Step 4: 加入失敗通知**

於 RUNBOOK 規定：任一步驟拋錯時，分身改發「⚠️ 今天儀表板產製失敗：<原因>」到同一 Telegram chat，不靜默。

- [ ] **Step 5: 手動觸發一次完整實跑驗證**

手動執行整條流程一次（等同排程內容），確認：線上網頁出現「今天」這天、index 多一筆、Telegram 收到摘要+可點連結。

- [ ] **Step 6: Commit**

```bash
git add scripts/notify.py scripts/tests/test_notify.py RUNBOOK.md
git commit -m "feat: 雲端排程、Telegram 摘要推送與失敗通知"
```

---

## Self-Review 結果

- **Spec coverage**：6 模組（Task 1 schema + Task 3 元件）、市場範圍（Task 2）、F&G 與台股替代（Task 0/1）、軟情報附來源（Task 1/5 RUNBOOK）、日程雙段（Task 5 events + 模組 4/5）、歷史回看（Task 1 index + Task 3）、18:43 排程（Task 7）、Telegram 摘要（Task 7）、失敗通知（Task 7）、部署（Task 6）、設計與 RWD（Task 4）。皆有對應任務。
- **Placeholder scan**：邏輯層（schema/parsers/merge/notify）皆附完整程式碼與測試；UI 層提供結構與關鍵程式碼，驗證以 build+截圖。外部資料源因需實測，以 Task 0 spike 先行降低風險。
- **Type consistency**：`validate_day`、`merge_day`、`fetch_hard_data` 輸出鍵與 schema（overview/sectors_and_hot/news/upcoming_events/past_events_review/verdict/summary）一致；`index.json` 結構於 Task 1/3/5 一致。

## 階段交付節點（建議 Andy 檢視點）

- **看到雛形**：Task 3 完成（fixture 版網頁可看長相）。
- **看到真實數據**：Task 2 + 手動 merge 後。
- **正式上線自動推送**：Task 7 完成。
