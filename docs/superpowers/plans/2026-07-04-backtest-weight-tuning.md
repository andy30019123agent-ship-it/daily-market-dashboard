# 回測調整權重 實作計劃（spike）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement task-by-task. Steps use checkbox (`- [ ]`).

**Goal:** 離線回測工具：用 TWSE T86（法人）＋FinMind（價量/營收）重建過去 N 個月的低基期候選＋三子分，量測未來 20 日報酬，網格搜尋「籌碼/價量結構/基本面」最佳權重，出建議報告（人工確認才套用）。

**Architecture:** 純數學函式（報酬、排序 IC、五分位差、網格搜尋）以 TDD 打底、不碰網路；資料層（T86 逐日抓取＋FinMind 價量/營收）帶磁碟快取、可注入假 fetch 測試；CLI 組裝重建候選→計分→回測→出報告。複用線上 `potential.py` 的 `chip_score/structure_score/fundamental_score` 確保與線上一致。

**Tech Stack:** Python 3（urllib/subprocess curl、pytest）。無新依賴。

## Global Constraints

- 台北時間；日期 ISO。
- **離線工具**：不進 CI、不改線上評分模型（`potential.py` 只被 import 複用，不修改權重）。
- 全免費資料源；**所有抓取都快取到 `backtest/cache/`（gitignore）**，抓過不重抓。
- **禁止前視偏誤**：計分只能用 as-of 日 D（含）以前的資料；未來報酬只用 D 之後。
- 抓取失敗/限流/空值→重試或跳過並計數，不得中斷整個回測。
- 報告必標樣本數與「僅研究參考、非未來保證」。
- 測試不打網路（注入假 fetch）。
- 繁中註解，風格一致。測試：`python3 -m pytest scripts/tests/test_backtest.py -q`。

## 已驗證（2026-07-04 spike 前置）

- TWSE T86 逐日歷史可抓：`www.twse.com.tw/rwd/zh/fund/T86?date=YYYYMMDD&selectType=ALLBUT0999&response=json`，交易日回 `stat:OK`＋~1300 列＋19 欄（含三大法人淨額股數，最後一欄），非交易日回「沒有符合條件的資料」。
- FinMind `TaiwanStockPrice` 可抓（msg success）。

## 檔案結構

- `scripts/lib/backtest.py`（新）：純函式 `forward_return / rank_ic / quintile_spread / weighted_score / grid_search_weights`。
- `scripts/lib/twse_hist.py`（新）：`parse_t86`（JSON→{code: 淨額股數}）、`fetch_t86_cached`（抓＋快取）。
- `scripts/backtest_weights.py`（新）：CLI；重建候選、計分、回測、出 md+json 報告。
- 測試：`scripts/tests/test_backtest.py`、`scripts/tests/test_twse_hist.py`。
- `.gitignore`：加 `backtest/cache/` 與 `backtest/report-*`。

## 計分與呼叫量控制（spike 範圍）

- 基準日：視窗內**每週一次**（省呼叫）；期間先 **2～3 個月**；**僅上市**（上櫃列延伸）。
- 每個基準日 D：抓 D 前 `window=10` 交易日的 T86（快取，唯一日期約 40～65 個、各 1 次）。以「window 內法人淨額股數加總」取 **top K=60** 為初選吸籌候選（避免對全市場 1300 檔查價）。
- 對候選（去重後約 100～250 檔）查 FinMind 一年日 K（截止 D）＋月營收（截止 D），各 1 次、快取。
- 三子分：`chip_s`＝window 內每日「淨額股數×當日收盤/1e8（億）」加總 + 買超天數，餵 `potential.chip_score`；`struct_s`＝`potential.low_base_metrics`(截止 D 的 K)→`structure_score`；`fund_s`＝`potential.revenue_yoy`→`fundamental_score`。低基期 gate（price_pos≤0.4）沿用。
- 未來報酬：`forward_return(K, D, 20)`。

---

## Task 1: 純數學核心（報酬、IC、五分位差、加權分、網格搜尋）

**Files:** Create `scripts/lib/backtest.py`；Test `scripts/tests/test_backtest.py`

