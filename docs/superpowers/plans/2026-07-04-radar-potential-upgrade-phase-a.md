# 資金流雷達×低基期潛力 升級 Phase A 實作計劃

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓低基期潛力股改用「發動信心分數」排序、雷達介面漸進式揭露＋一年走勢縮圖、每日推播主動點名 Top3。

**Architecture:** 後端 `potential.py` 把單一硬門檻升級為「多子分合成分數」：籌碼分＋價量結構分（落難股過濾關鍵）＋題材分。子分為純函式、可獨立測試；因題材分依賴 AI annotate 後才有的 `catalyst/theme`，最終合成分數在 `annotate_potential` 之後由 `finalize_scores` 計算並排序。前端顯示分數 badge＋sparkline，`Radar.jsx` 加頂部總結列並把進階控制項收摺。推播 `notify.py` 加潛力股 Top3 段。

**Tech Stack:** Python 3（urllib、pytest）、React 18 + Vite（vitest）、FinMind 免費 API（既有）。

## Global Constraints

- 台北時間（Asia/Taipei）；日期字串用 ISO `YYYY-MM-DD`。
- 潛力區塊獨立於主戰報：任何失敗都 try/except 吞掉、不得影響主戰報（沿用 `_attach_potential` 既有保護）。
- 免責文案保留：「跡象非保證，研究起點」。
- 白瓷粉視覺 tokens 不改、不新增字型/配色；僅重整版面。
- 所有新門檻/權重放進 `potential.py` 的 `DEFAULTS`，可調。
- 繁體中文註解，風格與周圍程式一致。
- 測試指令：Python `python3 -m pytest scripts/tests/ -q`；前端 `npm test`（vitest）。

---

## 檔案結構

- `scripts/lib/potential.py`（改）：`aggregate_chips` 加 `buy_days`；`low_base_metrics` 加 `vol_ratio/above_ma60/spark`；新增 `chip_score/structure_score/theme_score/combine_score/finalize_scores`；`build_potential` 掛子分與 metrics、保留低基期 gate；`DEFAULTS` 加權重與 sat 常數。
- `scripts/auto_daily.py`（改 `_attach_potential`）：`build_potential → annotate_potential → finalize_scores` 順序。
- `scripts/notify.py`（改）：新增 `_potential_lines(day)`，插進 `build_summary_text`。
- `src/lib/potential.js`（改）：加 `scoreTier(score)`、`sparkPath(points, w, h)` 純函式。
- `src/components/PotentialRadar.jsx`（改）：分數 badge、依分數排序、sparkline。
- `src/lib/radar.js`（改）：加 `radarSummary(radar, potential)` 純函式。
- `src/components/Radar.jsx`（改）：頂部總結列、進階控制項摺疊。
- `src/styles.css`（改）：分數 badge、sparkline、總結列、摺疊區樣式（白瓷粉 tokens）。
- 測試：`scripts/tests/test_potential.py`（既有，續加）、`scripts/tests/test_notify.py`（既有或新增段）、`src/lib/tests/potential.test.js`（既有，續加）、`src/lib/tests/radar.test.js`（既有，續加）。

---

## Task 1: aggregate_chips 加「近 N 日買超天數」buy_days

**Files:**
- Modify: `scripts/lib/potential.py`（`aggregate_chips`）
- Test: `scripts/tests/test_potential.py`

**Interfaces:**
- Produces: `aggregate_chips(days, window)` 回的每檔 dict 多一欄 `buy_days: int`（近 window 天內該檔 `inst_net_yi > 0` 的天數）。

- [ ] **Step 1: 寫失敗測試**

```python
def test_aggregate_chips_counts_buy_days():
    days = [
        _radar([{"code": "2603", "name": "長榮", "pct": -1.0, "inst_net_yi": 0.5, "value_yi": 3.0, "sector": "航運"}]),
        _radar([{"code": "2603", "name": "長榮", "pct": 0.0, "inst_net_yi": -0.2, "value_yi": 3.0, "sector": "航運"}]),
        _radar([{"code": "2603", "name": "長榮", "pct": 0.3, "inst_net_yi": 1.1, "value_yi": 4.0, "sector": "航運"}]),
    ]
    agg = potential.aggregate_chips(days, window=5)
    assert agg["2603"]["buy_days"] == 2  # 第1、3天買超
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python3 -m pytest scripts/tests/test_potential.py::test_aggregate_chips_counts_buy_days -q`
Expected: FAIL（`KeyError: 'buy_days'`）

- [ ] **Step 3: 最小實作**

在 `aggregate_chips` 迴圈內累加 buy_days：

