# 低基期潛力雷達 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在既有儀表板的「資金流雷達」區新增一個「低基期潛力」模式，找出低基期＋法人吸籌＋有題材/發酵點的台股。

**Architecture:** 沿用每日管線（GitHub Actions `daily.yml` 18:36）。在 `auto_daily` 產出 `day` 後，新增獨立漏斗：籌碼近 N 日聚合（用已存 day.json）→ 吸籌候選 → 只對候選查 FinMind 一年日 K 算低基期 → OpenAI 對最終候選貼題材＋查發酵點 → 寫入 `day["potential"]`。前端 `Radar.jsx` 加模式切換，新元件 `PotentialRadar.jsx` 呈現。

**Tech Stack:** Python 3（pytest）、Vite + React 18（vitest）、FinMind API、OpenAI（gpt-4o-search-preview，urllib）。

## Global Constraints

- Python 測試：`python -m pytest scripts/tests/<file> -v`；JS 測試：`npx vitest run <file>`。
- **部署一律走 CI**：`gh workflow run daily.yml`；**禁止本機 `npm run deploy`**（本機 public/data 會覆蓋線上成舊資料）。
- `potential` 區塊**獨立**：其產製失敗（FinMind/OpenAI 掛）**不得**影響主戰報數據與推播 → 整段包 try/except。
- 所有 potential 輸出標「跡象非保證、研究起點」。
- FinMind 免費層：抓不到/額度滿該股標 `history:"missing"` 跳過，呼叫間 sleep 避免限流。
- 門檻常數集中在 `scripts/lib/potential.py` 的 `DEFAULTS`，方便調整。預設：`window=5, inst_min_yi=1.0(億), pct_max=3.0(%), cand_max=30, pos_max=0.40, chg6m_max=0.15`。
- 毛玻璃卡片內若放 modal 要用 `createPortal` 到 body（已知踩雷）；本功能 K 線沿用父層 `onOpen`，不自建 modal。

## File Structure

- **Create** `scripts/lib/potential.py` — 低基期潛力核心（籌碼聚合、候選篩選、低基期指標、FinMind 抓取、組裝）。
- **Create** `scripts/tests/test_potential.py` — 上述純函式測試。
- **Modify** `scripts/gen_soft_openai.py` — 加 `annotate_potential(stocks)`（OpenAI 貼題材＋發酵點）。
- **Modify** `scripts/tests/test_gen_soft.py` — `annotate_potential` 容錯測試（mock）。
- **Modify** `scripts/auto_daily.py` — 主流程接入 potential（try/except 獨立）。
- **Modify** `scripts/lib/schema.py` — `validate_day` 容許可選 `potential`。
- **Create** `src/components/PotentialRadar.jsx` — 低基期潛力視圖（散佈圖＋候選卡＋空狀態）。
- **Create** `src/lib/potential.js` + `src/lib/tests/potential.test.js` — 前端純函式（象限/黃金區判定、格式）。
- **Modify** `src/components/Radar.jsx` — 加模式切換（象限｜低基期潛力），渲染 `PotentialRadar`。
- **Modify** `src/App.jsx` — 傳 `potential={day.potential}` 給 Radar（第 121 行）。
- **Modify** `src/styles.css` — potential 模式樣式。

---

### Task 1: 籌碼近 N 日聚合

**Files:**
- Create: `scripts/lib/potential.py`
- Test: `scripts/tests/test_potential.py`

**Interfaces:**
- Produces: `DEFAULTS: dict`、`aggregate_chips(days: list[dict], window: int) -> dict[str, dict]`。`days` 為由舊到新的 radar dict 串列（每個含 `{"stocks":[{code,name,pct,inst_net_yi,value_yi,sector}]}`）。回傳 `code -> {code,name,sector,pct,value_yi,inst_net_yi}`，其中 `inst_net_yi` 為視窗內加總，其餘取最新一天出現值。

- [ ] **Step 1: 寫失敗測試**

```python
# scripts/tests/test_potential.py
from scripts.lib import potential


def _radar(stocks):
    return {"stocks": stocks}


def test_aggregate_chips_sums_inst_and_takes_latest_meta():
    days = [
        _radar([{"code": "1111", "name": "舊名", "pct": -1.0, "inst_net_yi": 0.5,
                 "value_yi": 3.0, "sector": "塑膠"}]),
        _radar([{"code": "1111", "name": "新名", "pct": 0.8, "inst_net_yi": 1.2,
                 "value_yi": 4.0, "sector": "塑膠"}]),
    ]
    agg = potential.aggregate_chips(days, window=5)
    assert agg["1111"]["inst_net_yi"] == 1.7      # 0.5 + 1.2
    assert agg["1111"]["name"] == "新名"           # 最新
    assert agg["1111"]["pct"] == 0.8               # 最新
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest scripts/tests/test_potential.py -v`
Expected: FAIL（`AttributeError: module ... has no attribute 'aggregate_chips'`）