**Interfaces (Produces):**
- `forward_return(rows, as_of, horizon) -> float|None`：rows=日K（由舊到新，含 date/close），as_of 之後第 horizon 根的 close / as_of 當根 close − 1；不足回 None。
- `weighted_score(sub, w) -> float`：sub={chip,struct,fund}，w 同 key，回加權和。
- `rank_ic(pairs) -> float|None`：pairs=[(score,ret)]，回 Spearman 排序相關；<3 筆回 None。
- `quintile_spread(pairs) -> float|None`：高分五分之一平均報酬 − 低分五分之一平均報酬。
- `grid_search_weights(samples, step=0.1) -> dict`：samples=[{chip,struct,fund,ret}]，列舉 chip+struct+fund=1 的網格，回 `{"best": {w,ic,spread}, "top": [...]}`（依 ic 排序）。

- [ ] **Step 1: 失敗測試**

```python
from scripts.lib import backtest as bt

def _k(closes, start="2026-01-01"):
    import datetime
    d0 = datetime.date.fromisoformat(start)
    return [{"date": (d0 + datetime.timedelta(days=i)).isoformat(), "close": c}
            for i, c in enumerate(closes)]

def test_forward_return():
    rows = _k([100, 101, 102, 110])  # index0=as_of, horizon3 → 110/100-1
    assert round(bt.forward_return(rows, "2026-01-01", 3), 3) == 0.10
    assert bt.forward_return(rows, "2026-01-01", 99) is None  # 不足

def test_weighted_score():
    s = bt.weighted_score({"chip": 1.0, "struct": 0.0, "fund": 0.0},
                          {"chip": 0.5, "struct": 0.3, "fund": 0.2})
    assert s == 0.5

def test_rank_ic_monotonic():
    pairs = [(1, 0.1), (2, 0.2), (3, 0.3), (4, 0.4)]
    assert round(bt.rank_ic(pairs), 3) == 1.0

def test_quintile_spread_positive_when_score_predicts():
    pairs = [(i, i / 10) for i in range(10)]  # 分數高→報酬高
    assert bt.quintile_spread(pairs) > 0

def test_grid_search_recovers_chip():
    # 合成：報酬完全由 chip 決定 → 最佳權重應偏 chip
    samples = [{"chip": c, "struct": 0.5, "fund": 0.5, "ret": c}
               for c in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]]
    out = bt.grid_search_weights(samples, step=0.5)
    assert out["best"]["w"]["chip"] >= out["best"]["w"]["struct"]
```

- [ ] **Step 2: 跑測試確認失敗** — `python3 -m pytest scripts/tests/test_backtest.py -q`（module 不存在）
- [ ] **Step 3: 實作 `scripts/lib/backtest.py`**

```python
"""回測純函式：報酬、排序 IC、五分位差、加權分、權重網格搜尋。不碰網路。"""
from __future__ import annotations


def forward_return(rows, as_of, horizon):
    rows = [r for r in rows if r.get("close") is not None]
    idx = next((i for i, r in enumerate(rows) if r["date"] >= as_of), None)
    if idx is None or idx + horizon >= len(rows):
        return None
    base = rows[idx]["close"]
    fut = rows[idx + horizon]["close"]
    return (fut / base - 1) if base else None


def weighted_score(sub, w):
    return sum((sub.get(k) or 0) * w.get(k, 0) for k in ("chip", "struct", "fund"))


def _rank(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def rank_ic(pairs):
    pairs = [(s, r) for s, r in pairs if s is not None and r is not None]
    n = len(pairs)
    if n < 3:
        return None
    rs = _rank([p[0] for p in pairs])
    rr = _rank([p[1] for p in pairs])
    ms, mr = sum(rs) / n, sum(rr) / n
    num = sum((rs[i] - ms) * (rr[i] - mr) for i in range(n))
    den = (sum((x - ms) ** 2 for x in rs) * sum((x - mr) ** 2 for x in rr)) ** 0.5
    return round(num / den, 4) if den else None


def quintile_spread(pairs):
    pairs = sorted([(s, r) for s, r in pairs if s is not None and r is not None])
    n = len(pairs)
    if n < 5:
        return None
    q = max(1, n // 5)
    low = sum(r for _, r in pairs[:q]) / q
    high = sum(r for _, r in pairs[-q:]) / q
    return round(high - low, 4)


def _weight_grid(step):
    out = []
    n = round(1 / step)
    for a in range(n + 1):
        for b in range(n - a + 1):
            c = n - a - b
            out.append({"chip": round(a * step, 4), "struct": round(b * step, 4),
                        "fund": round(c * step, 4)})
    return out


def grid_search_weights(samples, step=0.1):
    results = []
    for w in _weight_grid(step):
        pairs = [(weighted_score(s, w), s["ret"]) for s in samples if s.get("ret") is not None]
        ic = rank_ic(pairs)
        if ic is None:
            continue
        results.append({"w": w, "ic": ic, "spread": quintile_spread(pairs)})
    results.sort(key=lambda x: x["ic"], reverse=True)
    return {"best": results[0] if results else None, "top": results[:10],
            "n_samples": len(samples)}
```

