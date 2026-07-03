# 資金流雷達×低基期潛力 升級 Phase B 實作計劃

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 為低基期潛力股加上「基本面分、進榜追蹤（連續在榜天數）、發動提醒推播、作戰室彙整」，把功能從「每日快照」升級為「持續追蹤 → 發動通知」。

**Architecture:** 沿用 Phase A 的評分管線。基本面分（免費 FinMind 月營收 YoY）併入既有子分合成。新增輕量歷史檔 `public/data/potential_history.json` 記錄每檔進榜狀態；純函式負責「更新歷史／算連續在榜天數／偵測發動」，auto_daily 讀寫並在偵測到發動時**經旗標控管**推播「🚀 發動提醒」。前端新增作戰室區塊，讀歷史檔把股票分成 觀察中／發動中／已淘汰 三組。

**Tech Stack:** Python 3（urllib、pytest）、React 18 + Vite（vitest）、FinMind 免費 API（TaiwanStockPrice 既有、TaiwanStockMonthRevenue 新）。

## Global Constraints

- 台北時間（Asia/Taipei）；日期字串 ISO `YYYY-MM-DD`。
- 潛力＋歷史＋提醒全區塊獨立於主戰報：任何失敗 try/except 吞掉、不得影響主戰報或每日推播。
- **發動提醒是對「叔叔名牌TG」群組（chat -5127072553）的新推播**：預設**不啟用**，僅當環境變數 `POTENTIAL_ALERTS=1` 才送，避免未經 Andy 確認門檻就洗群組。同一檔同一波只提醒一次（歷史檔記 alerted）。
- 分數權重（Phase B）：籌碼 0.35＋價量結構 0.35＋題材 0.20＋基本面 0.10，全部進 `potential.py DEFAULTS` 可調。
- 免責文案保留。白瓷粉視覺 tokens 不改、不新增字型/配色。
- 繁體中文註解，風格與周圍一致。
- 測試：Python `python3 -m pytest scripts/tests/ -q`；前端 `npm test`。
- 部署：此站為 Actions Pages artifact 部署（build_type=workflow），走 `gh workflow run daily.yml`，非 gh-pages 分支。

## 檔案結構

- `scripts/lib/potential.py`（改）：新增 `finmind_revenue`、`revenue_yoy`、`fundamental_score`；`build_potential` 掛 `fund_s`；`DEFAULTS` 加基本面權重與門檻；`finalize_scores` 合成改吃四子分。
- `scripts/lib/potential_history.py`（新）：`update_history`（進榜/連續天數/淘汰）、`detect_breakouts`（發動偵測）純函式，不碰 IO。
- `scripts/auto_daily.py`（改）：`_attach_potential` 之後接 `_attach_potential_history`（讀寫 `potential_history.json`、把 streak/first_date 標回今日 stocks、偵測發動、旗標控管推播）。
- `scripts/notify.py`（改）：`build_breakout_text(alerts)`。
- `public/data/potential_history.json`（新，CI commit 回 main，同 notify_state.json 模式）。
- `src/lib/loadDay.js`（改）：加 `loadPotentialHistory()`。
- `src/components/WarRoom.jsx`（新）：作戰室三組視圖。
- `src/App.jsx`（改）：台股分頁 grid 加 `<WarRoom>`。
- `src/styles.css`（改）：作戰室樣式（白瓷粉 tokens）。
- 測試：`scripts/tests/test_potential.py`、新 `scripts/tests/test_potential_history.py`、`scripts/tests/test_notify.py`、`src/lib/tests/warroom.test.js`（新）。

---

## Task 1: 基本面分（月營收 YoY）併入評分

**Files:**
- Modify: `scripts/lib/potential.py`
- Test: `scripts/tests/test_potential.py`

**Interfaces:**
- Consumes: FinMind `TaiwanStockMonthRevenue`（欄位 `revenue`、`revenue_year`、`revenue_month`，由舊到新）。
- Produces:
  - `revenue_yoy(rows) -> float | None`：最新月營收對去年同月的年增率（找不到同月回 None）。
  - `fundamental_score(yoy) -> float`（0~1）：yoy≤0→0、yoy≥0.3→1、中間線性。
  - `finmind_revenue(code, start_date) -> list`（打 FinMind，錯誤回 []）。
  - `build_potential` 每檔多掛 `fund_yoy`（float|None）與 `fund_s`（0~1）。
  - `finalize_scores` 合成改為四子分（chip/struct/theme/fund），`score_parts` 多 `fund`。