- [ ] **Step 3: 實作**

```python
# scripts/lib/potential.py
"""低基期潛力雷達：籌碼近N日聚合 → 吸籌候選 → FinMind 低基期 → 組裝。

此模組獨立於主戰報，呼叫端須自行 try/except，失敗不得影響主報告。
"""
from __future__ import annotations

DEFAULTS = {
    "window": 5,        # 籌碼累積天數
    "inst_min_yi": 1.0, # 近N日法人淨買超門檻（億）
    "pct_max": 3.0,     # 當日/最新漲幅上限（%），還沒起漲
    "cand_max": 30,     # 吸籌候選上限
    "pos_max": 0.40,    # 股價位置上限（0~1，越低越低基期）
    "chg6m_max": 0.15,  # 近半年漲幅上限
}


def aggregate_chips(days: list[dict], window: int) -> dict[str, dict]:
    """days 由舊到新；取最後 window 天，法人淨買超加總、其餘欄位取最新。"""
    recent = [d for d in days if d][-window:]
    agg: dict[str, dict] = {}
    for d in recent:
        for s in d.get("stocks", []):
            code = s.get("code")
            if not code:
                continue
            a = agg.setdefault(code, {"code": code, "inst_net_yi": 0.0})
            a["inst_net_yi"] = round(a["inst_net_yi"] + (s.get("inst_net_yi") or 0), 2)
            a["name"] = s.get("name")
            a["pct"] = s.get("pct")
            a["value_yi"] = s.get("value_yi")
            a["sector"] = s.get("sector")
    return agg
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest scripts/tests/test_potential.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/potential.py scripts/tests/test_potential.py
git commit -m "feat(potential): 籌碼近N日聚合 aggregate_chips"
```

---

### Task 2: 吸籌候選篩選

**Files:**
- Modify: `scripts/lib/potential.py`
- Test: `scripts/tests/test_potential.py`

**Interfaces:**
- Consumes: `aggregate_chips` 的輸出。
- Produces: `pick_accumulators(agg: dict, inst_min_yi: float, pct_max: float, cand_max: int) -> list[dict]`。回法人淨買超 ≥ `inst_min_yi` 且 `pct ≤ pct_max` 的股，依 `inst_net_yi` 由大到小取前 `cand_max`。

- [ ] **Step 1: 寫失敗測試**

```python
def test_pick_accumulators_filters_and_ranks():
    agg = {
        "A": {"code": "A", "inst_net_yi": 5.0, "pct": 0.5},   # 收
        "B": {"code": "B", "inst_net_yi": 0.3, "pct": 0.5},   # 淘汰：吸籌不足
        "C": {"code": "C", "inst_net_yi": 9.0, "pct": 6.0},   # 淘汰：已起漲
        "D": {"code": "D", "inst_net_yi": 2.0, "pct": -1.0},  # 收
    }
    out = potential.pick_accumulators(agg, inst_min_yi=1.0, pct_max=3.0, cand_max=10)
    assert [s["code"] for s in out] == ["A", "D"]   # 依吸籌排序
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest scripts/tests/test_potential.py::test_pick_accumulators_filters_and_ranks -v`
Expected: FAIL

- [ ] **Step 3: 實作**（append 到 `scripts/lib/potential.py`）

```python
def pick_accumulators(agg: dict, inst_min_yi: float, pct_max: float,
                      cand_max: int) -> list[dict]:
    cands = [
        s for s in agg.values()
        if (s.get("inst_net_yi") or 0) >= inst_min_yi
        and (s.get("pct") if s.get("pct") is not None else 999) <= pct_max
    ]
    cands.sort(key=lambda s: s["inst_net_yi"], reverse=True)
    return cands[:cand_max]
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest scripts/tests/test_potential.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/potential.py scripts/tests/test_potential.py
git commit -m "feat(potential): 吸籌候選篩選 pick_accumulators"
```

---

### Task 3: 低基期指標計算

**Files:**
- Modify: `scripts/lib/potential.py`
- Test: `scripts/tests/test_potential.py`

**Interfaces:**
- Produces: `low_base_metrics(rows: list[dict]) -> dict | None`。`rows` 為 FinMind 日 K（由舊到新，每筆含 `date, close, max, min`）。回 `{"price_pos": float, "chg_6m": float}`：`price_pos=(close-low_1y)/(high_1y-low_1y)`；`chg_6m=close/close_約6個月前-1`（取日期最接近「最後一天往前 182 天」的那筆）。資料不足（<20 筆或高低相等）回 `None`。

- [ ] **Step 1: 寫失敗測試**