- [ ] **Step 4: 跑測試確認通過** — `python3 -m pytest scripts/tests/test_backtest.py -q`
- [ ] **Step 5: Commit** — `git commit -m "feat(backtest): 純數學核心（報酬/IC/五分位/網格搜尋）"`

---

## Task 2: T86 逐日抓取＋解析＋快取

**Files:** Create `scripts/lib/twse_hist.py`；Test `scripts/tests/test_twse_hist.py`

**Interfaces (Produces):**
- `parse_t86(payload) -> dict[str,int]`：TWSE T86 JSON → `{4碼證券代號: 三大法人買賣超淨額股數}`。只收 4 碼代號（濾 ETF/權證），淨額欄＝最後一欄、去逗號轉 int。
- `fetch_t86_cached(date, cache_dir, get=<curl>) -> dict[str,int]`：先讀 `cache_dir/t86-<date>.json`，無則抓 TWSE、存快取再回。非交易日/空回 {}。

- [ ] **Step 1: 失敗測試（注入假 payload，不打網路）**

```python
from scripts.lib import twse_hist as th

def test_parse_t86_filters_and_parses():
    payload = {"stat": "OK",
               "fields": ["代號", "名稱"] + ["x"] * 16 + ["淨額"],
               "data": [
                   ["2330", "台積電"] + ["0"] * 16 + ["1,234,000"],
                   ["00403A", "某ETF"] + ["0"] * 16 + ["999"],  # 非4碼→濾掉
               ]}
    out = th.parse_t86(payload)
    assert out == {"2330": 1234000}

def test_fetch_t86_cached_hit(tmp_path):
    import json
    (tmp_path / "t86-20260703.json").write_text(json.dumps({"2330": 500}), encoding="utf-8")
    got = th.fetch_t86_cached("20260703", tmp_path, get=lambda url: (_ for _ in ()).throw(AssertionError("不該連網")))
    assert got == {"2330": 500}
```

- [ ] **Step 2: 確認失敗** — `python3 -m pytest scripts/tests/test_twse_hist.py -q`
- [ ] **Step 3: 實作**

```python
"""TWSE T86（三大法人買賣超）逐日抓取＋解析＋磁碟快取。"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess

T86_URL = ("https://www.twse.com.tw/rwd/zh/fund/T86"
           "?date={date}&selectType=ALLBUT0999&response=json")


def parse_t86(payload: dict) -> dict:
    if not payload or payload.get("stat") != "OK":
        return {}
    out = {}
    for row in payload.get("data") or []:
        code = (row[0] or "").strip()
        if not re.fullmatch(r"\d{4}", code):
            continue
        try:
            out[code] = int(str(row[-1]).replace(",", ""))
        except (ValueError, IndexError):
            continue
    return out


def _curl(url: str) -> str:
    return subprocess.run(["curl", "-s", "--http1.1", "-4", "--max-time", "25", url],
                          capture_output=True, text=True, timeout=40).stdout


def fetch_t86_cached(date: str, cache_dir, get=_curl) -> dict:
    cache_dir = pathlib.Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    fp = cache_dir / f"t86-{date}.json"
    if fp.exists():
        return json.loads(fp.read_text(encoding="utf-8"))
    try:
        payload = json.loads(get(T86_URL.format(date=date)) or "{}")
    except Exception:
        payload = {}
    parsed = parse_t86(payload)
    fp.write_text(json.dumps(parsed, ensure_ascii=False), encoding="utf-8")
    return parsed
```