```python
def aggregate_chips(days: list[dict], window: int) -> dict[str, dict]:
    """days 由舊到新；取最後 window 天，法人淨買超加總、買超天數計數、其餘欄位取最新。"""
    recent = [d for d in days if d][-window:]
    agg: dict[str, dict] = {}
    for d in recent:
        for s in d.get("stocks", []):
            code = s.get("code")
            if not code:
                continue
            a = agg.setdefault(code, {"code": code, "inst_net_yi": 0.0, "buy_days": 0})
            net = s.get("inst_net_yi") or 0
            a["inst_net_yi"] = round(a["inst_net_yi"] + net, 2)
            if net > 0:
                a["buy_days"] += 1
            a["name"] = s.get("name")
            a["pct"] = s.get("pct")
            a["value_yi"] = s.get("value_yi")
            a["sector"] = s.get("sector")
    return agg
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python3 -m pytest scripts/tests/test_potential.py -q`
Expected: PASS（含既有 aggregate 測試）

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/potential.py scripts/tests/test_potential.py
git commit -m "feat(potential): aggregate_chips 計算近N日法人買超天數 buy_days"
```

---

## Task 2: low_base_metrics 擴充 量能比、季線、走勢縮圖

**Files:**
- Modify: `scripts/lib/potential.py`（`low_base_metrics`）
- Test: `scripts/tests/test_potential.py`

**Interfaces:**
- Consumes: FinMind 日 K rows（含 `close/max/min/date/Trading_Volume`）。
- Produces: `low_base_metrics(rows)` 回 dict 多三欄：`vol_ratio: float`（近5日均量 / 前20日均量，量增>1）、`above_ma60: bool`（收盤 ≥ 近60日均價）、`spark: list[float]`（收盤序列降採樣至 ≤52 點、含最後一點）。原有 `price_pos/chg_6m` 不變。

- [ ] **Step 1: 寫失敗測試**

```python
def test_low_base_metrics_adds_vol_ma_spark():
    rows = []
    for i in range(120):
        rows.append({"date": f"2025-{(i//28)+1:02d}-{(i%28)+1:02d}",
                     "close": 100 + i * 0.1, "max": 101 + i * 0.1,
                     "min": 99 + i * 0.1, "Trading_Volume": 1000 + (500 if i >= 115 else 0)})
    m = potential.low_base_metrics(rows)
    assert m["vol_ratio"] > 1.0          # 最後5天爆量
    assert m["above_ma60"] is True       # 緩漲、收盤在季線上
    assert 2 <= len(m["spark"]) <= 52
    assert m["spark"][-1] == rows[-1]["close"]
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python3 -m pytest scripts/tests/test_potential.py::test_low_base_metrics_adds_vol_ma_spark -q`
Expected: FAIL（`KeyError: 'vol_ratio'`）

- [ ] **Step 3: 最小實作**

在 `low_base_metrics` 回傳前計算並加入三欄（沿用已過濾的 `rows`）：

```python
    # 量能比：近5日均量 / 前20日均量（缺量或分母 0 時給 1.0 中性）
    vols = [r.get("Trading_Volume") for r in rows if isinstance(r.get("Trading_Volume"), (int, float))]
    vol_ratio = 1.0
    if len(vols) >= 25:
        recent5 = sum(vols[-5:]) / 5
        prev20 = sum(vols[-25:-5]) / 20
        vol_ratio = round(recent5 / prev20, 2) if prev20 else 1.0

    # 站上季線：收盤 ≥ 近60日均價
    closes = [r["close"] for r in rows if r.get("close") is not None]
    ma60 = sum(closes[-60:]) / len(closes[-60:]) if len(closes) >= 20 else close
    above_ma60 = close >= ma60

    # 走勢縮圖：收盤序列降採樣至 ≤52 點、保底含最後一點
    step = max(1, (len(closes) + 51) // 52)
    spark = closes[::step]
    if spark[-1] != closes[-1]:
        spark.append(closes[-1])

    return {"price_pos": price_pos, "chg_6m": chg_6m,
            "vol_ratio": vol_ratio, "above_ma60": above_ma60,
            "spark": [round(c, 2) for c in spark]}
```

（把原本的 `return {"price_pos": price_pos, "chg_6m": chg_6m}` 換成上面這段；`close` 變數在函式上方已定義。）

- [ ] **Step 4: 跑測試確認通過**

Run: `python3 -m pytest scripts/tests/test_potential.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/potential.py scripts/tests/test_potential.py
git commit -m "feat(potential): low_base_metrics 加量能比/季線/走勢縮圖"
```

---

## Task 3: 籌碼分與價量結構分（純函式）

**Files:**
- Modify: `scripts/lib/potential.py`（新增函式、`DEFAULTS` 加常數）
- Test: `scripts/tests/test_potential.py`

**Interfaces:**
- Produces:
  - `chip_score(cand, window) -> float`（0~1）。`cand` 含 `inst_net_yi`、`buy_days`。
  - `structure_score(metrics) -> float`（0~1）。`metrics` 含 `price_pos`、`vol_ratio`、`above_ma60`。
- `DEFAULTS` 新增：`chip_sat: 5.0`（億，淨買超飽和點）、`vol_hi: 1.8`（量增給滿倍數）、`pos_ref: 0.5`（位置分基準）。

- [ ] **Step 1: 寫失敗測試**

```python
def test_chip_score_rewards_amount_and_persistence():
    strong = potential.chip_score({"inst_net_yi": 5.0, "buy_days": 5}, window=5)
    weak = potential.chip_score({"inst_net_yi": 0.3, "buy_days": 1}, window=5)
    assert strong > weak
    assert 0.0 <= weak <= strong <= 1.0

def test_structure_score_pushes_down_falling_stock():
    # 蓄勢：低位置、量增、站季線
    ready = potential.structure_score({"price_pos": 0.15, "vol_ratio": 1.8, "above_ma60": True})
    # 落難：低位置但無量、破季線
    laggard = potential.structure_score({"price_pos": 0.15, "vol_ratio": 0.8, "above_ma60": False})
    assert ready > laggard
    assert 0.0 <= laggard <= ready <= 1.0
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python3 -m pytest scripts/tests/test_potential.py -k "chip_score or structure_score" -q`
Expected: FAIL（`AttributeError: ... has no attribute 'chip_score'`）

- [ ] **Step 3: 最小實作**

`DEFAULTS` 補常數，並在 `low_base_metrics` 後新增：

```python
DEFAULTS = {
    "window": 10,        # 籌碼累積天數（由 5 拉長，看得出趨勢）
    "inst_min_yi": 0.5,
    "pct_max": 3.0,
    "cand_max": 80,
    "pos_max": 0.40,     # 低基期 gate：股價位置上限
    "chip_sat": 5.0,     # 淨買超飽和點（億）
    "vol_hi": 1.8,       # 量增給滿倍數
    "pos_ref": 0.5,      # 位置分基準
    "score_min": 40,     # 進榜分數下限
    "w_chip": 0.35, "w_struct": 0.40, "w_theme": 0.25,  # Phase A 權重（可調）
}


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def chip_score(cand: dict, window: int, chip_sat: float = 5.0) -> float:
    """籌碼分：淨買超金額（飽和）0.6 + 買超天數佔比 0.4。"""
    amount = _clamp01((cand.get("inst_net_yi") or 0) / chip_sat)
    persistence = _clamp01((cand.get("buy_days") or 0) / max(1, window))
    return round(0.6 * amount + 0.4 * persistence, 3)


def structure_score(metrics: dict, vol_hi: float = 1.8, pos_ref: float = 0.5) -> float:
    """價量結構分：位置低 0.4 + 量增 0.4 + 站季線 0.2。落難股（無量、破季線）分低。"""
    pos_comp = _clamp01(1 - (metrics.get("price_pos") or 1) / pos_ref)
    vol_comp = _clamp01(((metrics.get("vol_ratio") or 1) - 0.8) / (vol_hi - 0.8))
    ma_comp = 1.0 if metrics.get("above_ma60") else 0.0
    return round(0.4 * pos_comp + 0.4 * vol_comp + 0.2 * ma_comp, 3)
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python3 -m pytest scripts/tests/test_potential.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/potential.py scripts/tests/test_potential.py
git commit -m "feat(potential): 籌碼分/價量結構分純函式"
```

---

## Task 4: 題材分、合成分數、finalize_scores

**Files:**
- Modify: `scripts/lib/potential.py`
- Test: `scripts/tests/test_potential.py`

**Interfaces:**
- Consumes: `chip_score`、`structure_score`（Task 3）。stock dict 內的 `chip_s/struct_s`（由 build_potential 掛，Task 5）、`catalyst/theme/sector`（由 annotate 掛）。
- Produces:
  - `theme_score(stock) -> float`（有 catalyst=1.0 / 有題材且≠產業別=0.5 / 否則 0）。
  - `combine_score(chip_s, struct_s, theme_s, cfg) -> int`（0~100）。
  - `finalize_scores(stocks, cfg) -> list`：對每檔算 theme_s＋`score`＋`score_parts`，依 `score` 由高到低排序後回傳同一 list。

- [ ] **Step 1: 寫失敗測試**

```python
def test_theme_score_levels():
    assert potential.theme_score({"catalyst": "國防採購千艘無人艇", "theme": "無人船", "sector": "航運"}) == 1.0
    assert potential.theme_score({"catalyst": "", "theme": "矽光子", "sector": "電子零組件"}) == 0.5
    assert potential.theme_score({"catalyst": "", "theme": "航運", "sector": "航運"}) == 0.0

def test_finalize_scores_sorts_and_scores():
    cfg = dict(potential.DEFAULTS)
    stocks = [
        {"code": "A", "chip_s": 0.9, "struct_s": 0.9, "catalyst": "轉單題材", "theme": "AI", "sector": "電子"},
        {"code": "B", "chip_s": 0.2, "struct_s": 0.2, "catalyst": "", "theme": "食品", "sector": "食品"},
    ]
    out = potential.finalize_scores(stocks, cfg)
    assert [s["code"] for s in out] == ["A", "B"]
    assert out[0]["score"] > out[1]["score"]
    assert 0 <= out[1]["score"] <= 100
    assert set(out[0]["score_parts"]) == {"chip", "struct", "theme"}
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python3 -m pytest scripts/tests/test_potential.py -k "theme_score or finalize" -q`
Expected: FAIL

- [ ] **Step 3: 最小實作**

```python
def theme_score(stock: dict) -> float:
    if (stock.get("catalyst") or "").strip():
        return 1.0
    theme = (stock.get("theme") or "").strip()
    if theme and theme != (stock.get("sector") or "").strip():
        return 0.5
    return 0.0


def combine_score(chip_s: float, struct_s: float, theme_s: float, cfg: dict) -> int:
    raw = cfg["w_chip"] * chip_s + cfg["w_struct"] * struct_s + cfg["w_theme"] * theme_s
    return int(round(100 * raw))


def finalize_scores(stocks: list[dict], cfg: dict) -> list[dict]:
    """在 annotate（題材/發酵點）之後呼叫：算題材分＋合成分數＋分項，依分數排序。"""
    for s in stocks:
        t = theme_score(s)
        s["score"] = combine_score(s.get("chip_s", 0.0), s.get("struct_s", 0.0), t, cfg)
        s["score_parts"] = {
            "chip": int(round(100 * s.get("chip_s", 0.0))),
            "struct": int(round(100 * s.get("struct_s", 0.0))),
            "theme": int(round(100 * t)),
        }
    stocks.sort(key=lambda s: s["score"], reverse=True)
    return stocks
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python3 -m pytest scripts/tests/test_potential.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/potential.py scripts/tests/test_potential.py
git commit -m "feat(potential): 題材分/合成分數/finalize_scores 排序"
```

---

## Task 5: build_potential 掛子分＋保留低基期 gate；_attach_potential 串接順序

**Files:**
- Modify: `scripts/lib/potential.py`（`filter_low_base`、`build_potential`）
- Modify: `scripts/auto_daily.py`（`_attach_potential`）
- Test: `scripts/tests/test_potential.py`

**Interfaces:**
- Consumes: `aggregate_chips`(含 buy_days)、`pick_accumulators`、`low_base_metrics`(含 vol/ma/spark)、`chip_score`、`structure_score`。
- Produces: `build_potential(days, start_date, cfg, fetch, sleep_s)` 回 `{"window_days", "stocks":[...]}`；每檔含 `code/name/pct/value_yi/sector/inst_net_yi/buy_days/price_pos/chg_6m/vol_ratio/above_ma60/spark/chip_s/struct_s`（**尚無 score**，等 finalize）。低基期 gate 仍為 `price_pos <= pos_max`（去掉 chg_6m 硬篩，改由結構分吸收）。

- [ ] **Step 1: 寫失敗測試（用假 fetch，不打網路）**

```python
def test_build_potential_attaches_subscores_no_score_yet():
    days = [potential.__dict__  # 佔位，真正資料如下
            ]
    days = [_radar([{"code": "2603", "name": "長榮", "pct": 0.0, "inst_net_yi": 1.0,
                     "value_yi": 5.0, "sector": "航運"}])]

    def fake_fetch(code, start):
        rows = []
        for i in range(120):
            rows.append({"date": f"2025-{(i//28)+1:02d}-{(i%28)+1:02d}",
                         "close": 50 - i * 0.05, "max": 51 - i * 0.05,
                         "min": 49 - i * 0.05, "Trading_Volume": 1000 + (400 if i >= 115 else 0)})
        return rows

    out = potential.build_potential(days, "2025-01-01",
                                    cfg={"window": 5}, fetch=fake_fetch, sleep_s=0)
    s = out["stocks"][0]
    assert "chip_s" in s and "struct_s" in s and "spark" in s
    assert "score" not in s  # 分數在 finalize 才算
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python3 -m pytest scripts/tests/test_potential.py::test_build_potential_attaches_subscores_no_score_yet -q`
Expected: FAIL（`KeyError: 'chip_s'`）

- [ ] **Step 3: 最小實作**

`filter_low_base` 改為只用 `pos_max` 當 gate、掛結構分與 metrics；`build_potential` 掛籌碼分：

```python
def filter_low_base(cands: list[dict], start_date: str, cfg: dict,
                    fetch=finmind_history, sleep_s: float = 0.3) -> list[dict]:
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
        if m["price_pos"] > cfg["pos_max"]:   # 低基期 gate（唯一硬門檻）
            continue
        struct_s = structure_score(m, cfg["vol_hi"], cfg["pos_ref"])
        out.append({**c, **m, "struct_s": struct_s, "history": "ok"})
    return out


def build_potential(days: list[dict], start_date: str, cfg: dict | None = None,
                    fetch=finmind_history, sleep_s: float = 0.3) -> dict:
    cfg = {**DEFAULTS, **(cfg or {})}
    agg = aggregate_chips(days, cfg["window"])
    cands = pick_accumulators(agg, cfg["inst_min_yi"], cfg["pct_max"], cfg["cand_max"])
    stocks = filter_low_base(cands, start_date, cfg, fetch=fetch, sleep_s=sleep_s)
    for s in stocks:
        s["chip_s"] = chip_score(s, cfg["window"], cfg["chip_sat"])
    return {"window_days": cfg["window"], "stocks": stocks}
```

（注意：`filter_low_base` 簽章由舊的 `pos_max, chg6m_max` 改成吃整個 `cfg`；本 repo 內僅 `build_potential` 呼叫它，無其他呼叫端。）

- [ ] **Step 4: 跑測試確認通過**

Run: `python3 -m pytest scripts/tests/test_potential.py -q`
Expected: PASS（若既有測試呼叫舊 `filter_low_base(..., pos_max=, chg6m_max=)`，一併更新為傳 cfg）

- [ ] **Step 5: 串接 _attach_potential 順序**

`scripts/auto_daily.py` 的 `_attach_potential`，把 annotate 後補 finalize：

```python
        pot = build_potential(history, start)
        annotate_potential(pot["stocks"])
        from scripts.lib.potential import finalize_scores, DEFAULTS as POT_DEFAULTS
        finalize_scores(pot["stocks"], dict(POT_DEFAULTS))
        # 進榜分數下限：低於 score_min 的沉底股不顯示
        pot["stocks"] = [s for s in pot["stocks"] if s.get("score", 0) >= POT_DEFAULTS["score_min"]]
        day["potential"] = pot
```

- [ ] **Step 6: 本機 dry-run 驗證（不發推播）**

Run: `OPENAI_API_KEY=dummy python3 -m scripts.auto_daily --dry-run 2>&1 | grep -i 潛力`
Expected: 印出「低基期潛力：候選 N 檔」；打開最新 `public/data/<date>.json` 確認 `potential.stocks[0]` 有 `score`、`score_parts`、`spark` 且依 score 由高到低。（無網路/額度時候選可能為 0，屬正常，不報錯即可）

- [ ] **Step 7: Commit**

```bash
git add scripts/lib/potential.py scripts/auto_daily.py scripts/tests/test_potential.py
git commit -m "feat(potential): build_potential 掛子分、gate 保留低基期、串 finalize 排序"
```

---

## Task 6: 前端 PotentialRadar 分數 badge、排序、sparkline

**Files:**
- Modify: `src/lib/potential.js`
- Modify: `src/components/PotentialRadar.jsx`
- Modify: `src/styles.css`
- Test: `src/lib/tests/potential.test.js`

**Interfaces:**
- Produces（`src/lib/potential.js`）：
  - `scoreTier(score) -> 'hot'|'warm'|'cool'`（≥70 hot、≥50 warm、else cool）。
  - `sparkPath(points, w, h) -> string`（把數列映射成 SVG polyline 的 `points` 字串；points 長度 <2 回空字串）。

- [ ] **Step 1: 寫失敗測試**

```js
import { describe, it, expect } from 'vitest'
import { scoreTier, sparkPath } from '../potential.js'

describe('scoreTier', () => {
  it('分級', () => {
    expect(scoreTier(80)).toBe('hot')
    expect(scoreTier(55)).toBe('warm')
    expect(scoreTier(30)).toBe('cool')
  })
})

describe('sparkPath', () => {
  it('產生 polyline points，端點對齊', () => {
    const s = sparkPath([1, 2, 3], 100, 20)
    const pts = s.split(' ')
    expect(pts.length).toBe(3)
    expect(pts[0].startsWith('0,')).toBe(true)      // 第一點 x=0
    expect(pts[2].startsWith('100,')).toBe(true)    // 最後一點 x=w
  })
  it('點數不足回空字串', () => {
    expect(sparkPath([5], 100, 20)).toBe('')
  })
})
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `npm test -- potential`
Expected: FAIL（`scoreTier is not a function`）

- [ ] **Step 3: 實作純函式**

`src/lib/potential.js` 追加：

```js
export function scoreTier(score) {
  const s = score ?? 0
  return s >= 70 ? 'hot' : s >= 50 ? 'warm' : 'cool'
}

// 數列 → SVG polyline points（x 均分 0..w，y 依 min..max 映射到 h..0）
export function sparkPath(points, w, h) {
  if (!points || points.length < 2) return ''
  const min = Math.min(...points)
  const max = Math.max(...points)
  const span = max - min || 1
  return points
    .map((v, i) => {
      const x = (i / (points.length - 1)) * w
      const y = h - ((v - min) / span) * h
      return `${+x.toFixed(1)},${+y.toFixed(1)}`
    })
    .join(' ')
}
```

- [ ] **Step 4: 跑測試確認通過**

Run: `npm test -- potential`
Expected: PASS

- [ ] **Step 5: PotentialRadar 卡片加分數 badge、依 score 排序、sparkline**

`src/components/PotentialRadar.jsx` 改（import 補 `scoreTier, sparkPath`；stocks 依 score 排序；卡片加 badge 與 sparkline）：

```jsx
import { isGolden, fmtPct, scoreTier, sparkPath } from '../lib/potential.js'

export default function PotentialRadar({ potential, onOpen }) {
  const stocks = [...(potential?.stocks || [])].sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
  if (!stocks.length) {
    return (
      <div className="pot-empty">
        今日無低基期吸籌標的。<br />
        <span className="pot-note">（跡象非保證，研究起點）</span>
      </div>
    )
  }
  return (
    <div className="pot-wrap">
      <div className="pot-list">
        {stocks.map((s) => (
          <div key={s.code} className={'pot-card tier-' + scoreTier(s.score)}>
            <div className="pot-head">
              <button className="pot-name" onClick={() => onOpen && onOpen(s.code)}>
                {s.name} <span className="pot-code">{s.code}</span>
              </button>
              <span className={'pot-score tier-' + scoreTier(s.score)}>{s.score ?? '—'} 分</span>
            </div>
            {s.spark && s.spark.length > 1 && (
              <svg className="pot-spark" viewBox="0 0 100 22" preserveAspectRatio="none" aria-label="近一年走勢">
                <polyline points={sparkPath(s.spark, 100, 22)} />
              </svg>
            )}
            <div className="pot-metrics">
              {s.theme && <span className="pot-tag">🏷️ {s.theme}</span>}
              <span>位置 {Math.round((s.price_pos ?? 0) * 100)}%</span>
              <span>近半年 {fmtPct(s.chg_6m)}</span>
              <span>法人 {(s.inst_net_yi ?? 0).toFixed(1)} 億</span>
            </div>
            {s.catalyst && <div className="pot-cat">🌱 {s.catalyst}</div>}
          </div>
        ))}
      </div>
      <div className="pot-note">分數＝籌碼＋價量結構＋題材綜合；跡象非保證，研究起點</div>
    </div>
  )
}
```

（移除舊的散佈圖 SVG 與 `isGolden` 用法：清單改分數排序後，散佈圖資訊已由分數 badge 取代；`isGolden` 保留於 potential.js 不動，避免影響其他 import。）

- [ ] **Step 6: 加樣式（白瓷粉 tokens）**

`src/styles.css` 潛力區塊段追加：

```css
.pot-score{ font: 600 12px/1 var(--font-mono, monospace); padding:2px 8px; border-radius:999px; white-space:nowrap; }
.pot-score.tier-hot{ background:rgba(204,82,131,.14); color:var(--gold,#CC5283); }
.pot-score.tier-warm{ background:rgba(204,82,131,.08); color:var(--gold,#CC5283); }
.pot-score.tier-cool{ background:rgba(0,0,0,.05); color:var(--muted,#8a7480); }
.pot-card.tier-hot{ border-color:rgba(204,82,131,.35); }
.pot-spark{ width:100%; height:22px; margin:6px 0; display:block; }
.pot-spark polyline{ fill:none; stroke:var(--gold,#CC5283); stroke-width:1.2; vector-effect:non-scaling-stroke; }
```

- [ ] **Step 7: 跑測試＋build**

Run: `npm test -- potential && npm run build`
Expected: 測試 PASS、build 成功

- [ ] **Step 8: Commit**

```bash
git add src/lib/potential.js src/components/PotentialRadar.jsx src/styles.css src/lib/tests/potential.test.js
git commit -m "feat(ui): 低基期卡片分數 badge、依分數排序、一年走勢縮圖"
```

---

## Task 7: Radar.jsx 頂部總結列 + 進階控制項摺疊

**Files:**
- Modify: `src/lib/radar.js`
- Modify: `src/components/Radar.jsx`
- Modify: `src/styles.css`
- Test: `src/lib/tests/radar.test.js`

**Interfaces:**
- Produces（`src/lib/radar.js`）：`radarSummary(radar, potential) -> string`。用象限計數與潛力股數組一句話，例：「法人今日逆勢吸籌 8 檔 · 撤離 3 個類股 · 🌱潛力股 5 檔」。無資料回空字串。
- Consumes: `radar.stocks`（象限判定沿用 `quadKey` 概念，但 radar.js 需自帶簡化計數，避免循環相依）。

- [ ] **Step 1: 寫失敗測試**

```js
import { radarSummary } from '../radar.js'

describe('radarSummary', () => {
  it('組出總結句', () => {
    const radar = { stocks: [
      { pct: -1, inst_net_yi: 2 }, { pct: -1, inst_net_yi: 3 },   // 逆勢吸籌 x2
      { pct: 1, inst_net_yi: -2 },                                 // 漲高出貨 x1
    ] }
    const potential = { stocks: [{}, {}] }
    const s = radarSummary(radar, potential)
    expect(s).toContain('吸籌 2')
    expect(s).toContain('潛力股 2')
  })
  it('無資料回空字串', () => {
    expect(radarSummary(null, null)).toBe('')
  })
})
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `npm test -- radar`
Expected: FAIL（`radarSummary is not a function`）

- [ ] **Step 3: 實作 radarSummary**

`src/lib/radar.js` 追加（自帶輕量象限判定，門檻用 1 億中性帶近似單日）：

```js
export function radarSummary(radar, potential) {
  const stocks = radar?.stocks || []
  if (!stocks.length && !(potential?.stocks || []).length) return ''
  let acc = 0, dist = 0
  for (const d of stocks) {
    if (Math.abs(d.inst_net_yi ?? 0) < 1) continue
    if (d.inst_net_yi > 0 && d.pct < 0) acc++
    else if (d.inst_net_yi < 0 && d.pct > 0) dist++
  }
  const potN = (potential?.stocks || []).length
  const parts = []
  if (acc) parts.push(`法人逆勢吸籌 ${acc} 檔`)
  if (dist) parts.push(`撤離 ${dist} 檔`)
  if (potN) parts.push(`🌱潛力股 ${potN} 檔`)
  return parts.join(' · ')
}
```

- [ ] **Step 4: 跑測試確認通過**

Run: `npm test -- radar`
Expected: PASS

- [ ] **Step 5: Radar.jsx 加總結列 + 進階摺疊**

在 `src/components/Radar.jsx`：import `radarSummary`；在標題列下方、`pmode` 上方插入總結列；把「觀察區間」`radar-win` 區塊包進 `<details className="radar-adv">`。

```jsx
import { aggregateRadar, radarSummary } from '../lib/radar.js'
// ...標題 card-h 之後、pmode 之前：
{radarSummary(radar, potential) && (
  <div className="radar-summary">📌 {radarSummary(radar, potential)}</div>
)}
// ...把觀察區間 radar-win 包起來：
<details className="radar-adv">
  <summary>進階：觀察區間・類股/個股</summary>
  <div className="radar-win"> ...原內容... </div>
</details>
```

（`類股/個股` 的 `seg` 目前在 `card-h` 內；一併移入 `<details>` 的 summary 下方，`card-h` 只留標題。若移動成本高，Phase A 先只收「觀察區間」，類股/個股保留於標題列——以實際排版乾淨為準。）

- [ ] **Step 6: 樣式**

`src/styles.css`：

```css
.radar-summary{ font:600 13px/1.5 var(--font, inherit); color:var(--gold,#CC5283); margin:2px 0 10px; }
.radar-adv{ margin:6px 0 10px; }
.radar-adv > summary{ cursor:pointer; font-size:13px; color:var(--muted,#8a7480); padding:6px 0; list-style:revert; }
```

- [ ] **Step 7: build + headless 截圖驗證手機版**

Run: `npm run build && npm run preview &`（另開）
用 chrome headless 或 Playwright 開 `http://localhost:4173/daily-market-dashboard/?win=1` 手機寬度（≥500）截圖，確認：總結列出現、進階區預設收合、雷達不再一次攤四層。截圖發 Andy。

- [ ] **Step 8: Commit**

```bash
git add src/lib/radar.js src/components/Radar.jsx src/styles.css src/lib/tests/radar.test.js
git commit -m "feat(ui): 資金雷達頂部總結列＋進階控制項收摺"
```

---

## Task 8: 推播加「🌱今日新進潛力股 Top3」

**Files:**
- Modify: `scripts/notify.py`
- Test: `scripts/tests/test_notify.py`（無則新建）

**Interfaces:**
- Produces: `_potential_lines(day) -> list[str]`（依 score 取 Top3，每檔一行「• 名稱 分數分｜題材」，有 catalyst 附一句；無 potential 回 `[]`）。插進 `build_summary_text`（放機會股之後、法說會之前）。

- [ ] **Step 1: 寫失敗測試**

```python
from scripts import notify

def test_potential_lines_top3():
    day = {"potential": {"stocks": [
        {"name": "龍德造船", "code": "6753", "score": 82, "theme": "無人船", "catalyst": "國防採購千艘無人艇"},
        {"name": "長榮", "code": "2603", "score": 61, "theme": "航運", "catalyst": ""},
        {"name": "統一", "code": "1216", "score": 55, "theme": "食品", "catalyst": ""},
        {"name": "台中銀", "code": "2812", "score": 40, "theme": "金融", "catalyst": ""},
    ]}}
    lines = notify._potential_lines(day)
    assert lines[0] == "🌱 今日潛力股 Top3"
    assert "龍德造船" in lines[1] and "82" in lines[1]
    assert sum(1 for l in lines if l.startswith("•")) == 3  # 只取 3 檔

def test_potential_lines_empty():
    assert notify._potential_lines({}) == []
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python3 -m pytest scripts/tests/test_notify.py -k potential -q`
Expected: FAIL

- [ ] **Step 3: 實作 _potential_lines 並插入 build_summary_text**

```python
def _potential_lines(day: dict):
    """低基期潛力股 Top3（依分數）；無資料回空清單、靜默省略。"""
    picks = ((day.get("potential") or {}).get("stocks")) or []
    if not picks:
        return []
    top = sorted(picks, key=lambda s: s.get("score", 0), reverse=True)[:3]
    lines = ["🌱 今日潛力股 Top3"]
    for s in top:
        row = f"• {s.get('name', '')} {s.get('score', '')} 分"
        theme = (s.get("theme") or "").strip()
        if theme:
            row += f"｜{theme}"
        lines.append(row)
        cat = (s.get("catalyst") or "").strip()
        if cat:
            lines.append(f"　🌱 {cat}")
    lines.append("")
    return lines
```

在 `build_summary_text` 內、`lines += _opportunities_lines(day)` 之後插入：

```python
    # 🌱 低基期潛力股 Top3（無資料靜默省略）
    lines += _potential_lines(day)
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python3 -m pytest scripts/tests/test_notify.py -q`
Expected: PASS

- [ ] **Step 5: 本機預覽推播文字**

Run: `python3 -c "from scripts import notify, json; d=json.load(open('public/data/2026-07-02.json')); print(notify.build_summary_text(d))"`
Expected: 若該日有 potential 分數，摘要中出現「🌱 今日潛力股 Top3」段（07-02 舊資料無 score 時該段自動省略，屬正常）。

- [ ] **Step 6: Commit**

```bash
git add scripts/notify.py scripts/tests/test_notify.py
git commit -m "feat(notify): 每日推播加低基期潛力股 Top3"
```

---

## 完工驗收（Phase A）

- [ ] 全測試綠：`python3 -m pytest scripts/tests/ -q` 且 `npm test`
- [ ] `npm run build` 成功
- [ ] 本機 `--dry-run` 產出的 `<date>.json` 內 `potential.stocks` 有 `score/score_parts/spark`、依分數排序
- [ ] 手機寬度截圖：雷達有總結列、進階收摺、潛力卡片有分數 badge 與走勢縮圖 → 發 Andy 確認
- [ ] 部署：`git push` main → `gh workflow run daily.yml` → `gh run view <id> --log` 綠燈（此站為 Actions Pages artifact 部署，非 gh-pages 分支）
- [ ] 線上驗證（`?cb=隨機` 繞快取）→ 發 Andy

## Self-Review 對照 spec

- 支柱一（發動信心分數）：Task 1–5 ✔（籌碼/價量結構/題材三子分、落難股由結構分壓低、分數排序、門檻改分數制）。基本面分屬 Phase B，本計劃不含 ✔（spec 已分期）。
- 支柱二（呈現）：Task 6（分數 badge、走勢縮圖、排序）+ Task 7（總結列、進階收摺、白瓷粉保留）✔。
- 支柱三（使用）：Task 8（推播 Top3）✔；追蹤/發動提醒/作戰室屬 Phase B ✔。
- 型別一致：`build_potential` 產 `chip_s/struct_s` → `finalize_scores` 讀同名並產 `score/score_parts`；前端讀 `score/spark/theme/catalyst` 一致 ✔。
- 無 placeholder：各步驟含實碼與指令 ✔。