```python
def test_low_base_metrics_basic():
    # 造 200 筆：價格從 100 緩跌到 50，最後收 55
    rows = []
    for i in range(200):
        c = 100 - i * 0.25          # 100 → 50.25
        rows.append({"date": f"2025-{(i%12)+1:02d}-01", "close": c,
                     "max": c + 1, "min": c - 1})
    rows[-1]["close"] = 55.0
    m = potential.low_base_metrics(rows)
    assert m is not None
    assert 0.0 <= m["price_pos"] <= 0.4      # 收在區間下緣
    assert m["chg_6m"] < 0                     # 近半年是跌的


def test_low_base_metrics_insufficient():
    assert potential.low_base_metrics([{"date": "2025-01-01", "close": 10,
                                        "max": 10, "min": 10}]) is None
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest scripts/tests/test_potential.py -k low_base_metrics -v`
Expected: FAIL

- [ ] **Step 3: 實作**（append）

```python
import datetime as _dt


def low_base_metrics(rows: list[dict]) -> dict | None:
    rows = [r for r in rows if r.get("close") is not None][-260:]
    if len(rows) < 20:
        return None
    highs = [r["max"] for r in rows if r.get("max") is not None]
    lows = [r["min"] for r in rows if r.get("min") is not None]
    if not highs or not lows:
        return None
    hi, lo = max(highs), min(lows)
    if hi == lo:
        return None
    close = rows[-1]["close"]
    price_pos = round((close - lo) / (hi - lo), 3)

    def _d(s):
        try:
            return _dt.date.fromisoformat(s)
        except Exception:
            return None
    last_d = _d(rows[-1]["date"])
    ref = None
    if last_d:
        target = last_d - _dt.timedelta(days=182)
        ref = min(
            (r for r in rows if _d(r["date"])),
            key=lambda r: abs((_d(r["date"]) - target).days),
            default=None,
        )
    base = ref["close"] if ref and ref["close"] else rows[0]["close"]
    chg_6m = round(close / base - 1, 4) if base else 0.0
    return {"price_pos": price_pos, "chg_6m": chg_6m}
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest scripts/tests/test_potential.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/potential.py scripts/tests/test_potential.py
git commit -m "feat(potential): 低基期指標計算 low_base_metrics"
```

---

### Task 4: FinMind 抓取（可注入、容錯）

**Files:**
- Modify: `scripts/lib/potential.py`
- Test: `scripts/tests/test_potential.py`

**Interfaces:**
- Produces: `finmind_history(code: str, start_date: str) -> list[dict]`。打 `https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&data_id=<code>&start_date=<start_date>`，回 `data`（含 `date/open/max/min/close`）；任何錯誤回 `[]`（不拋例外）。

- [ ] **Step 1: 寫失敗測試**（用 monkeypatch 模擬 urlopen）

```python
import io, json as _json


def test_finmind_history_parses(monkeypatch):
    payload = {"data": [{"date": "2025-01-02", "open": 1, "max": 2,
                         "min": 0.5, "close": 1.5}]}

    class _Resp(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): return False
    def fake_urlopen(req, timeout=0):
        return _Resp(_json.dumps(payload).encode())
    monkeypatch.setattr(potential.urllib.request, "urlopen", fake_urlopen)
    rows = potential.finmind_history("1234", "2024-07-01")
    assert rows and rows[0]["close"] == 1.5


def test_finmind_history_tolerates_error(monkeypatch):
    def boom(req, timeout=0):
        raise OSError("quota")
    monkeypatch.setattr(potential.urllib.request, "urlopen", boom)
    assert potential.finmind_history("1234", "2024-07-01") == []
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest scripts/tests/test_potential.py -k finmind -v`
Expected: FAIL

- [ ] **Step 3: 實作**（append；於檔案頂部 import 區加 `import urllib.request, json`）

```python
import urllib.request
import json

FINMIND_API = "https://api.finmindtrade.com/api/v4/data"


def finmind_history(code: str, start_date: str) -> list[dict]:
    url = (f"{FINMIND_API}?dataset=TaiwanStockPrice"
           f"&data_id={code}&start_date={start_date}")
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.load(r)
        return data.get("data") or []
    except Exception:
        return []
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest scripts/tests/test_potential.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/potential.py scripts/tests/test_potential.py
git commit -m "feat(potential): FinMind 一年日K 抓取(容錯)"
```

---

### Task 5: 低基期篩選 orchestrate

**Files:**
- Modify: `scripts/lib/potential.py`
- Test: `scripts/tests/test_potential.py`

**Interfaces:**
- Consumes: `low_base_metrics`、`finmind_history`。
- Produces: `filter_low_base(cands: list[dict], start_date: str, pos_max: float, chg6m_max: float, fetch=finmind_history, sleep_s: float = 0.3) -> list[dict]`。對每檔抓歷史→算指標；通過門檻者附上 `price_pos/chg_6m/history:"ok"` 收入；抓不到者略過（不收）。回通過清單。