- `DEFAULTS` 新增：`w_chip 0.35, w_struct 0.35, w_theme 0.20, w_fund 0.10`（覆蓋 Phase A 的三權重）、`yoy_full 0.30`（YoY 給滿）。

- [ ] **Step 1: 寫失敗測試**

```python
def test_revenue_yoy_and_fund_score():
    rows = [
        {"revenue_year": 2024, "revenue_month": 5, "revenue": 100},
        {"revenue_year": 2025, "revenue_month": 5, "revenue": 130},  # YoY +30%
    ]
    yoy = potential.revenue_yoy(rows)
    assert round(yoy, 2) == 0.30
    assert potential.fundamental_score(0.30) == 1.0
    assert potential.fundamental_score(0.0) == 0.0
    assert potential.fundamental_score(None) == 0.0

def test_finalize_scores_includes_fund():
    cfg = dict(potential.DEFAULTS)
    stocks = [{"code": "A", "chip_s": 0.5, "struct_s": 0.5, "fund_s": 1.0,
               "catalyst": "", "theme": "AI", "sector": "電子"}]
    out = potential.finalize_scores(stocks, cfg)
    assert "fund" in out[0]["score_parts"]
    assert out[0]["score_parts"]["fund"] == 100
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python3 -m pytest scripts/tests/test_potential.py -k "revenue or fund" -q`
Expected: FAIL（`AttributeError: ... 'revenue_yoy'`）

- [ ] **Step 3: 實作**

`DEFAULTS` 權重改為四項並加 `yoy_full`：

```python
    "w_chip": 0.35, "w_struct": 0.35, "w_theme": 0.20, "w_fund": 0.10,
    "yoy_full": 0.30,   # 月營收 YoY 給滿分的門檻
```

新增函式（放在 `fundamental` 相關一段，`finmind_history` 之後）：

```python
FINMIND_REV = "TaiwanStockMonthRevenue"


def finmind_revenue(code: str, start_date: str) -> list[dict]:
    url = (f"{FINMIND_API}?dataset={FINMIND_REV}"
           f"&data_id={code}&start_date={start_date}")
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r).get("data") or []
    except Exception:
        return []


def revenue_yoy(rows: list[dict]) -> float | None:
    """最新月營收對去年同月年增率；找不到去年同月回 None。"""
    rows = [r for r in rows if r.get("revenue")]
    if not rows:
        return None
    last = rows[-1]
    y, m, rev = last["revenue_year"], last["revenue_month"], last["revenue"]
    prev = next((r for r in rows
                 if r["revenue_year"] == y - 1 and r["revenue_month"] == m), None)
    if not prev or not prev.get("revenue"):
        return None
    return round(rev / prev["revenue"] - 1, 4)


def fundamental_score(yoy: float | None, yoy_full: float = 0.30) -> float:
    if yoy is None or yoy <= 0:
        return 0.0
    return round(_clamp01(yoy / yoy_full), 3)
```

`build_potential` 迴圈掛 `fund_s`（沿用 `filter_low_base` 回來的 stocks；用同一 start_date 抓營收，抓不到給 0）：

```python
    for s in stocks:
        s["chip_s"] = chip_score(s, cfg["window"], cfg["chip_sat"])
        rev = fetch_revenue(s["code"], start_date) if fetch_revenue else []
        s["fund_yoy"] = revenue_yoy(rev)
        s["fund_s"] = fundamental_score(s["fund_yoy"], cfg["yoy_full"])
```

`build_potential` 簽章加 `fetch_revenue=finmind_revenue`（可注入假 fetch 測試）。

`finalize_scores` 合成改四子分：

```python
def finalize_scores(stocks: list[dict], cfg: dict) -> list[dict]:
    for s in stocks:
        t = theme_score(s)
        raw = (cfg["w_chip"] * s.get("chip_s", 0.0)
               + cfg["w_struct"] * s.get("struct_s", 0.0)
               + cfg["w_theme"] * t
               + cfg["w_fund"] * s.get("fund_s", 0.0))
        s["score"] = int(round(100 * raw))
        s["score_parts"] = {
            "chip": int(round(100 * s.get("chip_s", 0.0))),
            "struct": int(round(100 * s.get("struct_s", 0.0))),
            "theme": int(round(100 * t)),
            "fund": int(round(100 * s.get("fund_s", 0.0))),
        }
    stocks.sort(key=lambda s: s["score"], reverse=True)
    return stocks
```