- [ ] **Step 4: 確認通過** — `python3 -m pytest scripts/tests/test_twse_hist.py -q`
- [ ] **Step 5: Commit** — `git commit -m "feat(backtest): T86 逐日抓取解析＋快取"`

---

## Task 3: CLI 組裝＋重建候選＋出報告＋跑 spike

**Files:** Create `scripts/backtest_weights.py`；Modify `.gitignore`

**Interfaces (Consumes):** Task 1/2 函式；`potential.py` 的 `chip_score/low_base_metrics/structure_score/revenue_yoy/fundamental_score/finmind_history/finmind_revenue/DEFAULTS`。

- [ ] **Step 1: `.gitignore` 加 backtest 快取/報告**

```
backtest/cache/
backtest/report-*
```

- [ ] **Step 2: 實作 CLI（重建→計分→回測→報告）**

`scripts/backtest_weights.py`：
- 參數：`--start --end --horizon 20 --window 10 --topk 60 --grid-step 0.1 --sleep 0.4`。
- 產生基準日：呼叫 `fetch_t86_cached` 逐日（用日曆日試抓，回空即非交易日跳過），蒐集期間交易日清單；每週取一個為 as-of D。
- 每個 D：對 D 前 window 交易日的 T86 聚合每股淨額股數 → top K 初選；對候選查 FinMind 一年日 K（截止 D 過濾 `date<=D`）＋月營收；算三子分（chip 用「Σ 淨額股數×當日 close/1e8」＋買超天數→`chip_score`；struct 用 `low_base_metrics`→`structure_score`，過低基期 gate；fund 用 `revenue_yoy`→`fundamental_score`）；算 `forward_return(K, D, horizon)`。
- 匯集所有 (D,候選) 樣本 → `grid_search_weights`；另做前後兩半交叉。
- 出 `backtest/report-<rundate>.md`（建議權重、Top10、IC、五分位差、樣本數、前後半穩定度、警語）＋ `.json`。
- 全程 try/except 單檔失敗跳過並計數；抓取間 `sleep`。

- [ ] **Step 3: 冒煙（小範圍）**

Run: `python3 scripts/backtest_weights.py --start 2026-04-01 --end 2026-06-30 --topk 40 --grid-step 0.2`
Expected: 產出 report md，內含建議三權重與樣本數（≥數十）；無前視（截止日過濾）；FinMind/TWSE 快取檔生成於 `backtest/cache/`。若限流，降 topk/加 sleep 重跑（快取已存不重抓）。

- [ ] **Step 4: Commit（不含快取/報告，已 gitignore）** — `git commit -m "feat(backtest): CLI 重建候選＋回測＋報告"`

## 完工驗收

- [ ] `python3 -m pytest scripts/tests/test_backtest.py scripts/tests/test_twse_hist.py -q` 綠
- [ ] spike 報告產得出、樣本數合理、建議三權重（籌碼/價量結構/基本面）
- [ ] 報告含樣本數、前後半穩定度、「僅研究參考」警語
- [ ] 把報告重點（建議權重 vs 現行 0.35/0.35/0.10-題材除外）發 Andy，由他決定是否手動更新 `potential.py DEFAULTS`

## Self-Review 對照 spec

- 三項權重回測、題材不進、不加類股 ✔；離線工具不碰線上 ✔；混用資料源＋快取 ✔；禁前視（截止日過濾）✔；防過度配適（前後半交叉、標樣本數/警語）✔；先 spike（2-3月/上市/週頻/topK）✔。
- 型別一致：Task1 `grid_search_weights(samples[{chip,struct,fund,ret}])` 與 CLND 組的樣本鍵一致；chip/struct/fund 子分複用 potential.py 同名函式 ✔。