- [ ] **Step 1: 寫失敗測試**（注入假 fetch，不碰網路）

```python
def test_filter_low_base_keeps_only_low_base():
    cands = [{"code": "LOW", "inst_net_yi": 3.0},
             {"code": "HIGH", "inst_net_yi": 2.0},
             {"code": "MISS", "inst_net_yi": 1.0}]

    def fake_fetch(code, start):
        if code == "LOW":   # 收在下緣、半年下跌
            return [{"date": "2024-07-01", "close": 100, "max": 100, "min": 30}
                    ] * 1 + [{"date": f"2025-{(i%12)+1:02d}-15", "close": 40,
                              "max": 41, "min": 39} for i in range(30)]
        if code == "HIGH":  # 收在高檔
            return [{"date": f"2025-{(i%12)+1:02d}-15", "close": 95,
                     "max": 100, "min": 30} for i in range(30)]
        return []           # MISS：抓不到

    out = potential.filter_low_base(cands, "2024-07-01", pos_max=0.4,
                                    chg6m_max=0.15, fetch=fake_fetch, sleep_s=0)
    codes = [s["code"] for s in out]
    assert "LOW" in codes and "HIGH" not in codes and "MISS" not in codes
    low = next(s for s in out if s["code"] == "LOW")
    assert low["history"] == "ok" and "price_pos" in low
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest scripts/tests/test_potential.py -k filter_low_base -v`
Expected: FAIL

- [ ] **Step 3: 實作**（append；頂部 import 加 `import time`）

```python
import time


def filter_low_base(cands: list[dict], start_date: str, pos_max: float,
                    chg6m_max: float, fetch=finmind_history,
                    sleep_s: float = 0.3) -> list[dict]:
    out = []
    for c in cands:
        rows = fetch(c["code"], start_date)
        if sleep_s:
            time.sleep(sleep_s)
        if not rows:
            continue
        m = low_base_metrics(rows)
        if not m:
            continue
        if m["price_pos"] <= pos_max and m["chg_6m"] <= chg6m_max:
            out.append({**c, **m, "history": "ok"})
    return out
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest scripts/tests/test_potential.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/potential.py scripts/tests/test_potential.py
git commit -m "feat(potential): 低基期篩選 filter_low_base"
```

---

### Task 6: build_potential 主組裝

**Files:**
- Modify: `scripts/lib/potential.py`
- Test: `scripts/tests/test_potential.py`

**Interfaces:**
- Consumes: 前述全部。
- Produces: `build_potential(days: list[dict], start_date: str, cfg: dict | None = None, fetch=finmind_history, sleep_s: float = 0.3) -> dict`。回 `{"window_days": int, "stocks": [...]}`（stocks 尚無 theme/catalyst，Task 7 補）。`cfg` 未給用 `DEFAULTS`。

- [ ] **Step 1: 寫失敗測試**

```python
def test_build_potential_end_to_end():
    days = [{"stocks": [
        {"code": "LOW", "name": "低基", "pct": 0.5, "inst_net_yi": 3.0,
         "value_yi": 5.0, "sector": "電機"},
        {"code": "HOT", "name": "熱門", "pct": 8.0, "inst_net_yi": 9.0,
         "value_yi": 5.0, "sector": "半導體"},
    ]}]

    def fake_fetch(code, start):
        return [{"date": f"2025-{(i%12)+1:02d}-15", "close": 40, "max": 41,
                 "min": 39} for i in range(30)] + \
               [{"date": "2024-07-01", "close": 100, "max": 100, "min": 30}]

    out = potential.build_potential(days, "2024-07-01", fetch=fake_fetch, sleep_s=0)
    assert out["window_days"] == potential.DEFAULTS["window"]
    codes = [s["code"] for s in out["stocks"]]
    assert "LOW" in codes and "HOT" not in codes   # HOT 漲幅過大被吸籌關淘汰
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest scripts/tests/test_potential.py -k build_potential -v`
Expected: FAIL

- [ ] **Step 3: 實作**（append）

```python
def build_potential(days: list[dict], start_date: str, cfg: dict | None = None,
                    fetch=finmind_history, sleep_s: float = 0.3) -> dict:
    cfg = {**DEFAULTS, **(cfg or {})}
    agg = aggregate_chips(days, cfg["window"])
    cands = pick_accumulators(agg, cfg["inst_min_yi"], cfg["pct_max"],
                              cfg["cand_max"])
    stocks = filter_low_base(cands, start_date, cfg["pos_max"], cfg["chg6m_max"],
                             fetch=fetch, sleep_s=sleep_s)
    return {"window_days": cfg["window"], "stocks": stocks}
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest scripts/tests/test_potential.py -v`
Expected: PASS（全部）

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/potential.py scripts/tests/test_potential.py
git commit -m "feat(potential): build_potential 主組裝"
```

---

### Task 7: AI 題材＋潛在發酵點標註

**Files:**
- Modify: `scripts/gen_soft_openai.py`
- Test: `scripts/tests/test_gen_soft.py`

**Interfaces:**
- Produces: `annotate_potential(stocks: list[dict]) -> None`（原地修改）。對每檔加 `theme`（題材標籤，查不到用 `sector`）與 `catalyst`（🌱潛在發酵點一句，查不到 `""`）。無 `OPENAI_API_KEY`、或 API/解析失敗 → 全部 fallback（theme=sector、catalyst=""），**不拋例外**。空清單直接返回。

- [ ] **Step 1: 寫失敗測試**

```python
# scripts/tests/test_gen_soft.py（新增）
from scripts.gen_soft_openai import annotate_potential