（移除舊 `combine_score`，或保留但不再被 finalize 使用；若移除，順手刪其無引用。以實際引用為準——grep `combine_score` 確認無其他呼叫端再刪。）

- [ ] **Step 4: 跑測試確認通過**

Run: `python3 -m pytest scripts/tests/test_potential.py -q`
Expected: PASS（Phase A 的 `test_finalize_scores_sorts_and_scores` 仍過：只驗 A>B 與範圍，四權重不影響排序關係）

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/potential.py scripts/tests/test_potential.py
git commit -m "feat(potential): 基本面分(月營收YoY)併入發動信心分數"
```

---

## Task 2: potential_history 進榜追蹤（連續在榜天數）

**Files:**
- Create: `scripts/lib/potential_history.py`
- Test: `scripts/tests/test_potential_history.py`

**Interfaces:**
- Produces: `update_history(history, today_stocks, date) -> dict`
  - `history` 形如 `{"last_date": str|None, "stocks": {code: {name, streak, first_date, last_date, last_score}}}`（首次傳 `{}` 視為空）。
  - `today_stocks`：今日潛力榜（含 code/name/score）。
  - 規則：同一 `date` 重覆呼叫為冪等（不重覆累加）；今日在榜且上次也在榜（`last_date == history.last_date`）→ `streak+=1`，否則 `streak=1`、`first_date=date`；更新 `last_date=date`、`last_score`。回傳新 history（含更新後的 `last_date`）。
  - 回傳的 history 供呼叫端把 `streak/first_date` 標回今日 stocks。

- [ ] **Step 1: 寫失敗測試**

```python
from scripts.lib import potential_history as ph


def test_update_history_new_and_streak():
    h = {}
    h = ph.update_history(h, [{"code": "2603", "name": "長榮", "score": 80}], "2026-07-01")
    assert h["stocks"]["2603"]["streak"] == 1
    assert h["stocks"]["2603"]["first_date"] == "2026-07-01"
    # 隔一交易日仍在榜 → streak 2
    h = ph.update_history(h, [{"code": "2603", "name": "長榮", "score": 82}], "2026-07-02")
    assert h["stocks"]["2603"]["streak"] == 2
    assert h["last_date"] == "2026-07-02"


def test_update_history_idempotent_same_date():
    h = ph.update_history({}, [{"code": "2603", "name": "長榮", "score": 80}], "2026-07-01")
    h2 = ph.update_history(h, [{"code": "2603", "name": "長榮", "score": 80}], "2026-07-01")
    assert h2["stocks"]["2603"]["streak"] == 1  # 同日重跑不累加


def test_update_history_reset_after_gap():
    h = ph.update_history({}, [{"code": "2603", "name": "長榮", "score": 80}], "2026-07-01")
    # 07-02 沒在榜（今日清單不含 2603），07-03 又回來 → streak 重置 1
    h = ph.update_history(h, [{"code": "1216", "name": "統一", "score": 60}], "2026-07-02")
    h = ph.update_history(h, [{"code": "2603", "name": "長榮", "score": 70}], "2026-07-03")
    assert h["stocks"]["2603"]["streak"] == 1
    assert h["stocks"]["2603"]["first_date"] == "2026-07-03"
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python3 -m pytest scripts/tests/test_potential_history.py -q`
Expected: FAIL（module/function 不存在）

- [ ] **Step 3: 實作**

```python
"""低基期潛力股進榜歷史與發動偵測（純函式，不做 IO）。"""
from __future__ import annotations


