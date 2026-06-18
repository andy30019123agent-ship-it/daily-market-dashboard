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

"verdict": { "bullish": ["費半強漲…"], "bearish": ["關稅疑慮…"], "risks": ["四巫日結算波動"] }
```

前端日期顯示用 `date` 解析出月/日；events 的月縮寫由前端產生（JUN…）。
