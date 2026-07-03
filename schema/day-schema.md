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