def update_history(history: dict, today_stocks: list[dict], date: str) -> dict:
    prev_date = (history or {}).get("last_date")
    stocks = dict((history or {}).get("stocks") or {})
    if date == prev_date:
        return {"last_date": date, "stocks": stocks}  # 同日冪等
    today_codes = set()
    for s in today_stocks:
        code = s.get("code")
        if not code:
            continue
        today_codes.add(code)
        rec = stocks.get(code)
        if rec and rec.get("last_date") == prev_date:
            rec = {**rec, "streak": rec.get("streak", 0) + 1}
        else:
            rec = {"name": s.get("name"), "streak": 1, "first_date": date}
        rec["name"] = s.get("name") or rec.get("name")
        rec["last_date"] = date
        rec["last_score"] = s.get("score")
        stocks[code] = rec
    return {"last_date": date, "stocks": stocks}
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python3 -m pytest scripts/tests/test_potential_history.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/potential_history.py scripts/tests/test_potential_history.py
git commit -m "feat(potential): potential_history 進榜追蹤與連續在榜天數"
```

---

## Task 3: 發動偵測 + 🚀 提醒推播（旗標控管）

**Files:**
- Modify: `scripts/lib/potential_history.py`（`detect_breakouts`）
- Modify: `scripts/notify.py`（`build_breakout_text`）
- Modify: `scripts/auto_daily.py`（`_attach_potential_history` 串接、旗標推播）
- Test: `scripts/tests/test_potential_history.py`、`scripts/tests/test_notify.py`

**Interfaces:**
- `detect_breakouts(history, radar_stocks, date, cfg) -> list[dict]`
  - 對「近 `track_days` 內曾在榜」（history.stocks 內 `last_date` 在 date 前 track_days 天內）的 code，若今日 `radar_stocks` 中該 code 的 `pct >= breakout_pct` 且 history 中未標記過本波發動（`alerted_date` 空或早於本次在榜起點）→ 視為發動。
  - 回傳 `[{code, name, pct}]`；並在傳入的 `history.stocks[code]["alerted_date"] = date`（原地標記，呼叫端負責存檔）。
- `cfg` 取自 `potential.DEFAULTS`：新增 `track_days 5`、`breakout_pct 4.5`。
- `build_breakout_text(alerts, url) -> str`：組「🚀 發動提醒」訊息。

- [ ] **Step 1: 寫失敗測試**

```python
def test_detect_breakouts_flags_onboard_surge():
    h = {"last_date": "2026-07-02", "stocks": {
        "2603": {"name": "長榮", "streak": 3, "first_date": "2026-06-30",
                 "last_date": "2026-07-02", "last_score": 80},
    }}
    radar = [{"code": "2603", "name": "長榮", "pct": 6.2},
             {"code": "1216", "name": "統一", "pct": 5.0}]  # 1216 沒在榜→不提醒
    cfg = {"track_days": 5, "breakout_pct": 4.5}
    alerts = potential_history.detect_breakouts(h, radar, "2026-07-03", cfg)
    assert [a["code"] for a in alerts] == ["2603"]
    assert h["stocks"]["2603"]["alerted_date"] == "2026-07-03"
    # 再跑同日不重覆提醒
    assert potential_history.detect_breakouts(h, radar, "2026-07-03", cfg) == []
```

（`test_notify.py`）：

```python
def test_build_breakout_text():
    txt = notify.build_breakout_text([{"code": "2603", "name": "長榮", "pct": 6.2}])
    assert "🚀" in txt and "長榮" in txt and "6.2" in txt
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python3 -m pytest scripts/tests/test_potential_history.py -k breakout scripts/tests/test_notify.py -k breakout -q`
Expected: FAIL

- [ ] **Step 3: 實作 detect_breakouts**

`potential_history.py` 追加：

```python
import datetime as _dt


def _within(days_str: str, date: str, n: int) -> bool:
    try:
        a = _dt.date.fromisoformat(days_str)
        b = _dt.date.fromisoformat(date)
        return 0 <= (b - a).days <= n
    except Exception:
        return False


def detect_breakouts(history: dict, radar_stocks: list[dict], date: str,
                     cfg: dict) -> list[dict]:
    stocks = (history or {}).get("stocks") or {}
    by_code = {s.get("code"): s for s in radar_stocks}
    out = []
    for code, rec in stocks.items():
        if not _within(rec.get("last_date", ""), date, cfg["track_days"]):
            continue
        if rec.get("alerted_date") == date:
            continue
        q = by_code.get(code)
        if q and (q.get("pct") or 0) >= cfg["breakout_pct"]:
            rec["alerted_date"] = date
            out.append({"code": code, "name": rec.get("name"), "pct": q.get("pct")})
    return out
