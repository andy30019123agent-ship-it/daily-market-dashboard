# 每日資料 Schema（對齊 v2 設計）

每天一個檔案 `public/data/<YYYY-MM-DD>.json`，前端與抓取腳本共用此契約。
另有 `public/data/index.json` = `{"dates": ["2026-06-18", ...]}` 作為日期索引。

## 頂層欄位（皆必填）

| 鍵 | 型別 | 說明 |
|---|---|---|
| `date` | str | `YYYY-MM-DD` |
| `updated_at` | str | 更新時間字串，如 `2026-06-18 18:43` |
| `overview` | obj | 今日總覽，含 `tw` / `us` / `vix` |
| `sectors` | obj | 板塊資金流向，含 `tw` / `us`，各有 `in` / `out` |
| `hot_stocks` | obj | 熱門個股，含 `tw` / `us` 陣列 |
| `news` | list | 川普及影響股市消息（每條附來源）|
| `upcoming_events` | list | 本週重大日程（事前分析）|
| `past_events_review` | list | 昨日已過日程（事後回顧）|
| `verdict` | obj | 今日綜合研判 `{bullish, bearish, risks}` |
| `summary` | str | Telegram 推播用 3~5 句摘要 |

## overview

```jsonc
"overview": {
  "tw": {
    "featured": { "name": "發行量加權股價指數", "close": 22486.31,
                  "change": 182.4, "change_pct": 0.82, "note": "較昨收",
                  "spark": [22180, 22240, ...] },          // 走勢線取樣點
    "stats": [ { "name": "櫃買 OTC", "value": "238.4", "change_pct": 0.68 },
               { "name": "成交金額", "value": "4,120 億", "change_pct": -6, "note": "量縮 6%" },
               { "name": "外資買賣超", "value": "+128 億", "dir": "up", "note": "連 3 買" } ]
  },
  "us": [ { "name": "道瓊", "close": 42318, "change_pct": -0.37 }, ... ],   // 4 檔
  "vix": {
    "tw": { "value": 18.5, "change": -0.8, "state": "波動偏低",
            "note": "市場情緒平穩，無明顯避險需求", "gauge": 0.26 },        // gauge 0~1，刻度位置
    "us": { "value": 14.2, "change": -0.5, "state": "低波動",
            "note": "恐慌情緒低，多頭氣氛延續", "gauge": 0.18 }
  }
}
```

- `change_pct` 為數字（正負），前端依正負上紅下綠（台灣慣例）。
- `dir` 可選，覆寫漲跌色（如外資買賣超用金額正負）。

## sectors

```jsonc
"sectors": {
  "tw": { "in":  [ { "name": "半導體", "amount": "+124 億", "weight": 1.0 }, ... ],   // weight 0~1 條長
          "out": [ { "name": "航運",   "amount": "−58 億",  "weight": 1.0 }, ... ] },
  "us": { "in": [...], "out": [...] }
}
```

## inst_top（三大法人個股買超 Top 5，台股）

```jsonc
"inst_top": {
  "foreign": [ { "code": "2618", "name": "長榮航", "zhang": 102134 }, ... ],  // 外資
  "trust":   [ ... ],   // 投信
  "dealer":  [ ... ]    // 自營商
}
```
- 單位為「張」（股數 ÷ 1000），只取買超（>0）前 5。
- `overview.tw.stats` 現含 外資/投信/自營 買賣超（`dir` 標漲跌色、正買超負賣超）。

## hot_stocks

```jsonc
"hot_stocks": {
  "tw": [ { "code": "2330", "name": "台積電", "change_pct": 2.1, "reason": "外資買超 1.8 萬張" }, ... ],
  "us": [ { "code": "NVDA", "name": "輝達", "change_pct": 3.4, "reason": "AI 晶片需求強" }, ... ]
}
```

## news / events / verdict