def test_annotate_potential_fallback_no_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    stocks = [{"code": "1234", "name": "某某", "sector": "電機"}]
    annotate_potential(stocks)
    assert stocks[0]["theme"] == "電機"      # fallback 用產業別
    assert stocks[0]["catalyst"] == ""


def test_annotate_potential_empty_ok():
    annotate_potential([])   # 不得拋錯
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest scripts/tests/test_gen_soft.py -k annotate_potential -v`
Expected: FAIL

- [ ] **Step 3: 實作**（append 到 `scripts/gen_soft_openai.py`；沿用檔內既有 `MODEL/API/_extract_json/urllib/json/os`）

```python
POTENTIAL_PROMPT = (
    "你是台股研究助理。以下是幾檔『低基期且法人默默吸籌』的股票，"
    "請為每檔判斷所屬『未來題材』標籤（如 AI 散熱、機器人、矽光子、重電…；"
    "只給一個最貼切的短標籤），並上網查是否有『正在醞釀、還沒被市場廣泛注意』"
    "的催化劑（即將法說、新產品、政策、轉單、產業拐點），寫成一句 catalyst"
    "（查不到就給空字串）。catalyst 是線索非保證，不得杜撰。\n"
    "只輸出 JSON 陣列，每筆 {code, theme, catalyst}。\n股票：\n"
)