```

`notify.py` 追加：

```python
def build_breakout_text(alerts: list, url: str = SITE_URL) -> str:
    lines = ["🚀 低基期潛力股發動提醒", ""]
    for a in alerts:
        pct = a.get("pct")
        pct_s = f"+{pct:.1f}%" if isinstance(pct, (int, float)) else ""
        lines.append(f"• {a.get('name', '')} {a.get('code', '')}　今日 {pct_s}")
    lines.append("")
    lines.append("（追蹤中的潛力股今日放量急拉，跡象非保證，請自行研判）")
    lines.append(f"🔗 {url}")
    return "\n".join(lines)
```

- [ ] **Step 4: 串接 auto_daily（旗標控管推播）**

在 `_attach_potential` 之後新增 `_attach_potential_history(day, date)`：讀 `potential_history.json` → `update_history` → 把 streak/first_date 標回 `day['potential']['stocks']` → `detect_breakouts`（用 `day['radar']['stocks']`）→ 寫回 `potential_history.json`；若有 alerts 且 `os.environ.get("POTENTIAL_ALERTS")=="1"` 且非 dry_run → `send_tg(build_breakout_text(alerts))`。全程 try/except。呼叫點：正常流程與凍結日都呼叫（潛力已在兩處刷新）。

```python
HISTORY = DATA_DIR / "potential_history.json"

def _attach_potential_history(day, date, dry_run=False):
    try:
        from scripts.lib.potential_history import update_history, detect_breakouts
        from scripts.lib.potential import DEFAULTS as PD
        from scripts.notify import build_breakout_text
        stocks = (day.get("potential") or {}).get("stocks") or []
        hist = {}
        if HISTORY.exists():
            hist = json.loads(HISTORY.read_text(encoding="utf-8"))
        hist = update_history(hist, stocks, date)
        # streak/first_date 標回今日 stocks 供前端顯示
        for s in stocks:
            rec = hist["stocks"].get(s.get("code")) or {}
            s["streak"] = rec.get("streak")
            s["first_date"] = rec.get("first_date")
        alerts = detect_breakouts(hist, (day.get("radar") or {}).get("stocks") or [],
                                  date, {"track_days": PD["track_days"],
                                         "breakout_pct": PD["breakout_pct"]})
        HISTORY.write_text(json.dumps(hist, ensure_ascii=False), encoding="utf-8")
        if alerts and not dry_run and os.environ.get("POTENTIAL_ALERTS") == "1":
            send_tg(build_breakout_text(alerts))
            print(f"🚀 發動提醒已推播：{[a['code'] for a in alerts]}")
        elif alerts:
            print(f"🚀 發動偵測（未推播，POTENTIAL_ALERTS≠1）：{[a['code'] for a in alerts]}")
    except Exception as e:
        print(f"⚠️ 潛力歷史/發動偵測略過（不影響主戰報）：{e}")
```

在 `potential.py DEFAULTS` 加 `"track_days": 5, "breakout_pct": 4.5,`。在 auto_daily 兩個呼叫 `_attach_potential(...)` 的地方（正常流程 line ~394、凍結日 line ~340 附近）之後各加一行 `_attach_potential_history(<day>, date, dry_run=dry_run)`。

- [ ] **Step 5: 跑測試確認通過**

Run: `python3 -m pytest scripts/tests/ -q`
Expected: PASS（含新測試）

- [ ] **Step 6: 本機冒煙（不推播）**

Run: `python3 -c "import scripts.auto_daily"` 確認 import 無誤；`POTENTIAL_ALERTS` 未設時即使有 alerts 也只印不推。

- [ ] **Step 7: Commit**

```bash
git add scripts/lib/potential_history.py scripts/lib/potential.py scripts/auto_daily.py scripts/notify.py scripts/tests/test_potential_history.py scripts/tests/test_notify.py
git commit -m "feat(potential): 發動偵測＋🚀提醒推播(POTENTIAL_ALERTS 旗標控管)＋進榜歷史落地"
```

---

## Task 4: 作戰室前端（觀察中／發動中／已淘汰）

**Files:**
- Modify: `src/lib/loadDay.js`（`loadPotentialHistory`）
- Create: `src/components/WarRoom.jsx`
- Modify: `src/App.jsx`（台股 grid 加 `<WarRoom>`）
- Modify: `src/styles.css`
- Test: `src/lib/tests/warroom.test.js`（純函式 `groupWarRoom`）

**Interfaces:**
- `loadPotentialHistory()`：fetch `data/potential_history.json`（沿用 loadDay 的 base 前綴），失敗回 `{stocks:{}}`。
- `groupWarRoom(history, todayStocks, date, opts) -> { watching, launched, dropped }`（純函式，放 `src/lib/warroom.js`）：
  - `watching`：今日在榜（todayStocks），附 streak。
  - `launched`：history 中 `alerted_date` 在近 `opts.launchDays`（預設 5）內的。
  - `dropped`：history 中曾在榜但 `last_date` 不是今日、且在近 `opts.dropDays`（預設 5）內掉出的。

- [ ] **Step 1: 寫失敗測試（`src/lib/tests/warroom.test.js`）**

```js
import { describe, it, expect } from 'vitest'
import { groupWarRoom } from '../warroom.js'