```jsonc
"news": [ { "tag": "neg", "title": "川普表示考慮對半導體進口加徵新關稅",
            "impact": "恐衝擊台廠美國出貨成本…", "source_name": "路透", "source_url": "https://…" } ],
            // tag: "pos" 利多 | "neg" 利空 | "neu" 中性

"upcoming_events": [ { "date": "2026-06-20", "name": "四巫日（三巫到期）", "analysis": "期權期貨結算…" } ],
"past_events_review": [ { "date": "2026-06-17", "name": "美國 5 月零售銷售", "result": "結果 +0.4% 優於預期…" } ],

"verdict": {                    // 台美分列
  "tw": { "stance": "偏多", "score": 70, "comment": "…",
          "bullish": [...], "bearish": [...], "risks": [...] },
  "us": { "stance": "偏多", "score": 72, "comment": "…",
          "bullish": [...], "bearish": [...], "risks": [...] }
}
// stance: 偏多/中性偏多/中性/中性偏空/偏空；score 0~100(0極空 50中性 100極多)
```

前端日期顯示用 `date` 解析出月/日；events 的月縮寫由前端產生（JUN…）。

## breadth（市場寬度，選填・2026-07-03 新增）

```jsonc
"breadth": { "up": 649, "up_limit": 54, "down": 323, "down_limit": 1, "flat": 75 }
```
- 台股全市場（僅一般股票，不含 ETF/權證）當日漲跌家數。來源 TWSE RWD `MI_INDEX?type=MS`。
- `up_limit`/`down_limit` 為其中漲停/跌停家數。
- 抓不到時整欄為 `null`（`_meta.missing` 會記一筆），前端與 notify 皆須容忍缺欄。
- 同步併入 `overview.tw.stats`（一筆「漲跌家數」tile），供既有台股總覽卡直接顯示，不需新前端元件。

## margin（融資餘額，選填・2026-07-03 新增）

```jsonc
"margin": {
  "listed": { "balance_yi": 6208.4, "change_yi": 113.3 },   // 上市，億元
  "otc":    { "balance_yi": 2103.4, "change_yi": 19.2 },    // 上櫃，億元（若抓不到為 null）
  "total_yi": 8311.8, "total_change_yi": 132.5              // 上市+上櫃合計（兩者皆有才算）
}
```
- 上市來源 TWSE `exchangeReport/MI_MARGN?selectType=MS`（信用交易統計・融資金額列）。
- 上櫃來源 TPEX `www/zh-tw/margin/balance`（summary 彙總列）。
- 任一市場抓不到就該子欄位為 `null`、`total_yi`/`total_change_yi` 一併省略；不得讓流程掛掉。
- 同步併入 `overview.tw.stats`（一筆「融資餘額」tile）。

## earnings_tomorrow（明日法說會，選填・2026-07-03 新增）

```jsonc
"earnings_tomorrow": [ { "id": "2330", "name": "台積電", "industry": "半導體" }, ... ]
```
- 跨專案互串：讀 `tw-earnings-calendar` 專案 GitHub Pages 公開的
  `https://andy30019123agent-ship-it.github.io/tw-earnings-calendar/data/latest.json`，
  取 `date` 為「明天（台北時間）」且 `type` 為「法說會」的事件。
- 失敗安全：連線/格式錯誤一律回空陣列 `[]`，不擋主流程、不擋部署，Telegram 與前端該段靜默跳過。
- Telegram 推播最多列 5 筆，超過附「等 N 場」。

## regime（市場紅綠燈，選填・2026-07-03 新增，元件 A）