def annotate_potential(stocks: list[dict]) -> None:
    if not stocks:
        return

    def _fallback():
        for s in stocks:
            s.setdefault("theme", s.get("sector") or "")
            s.setdefault("catalyst", "")

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        _fallback()
        return
    try:
        listing = "\n".join(
            f"{s['code']} {s.get('name','')}（{s.get('sector','')}）" for s in stocks
        )
        body = {
            "model": MODEL,
            "web_search_options": {},
            "messages": [{"role": "user", "content": POTENTIAL_PROMPT + listing}],
        }
        req = urllib.request.Request(
            API, data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.load(r)
        content = resp["choices"][0]["message"]["content"]
        notes = _extract_json(content)
        by_code = {n.get("code"): n for n in notes} if isinstance(notes, list) else {}
        for s in stocks:
            n = by_code.get(s["code"], {})
            s["theme"] = (n.get("theme") or s.get("sector") or "").strip()
            s["catalyst"] = (n.get("catalyst") or "").strip()
    except Exception:
        _fallback()
```

> 註：若 `_extract_json` 目前只支援物件，需確認它能回陣列；不行則在此就地 `json.loads` 容錯（已包在 try 內）。

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest scripts/tests/test_gen_soft.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/gen_soft_openai.py scripts/tests/test_gen_soft.py
git commit -m "feat(potential): AI 題材+發酵點標註 annotate_potential"
```

---

### Task 8: 管線接入 auto_daily + schema 相容

**Files:**
- Modify: `scripts/auto_daily.py`（`day = merge_day(...)` 之後、`(DATA_DIR / f"{date}.json").write_text(...)` 之前）
- Modify: `scripts/lib/schema.py`（`validate_day` 容許可選 `potential`）
- Test: `scripts/tests/test_schema.py`

**Interfaces:**
- Consumes: `build_potential`、`annotate_potential`、`DATA_DIR`。
- Produces: `day["potential"]`（成功時）；schema 對有/無 `potential` 皆通過。

- [ ] **Step 1: 寫失敗測試（schema 容許 potential）**

```python
# scripts/tests/test_schema.py（新增一條）
from scripts.lib.schema import validate_day
# 取現成的最小合法 day（沿用該檔既有的建構 helper / fixture），加上 potential 後仍應無錯：
def test_validate_day_accepts_potential(minimal_day):   # minimal_day = 既有 fixture
    minimal_day["potential"] = {"window_days": 5, "stocks": [
        {"code": "1234", "name": "x", "pct": 0.1, "inst_net_yi": 1.0,
         "price_pos": 0.2, "chg_6m": 0.0, "theme": "重電",
         "catalyst": "", "sector": "電機", "history": "ok"}]}
    assert validate_day(minimal_day) == []
```

> 若 `test_schema.py` 沒有 `minimal_day` fixture，先照該檔既有做法建一個合法 day dict 再加 `potential`。

- [ ] **Step 2: 跑測試確認失敗（或確認 validate_day 尚未處理 potential）**

Run: `python -m pytest scripts/tests/test_schema.py -k potential -v`
Expected: FAIL 或需求釐清

- [ ] **Step 3a: schema 放行 potential**

`validate_day` 若採「白名單鍵」邏輯，將 `"potential"` 加入允許的可選鍵；若採「檢查必填鍵存在」邏輯，則本來就會忽略多餘鍵、只需確認不會因多鍵報錯。實作為在 `validate_day` 內對 `potential` 做寬鬆檢查（存在時 stocks 必為 list）：

```python
# scripts/lib/schema.py，於 validate_day 內 return errs 之前加：
    pot = data.get("potential")
    if pot is not None and not isinstance(pot.get("stocks"), list):
        errs.append("potential.stocks 應為陣列")
```

- [ ] **Step 3b: auto_daily 接入（try/except 獨立，不影響主報告）**

於 `scripts/auto_daily.py` 頂部 import 區加：

```python
from scripts.lib.potential import build_potential
from scripts.gen_soft_openai import annotate_potential
```

於 `day["_warnings"] = collect_warnings(day)` 之後、寫檔之前插入：

```python
    # 低基期潛力雷達（獨立區塊，失敗不影響主戰報）
    try:
        import datetime as _dt
        history = []
        for p in sorted(DATA_DIR.glob("[0-9]*.json")):
            try:
                dd = json.loads(p.read_text(encoding="utf-8"))
                if dd.get("radar"):
                    history.append(dd["radar"])
            except Exception:
                pass
        if day.get("radar"):
            history.append(day["radar"])   # 含今天
        start = (_dt.date.fromisoformat(date) - _dt.timedelta(days=400)).isoformat()
        pot = build_potential(history, start)
        annotate_potential(pot["stocks"])
        day["potential"] = pot
        print(f"低基期潛力：候選 {len(pot['stocks'])} 檔")
    except Exception as e:
        print(f"⚠️ 低基期潛力雷達略過（不影響主戰報）：{e}")
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest scripts/tests/test_schema.py scripts/tests/test_auto_daily.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/auto_daily.py scripts/lib/schema.py scripts/tests/test_schema.py
git commit -m "feat(potential): 接入 auto_daily 管線 + schema 相容"
```

---

### Task 9: 前端純函式（黃金區/格式）

**Files:**
- Create: `src/lib/potential.js`
- Test: `src/lib/tests/potential.test.js`

**Interfaces:**
- Produces: `isGolden(s, posMax=0.4) -> boolean`（低基期＋吸籌＝price_pos≤posMax 且 inst_net_yi>0）；`fmtPct(x) -> string`（如 `+6.0%`）。

- [ ] **Step 1: 寫失敗測試**

```javascript
// src/lib/tests/potential.test.js
import { describe, it, expect } from 'vitest'
import { isGolden, fmtPct } from '../potential.js'

describe('potential helpers', () => {
  it('isGolden: 低基期且法人買', () => {
    expect(isGolden({ price_pos: 0.2, inst_net_yi: 3 })).toBe(true)
    expect(isGolden({ price_pos: 0.8, inst_net_yi: 3 })).toBe(false)
    expect(isGolden({ price_pos: 0.2, inst_net_yi: -1 })).toBe(false)
  })
  it('fmtPct', () => {
    expect(fmtPct(0.06)).toBe('+6.0%')
    expect(fmtPct(-0.153)).toBe('-15.3%')
  })
})
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `npx vitest run src/lib/tests/potential.test.js`
Expected: FAIL

- [ ] **Step 3: 實作**

```javascript
// src/lib/potential.js
export function isGolden(s, posMax = 0.4) {
  return (s?.price_pos ?? 1) <= posMax && (s?.inst_net_yi ?? 0) > 0
}
export function fmtPct(x) {
  const v = (x ?? 0) * 100
  return `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`
}
```

- [ ] **Step 4: 跑測試確認通過**

Run: `npx vitest run src/lib/tests/potential.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/lib/potential.js src/lib/tests/potential.test.js
git commit -m "feat(potential): 前端 helpers isGolden/fmtPct"
```

---

### Task 10: PotentialRadar 元件

**Files:**
- Create: `src/components/PotentialRadar.jsx`

**Interfaces:**
- Consumes: `isGolden`、`fmtPct`；props `{ potential, onOpen }`（`onOpen(code)` 開 K 線，沿用 Radar 現有的 `onOpen`）。
- Produces: `export default function PotentialRadar`。

- [ ] **Step 1: 實作元件**

```jsx
// src/components/PotentialRadar.jsx
import { isGolden, fmtPct } from '../lib/potential.js'

export default function PotentialRadar({ potential, onOpen }) {
  const stocks = potential?.stocks || []
  if (!stocks.length) {
    return (
      <div className="pot-empty">
        今日無低基期吸籌標的。<br />
        <span className="pot-note">（跡象非保證，研究起點）</span>
      </div>
    )
  }
  // 散佈圖座標：X=股價位置(0低→1高)、Y=法人吸籌
  const maxInst = Math.max(...stocks.map((s) => s.inst_net_yi || 0), 1)
  return (
    <div className="pot-wrap">
      <svg className="pot-scatter" viewBox="0 0 100 60" preserveAspectRatio="none">
        <rect x="0" y="0" width="40" height="30" className="pot-gold" />
        {stocks.map((s) => {
          const x = Math.min(1, Math.max(0, s.price_pos)) * 100
          const y = 60 - ((s.inst_net_yi || 0) / maxInst) * 58
          return (
            <circle key={s.code} cx={x} cy={y} r="1.6"
              className={isGolden(s) ? 'pot-dot on' : 'pot-dot'}
              onClick={() => onOpen && onOpen(s.code)} />
          )
        })}
      </svg>
      <div className="pot-axis"><span>← 低基期</span><span>法人吸籌 ↑</span></div>

      <div className="pot-list">
        {stocks.map((s) => (
          <div key={s.code} className={isGolden(s) ? 'pot-card gold' : 'pot-card'}>
            <div className="pot-head">
              <button className="pot-name" onClick={() => onOpen && onOpen(s.code)}>
                {s.name} <span className="pot-code">{s.code}</span>
              </button>
              {s.theme && <span className="pot-tag">🏷️ {s.theme}</span>}
            </div>
            <div className="pot-metrics">
              <span>位置 {Math.round((s.price_pos ?? 0) * 100)}%</span>
              <span>近半年 {fmtPct(s.chg_6m)}</span>
              <span>法人 {(s.inst_net_yi ?? 0).toFixed(1)} 億</span>
            </div>
            {s.catalyst && <div className="pot-cat">🌱 {s.catalyst}</div>}
          </div>
        ))}
      </div>
      <div className="pot-note">跡象非保證，研究起點</div>
    </div>
  )
}
```

- [ ] **Step 2: 建置驗證（無測試的元件靠 build 把關）**

Run: `npm run build`
Expected: build 成功、無 import/語法錯

- [ ] **Step 3: Commit**

```bash
git add src/components/PotentialRadar.jsx
git commit -m "feat(potential): PotentialRadar 視圖元件"
```

---

### Task 11: Radar 模式切換 + App 傳 prop + 樣式

**Files:**
- Modify: `src/components/Radar.jsx`（頂部加模式切換與條件渲染）
- Modify: `src/App.jsx:121`（傳 `potential`）
- Modify: `src/styles.css`（potential 樣式）

**Interfaces:**
- Consumes: `PotentialRadar`。
- Radar 新增 prop `potential`；`day.potential` 由 App 傳入。

- [ ] **Step 1: App 傳 prop**

`src/App.jsx` 第 121 行改為：

```jsx
            <Radar radar={day.radar} potential={day.potential} dates={dates} date={date} onOpen={openChart} />
```

- [ ] **Step 2: Radar 加模式切換**

在 `src/components/Radar.jsx`：
1. 頂部 import：`import PotentialRadar from './PotentialRadar.jsx'`
2. 函式簽名加 `potential`：`export default function Radar({ radar, potential, dates, date, onOpen }) {`
3. 元件內加狀態：`const [mode, setMode] = React.useState('quad')`（若檔案用具名 import 的 `useState`，改用之）。
4. 在雷達區標題列下方加模式切換鈕，並條件渲染：

```jsx
      <div className="pmode">
        <button className={mode === 'quad' ? 'pmode-btn on' : 'pmode-btn'}
          onClick={() => setMode('quad')}>象限</button>
        <button className={mode === 'potential' ? 'pmode-btn on' : 'pmode-btn'}
          onClick={() => setMode('potential')}>🌱 低基期潛力</button>
      </div>
      {mode === 'potential'
        ? <PotentialRadar potential={potential} onOpen={onOpen} />
        : (/* ← 這裡包住 Radar 原本的象限散佈圖＋清單 JSX */)}
```

> 執行時：先讀 `Radar.jsx` 全文，確認 `useState` 的 import 方式與原本 return 的 JSX 邊界，把象限原內容原封不動放進 `:` 後的分支，不改動其邏輯。

- [ ] **Step 3: 樣式**（append 到 `src/styles.css`）

```css
/* 低基期潛力雷達 */
.pmode { display: flex; gap: 8px; margin: 8px 0 12px; }
.pmode-btn { padding: 5px 12px; border-radius: 999px; border: 1px solid rgba(150,90,140,.25);
  background: transparent; color: var(--ink, #6b5566); font-size: 13px; cursor: pointer; }
.pmode-btn.on { background: var(--gold, #CC5283); color: #fff; border-color: transparent; }
.pot-wrap { display: flex; flex-direction: column; gap: 10px; }
.pot-scatter { width: 100%; height: 180px; background: rgba(150,90,140,.04);
  border-radius: 12px; }
.pot-gold { fill: rgba(204,82,131,.10); }
.pot-dot { fill: #9aa; cursor: pointer; }
.pot-dot.on { fill: var(--gold, #CC5283); }
.pot-axis { display: flex; justify-content: space-between; font-size: 11px;
  color: #9a8; opacity: .7; }
.pot-list { display: grid; gap: 10px; }
.pot-card { padding: 10px 12px; border-radius: 12px; border: 1px solid rgba(150,90,140,.15);
  background: rgba(255,255,255,.5); }
.pot-card.gold { border-color: var(--gold, #CC5283); }
.pot-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.pot-name { background: none; border: none; font-weight: 700; cursor: pointer;
  color: var(--ink, #4a3547); }
.pot-code { color: #9a8; font-weight: 400; font-size: 12px; }
.pot-tag { font-size: 12px; color: var(--gold, #CC5283); }
.pot-metrics { display: flex; gap: 12px; font-size: 12px; color: #7a6; margin-top: 4px; }
.pot-cat { margin-top: 6px; font-size: 13px; color: #4a3547; }
.pot-note { font-size: 11px; color: #9a8; opacity: .7; }
.pot-empty { padding: 24px; text-align: center; color: #9a8; }
@media (max-width: 640px) { .pot-scatter { height: 150px; } }
```

- [ ] **Step 4: 建置＋測試全綠**

Run: `npm run build && npx vitest run && python -m pytest scripts/tests/ -q`
Expected: build 成功、JS + Python 測試全綠

- [ ] **Step 5: Commit**

```bash
git add src/components/Radar.jsx src/App.jsx src/styles.css
git commit -m "feat(potential): Radar 模式切換 + 低基期潛力視圖接線"
```

---

### Task 12: 端到端本機驗證 + 上線

**Files:** 無（驗證與部署）

- [ ] **Step 1: 本機乾跑管線（不發 TG）**

Run: `OPENAI_API_KEY=<key> python -m scripts.auto_daily --dry-run`
Expected: 印出「低基期潛力：候選 N 檔」；`public/data/<date>.json` 含 `potential`；主戰報摘要照常。

- [ ] **Step 2: 前端本機預覽**

Run: `npm run build && npm run preview`
開瀏覽器 → 台股分頁 → 雷達區切「🌱 低基期潛力」→ 確認散佈圖＋候選卡（題材/發酵點/位置/吸籌）顯示；無候選時顯示空狀態。截圖發 Andy（手機寬 ≥500 截圖，見 headless 截圖下限教訓）。

- [ ] **Step 3: 上線（走 CI，勿本機 deploy）**

```bash
git pull --rebase && git push
gh workflow run daily.yml
gh run watch
```

Expected: CI 綠、線上站切模式看得到低基期潛力（用 `?cb=隨機` 繞 CDN 快取驗證）。

- [ ] **Step 4: 回報 Andy 上線＋提醒門檻可依實際結果微調。**

---

## Self-Review

**1. Spec coverage：**
- 四關漏斗 → Task 1(聚合)/2(吸籌)/3-6(低基期)/7(AI 題材+發酵點) ✅
- 做法 A（籌碼先篩、候選才查歷史）→ Task 6 順序 ✅
- 放進雷達當新模式 → Task 10/11 ✅
- day.json `potential` 格式 → Task 6+7 產出、Task 8 schema ✅
- 錯誤處理（FinMind/AI 容錯、獨立不影響主報、空狀態）→ Task 4/5/7/8/10 ✅
- 測試（Python 指標/篩選/容錯、JS 切換/空狀態）→ 各 Task ✅
- 成本（只查候選）→ Task 5 sleep、Task 6 cand_max ✅
- 標「跡象非保證」→ Task 10 ✅

**2. Placeholder scan：** Task 8/11 有兩處「執行時先讀原檔再插入」的指示（schema 白名單判斷、Radar 既有 JSX 邊界）——這是因為兩處需依現有實作微調，已標明具體插入點與程式碼，非空白占位。其餘皆有完整程式碼。

**3. Type consistency：** `build_potential` 產 `{window_days, stocks[]}`；stocks 欄位 `code/name/pct/inst_net_yi/value_yi/sector/price_pos/chg_6m/history` 由 Task 1/5 定義，Task 7 補 `theme/catalyst`，前端 Task 10 皆對應使用；`isGolden/fmtPct` 簽名一致。