describe('groupWarRoom', () => {
  it('分成 觀察中/發動中/已淘汰', () => {
    const history = { last_date: '2026-07-03', stocks: {
      '2603': { name: '長榮', streak: 3, last_date: '2026-07-03' },
      '1101': { name: '台泥', last_date: '2026-07-03', alerted_date: '2026-07-02' }, // 發動中
      '1216': { name: '統一', last_date: '2026-06-30' }, // 已淘汰(近日掉出)
    } }
    const today = [{ code: '2603', name: '長榮', score: 80, streak: 3 }]
    const g = groupWarRoom(history, today, '2026-07-03', { launchDays: 5, dropDays: 5 })
    expect(g.watching.map((s) => s.code)).toContain('2603')
    expect(g.launched.map((s) => s.code)).toContain('1101')
    expect(g.dropped.map((s) => s.code)).toContain('1216')
  })
})
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `npm test -- warroom`
Expected: FAIL（`groupWarRoom is not a function`）

- [ ] **Step 3: 實作 `src/lib/warroom.js`**

```js
// 作戰室分組：觀察中（今日在榜）/ 發動中（近日觸發發動）/ 已淘汰（近日掉出榜）
function daysBetween(a, b) {
  const d = (new Date(b) - new Date(a)) / 86400000
  return Number.isFinite(d) ? d : Infinity
}

export function groupWarRoom(history, todayStocks, date, opts = {}) {
  const launchDays = opts.launchDays ?? 5
  const dropDays = opts.dropDays ?? 5
  const stocks = (history && history.stocks) || {}
  const todayCodes = new Set((todayStocks || []).map((s) => s.code))
  const watching = [...(todayStocks || [])]
  const launched = []
  const dropped = []
  for (const [code, rec] of Object.entries(stocks)) {
    if (rec.alerted_date && daysBetween(rec.alerted_date, date) <= launchDays) {
      launched.push({ code, ...rec })
    }
    if (!todayCodes.has(code) && rec.last_date &&
        daysBetween(rec.last_date, date) <= dropDays) {
      dropped.push({ code, ...rec })
    }
  }
  return { watching, launched, dropped }
}
```

- [ ] **Step 4: 跑測試確認通過**

Run: `npm test -- warroom`
Expected: PASS

- [ ] **Step 5: WarRoom 元件 + 掛進 App**

`src/components/WarRoom.jsx`：

```jsx
import { useEffect, useState } from 'react'
import { loadPotentialHistory } from '../lib/loadDay.js'
import { groupWarRoom } from '../lib/warroom.js'

export default function WarRoom({ potential, date, onOpen }) {
  const [history, setHistory] = useState(null)
  useEffect(() => {
    let ok = true
    loadPotentialHistory().then((h) => { if (ok) setHistory(h) }).catch(() => {})
    return () => { ok = false }
  }, [])
  const today = potential?.stocks || []
  const { watching, launched, dropped } = groupWarRoom(history, today, date)
  if (!watching.length && !launched.length && !dropped.length) return null
  const Group = ({ title, items, tag }) => items.length ? (
    <div className="wr-group">
      <div className="wr-title">{title}</div>
      <div className="wr-rows">
        {items.map((s) => (
          <button key={s.code} className="wr-row" onClick={() => onOpen && onOpen(s.code)}>
            <span className="wr-nm">{s.name}<span className="wr-code">{s.code}</span></span>
            <span className="wr-meta">{tag(s)}</span>
          </button>
        ))}
      </div>
    </div>
  ) : null
  return (
    <section className="card col-12" data-region="⑩ 潛力股作戰室">
      <div className="card-h"><span className="label">🎯 潛力股作戰室</span></div>
      <Group title="🌱 觀察中" items={watching} tag={(s) => `在榜 ${s.streak ?? 1} 天 · ${s.score ?? '—'} 分`} />
      <Group title="🚀 發動中" items={launched} tag={(s) => '近日發動'} />
      <Group title="💤 已淘汰" items={dropped} tag={(s) => '已掉出榜'} />
      <div className="wr-note">跡象非保證，研究起點</div>
    </section>
  )
}
```