```jsonc
"regime": {
  "light": "green",   // green|yellow|red
  "score": 4,          // 總分（趨勢 0~3 + 寬度/波動/籌碼各 -1~+1，範圍約 -3~6）
  "components": {
    "trend":   { "score": 2, "missing": false, "detail": { "close": 46744.16, "ma20": 45210.3, "ma60": 44012.1, "close_gt_ma20": true, "ma20_gt_ma60": true, "close_gt_ma60": true } },
    "breadth": { "score": 1, "missing": false, "detail": { "ratio": 0.62, "up": 649, "down": 323 } },
    "vix":     { "score": 0, "missing": false, "detail": { "value": 22.4 } },
    "chips":   { "score": 1, "missing": false, "detail": { "net_yi": 128.4, "days_used": 5 } }
  }
}
```
- 計分規則常數集中在 `scripts/regime.py`（純函式，見檔頭註解）：
  - 趨勢：收盤>MA20（+1）、MA20>MA60（+1）、收盤>MA60（+1）
  - 寬度：上漲家數佔比 >55%（+1）、<45%（−1）
  - 波動：台指 VIX <20（+1）、>28（−1）
  - 籌碼：三大法人近 5 日合計淨買超 >0（+1）、<0（−1）
  - 總分 ≥3 → 🟢 green；0~2 → 🟡 yellow；<0 → 🔴 red
- 任一分項缺資料 → 該項 0 分、`missing: true`，不擋主流程。
- MA20/MA60 用的收盤序列來自獨立檔 `public/data/index-history.json`（見下）。
- 舊資料檔沒有這個欄位是正常的（回填前的歷史檔），前端與 notify 皆須容忍缺欄。

## index-history.json（台股加權指數歷史收盤，選填輔助檔・2026-07-03 新增）

```jsonc
// public/data/index-history.json
{ "history": [ { "date": "2026-01-05", "close": 44120.3 }, ... ] }   // 由舊到新
```
- 獨立於逐日 `<date>.json`（那份只從 2026-06-18 起，不足 60 個交易日算 MA60）。
- 回填：`python -m scripts.backfill_index_history`（一次性，可重跑，日期去重合併）。
- 每日流程：`fetch_hard_data.py` 抓到當日收盤後自動把當天併入這份檔案。
- 只保留最近 300 個交易日（`scripts/lib/index_history.py` 的 `MAX_ENTRIES`），避免無限增肥。

## inst_net_yi（三大法人大盤合計淨買超，選填・2026-07-03 新增）

```jsonc
"inst_net_yi": { "外資": 128.4, "投信": -12.0, "自營": 3.5 }   // 億元，null 代表當日抓取失敗
```
- 與 `overview.tw.stats` 裡格式化字串（如「+128.4 億」）同一份原始數據，這裡是給
  `regime.py` 籌碼分項做「近 5 日合計」數學運算用的原始數值版本。
- 抓不到時整欄為 `null`；`accuracy.py`／`regime` 聚合會自動略過缺值的天數，不炸。

## opportunities（機會股 Top 5，選填・2026-07-03 新增，元件 C，跨專案互串）

```jsonc
"opportunities": {
  "date": "2026-07-03",
  "picks": [
    { "id": "2330", "name": "台積電", "score": 8, "reasons": ["外資連買", "均線多頭"],
      "close": 1105, "support_ma20": 1080, "recent_high20": 1120, "rs20": 1.32,
      "revenue_yoy": 0.18, "earnings_date": "2026-07-17", "risk_flags": [] }
  ]
}
```
- 跨專案互串：讀 `tw-stock-screener` 專案 GitHub Pages 公開的
  `https://andy30019123agent-ship-it.github.io/tw-stock-screener/data/opportunities.json`。
- 欄位契約由 `tw-stock-screener` 該專案定義（見其 `pipeline/backtest_signals.py` 相關規格）；
  本專案只負責讀取、不驗證細節欄位。
- 失敗安全：該檔尚未上線／連線失敗／`picks` 為空，一律回 `None`，Telegram 晚報整段靜默省略，
  不擋主流程、不擋部署。目前前端未顯示此區塊（Top 5 卡片是 tw-stock-screener 網站自己的職責），
  本專案僅用於推播晚報彙整。