`src/lib/loadDay.js` 加（沿用檔內既有的 base 前綴變數/寫法）：

```js
export function loadPotentialHistory() {
  return fetch(`${BASE}data/potential_history.json`).then((r) => r.ok ? r.json() : { stocks: {} }).catch(() => ({ stocks: {} }))
}
```

（`BASE` 依 loadDay.js 內既有實作命名為準——實作時先讀該檔確認前綴變數怎麼取。）

`src/App.jsx` 台股 grid，`<Radar .../>` 之後加：

```jsx
<WarRoom potential={day.potential} date={date} onOpen={openChart} />
```

並在頂部 import：`import WarRoom from './components/WarRoom.jsx'`

- [ ] **Step 6: 樣式（白瓷粉 tokens）**

`src/styles.css` 追加：

```css
.wr-group{ margin:10px 0; }
.wr-title{ font-weight:700; font-size:13px; color:var(--ink,#2E2733); margin-bottom:6px; }
.wr-rows{ display:grid; gap:6px; }
.wr-row{ display:flex; justify-content:space-between; align-items:center; gap:8px;
  background:rgba(255,255,255,.5); border:1px solid rgba(150,90,140,.15);
  border-radius:10px; padding:8px 12px; cursor:pointer; text-align:left; width:100%; }
.wr-code{ color:#9a8b98; font-size:12px; margin-left:6px; font-family:'IBM Plex Mono',monospace; }
.wr-meta{ font-size:12px; color:var(--muted,#938799); white-space:nowrap; }
.wr-note{ font-size:11px; color:#9a8b98; opacity:.8; margin-top:6px; }
```

- [ ] **Step 7: build + headless 截圖**

Run: `npm test && npm run build`
Expected: 測試 PASS、build 成功。以注入示範 `potential_history.json` 的方式（同 Phase A 截圖法）headless 截作戰室手機版，發 Andy。

- [ ] **Step 8: Commit**

```bash
git add src/lib/loadDay.js src/lib/warroom.js src/components/WarRoom.jsx src/App.jsx src/styles.css src/lib/tests/warroom.test.js
git commit -m "feat(ui): 潛力股作戰室（觀察中/發動中/已淘汰）"
```

---

## 完工驗收（Phase B）

- [ ] 全測試綠：`python3 -m pytest scripts/tests/ -q` 且 `npm test`
- [ ] `npm run build` 成功
- [ ] `POTENTIAL_ALERTS` 未設時，即使偵測到發動也**只印不推**（不洗群組）
- [ ] 作戰室三組手機版截圖 → 發 Andy
- [ ] 部署：`git push` main → `gh workflow run daily.yml` → 綠燈；線上出現作戰室、潛力卡片有基本面分項
- [ ] 跟 Andy 確認發動門檻（`breakout_pct`/`track_days`）後，再由他決定把 `POTENTIAL_ALERTS=1` 加進 GitHub Secret/workflow 啟用提醒

## Self-Review 對照 spec（Phase B 段）

- 基本面分：Task 1 ✔（月營收 YoY、四子分重配權重）。
- 歷史追蹤/連續在榜天數：Task 2 ✔。
- 發動提醒：Task 3 ✔（偵測＋推播，旗標控管避免未確認就洗群組——比 spec 多的安全設計）。
- 作戰室：Task 4 ✔（觀察中/發動中/已淘汰三組）。
- 型別一致：`build_potential` 產 `fund_s/fund_yoy`；`finalize_scores` 讀 chip_s/struct_s/fund_s 產 score_parts{chip,struct,theme,fund}；`update_history` 產 streak/first_date/alerted_date，前端 `groupWarRoom` 讀同名欄位 ✔。
- 無 placeholder：各步驟含實碼與指令；`loadDay.js` 的 `BASE` 前綴標明「以該檔既有實作為準」需實作時確認 ✔。
