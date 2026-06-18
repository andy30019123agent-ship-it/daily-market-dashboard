# 資料源驗證結論（Task 0 Spike）

> 實測日期：2026-06-18（台北）。所有端點以當下實測為準，免費源隨時可能變動，正式抓取需做失敗處理。

## ✅ 確認可用（免費、免金鑰）

### 台股（TWSE 證交所 OpenAPI）— 全數可用
| 用途 | URL | 關鍵欄位 |
|---|---|---|
| 大盤各指數每日收盤 | `https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX` | `指數`=「發行量加權股價指數」、`收盤指數`、`漲跌`、`漲跌點數`、`漲跌百分比` |
| 大盤成交量歷史（含 TAIEX） | `https://openapi.twse.com.tw/v1/exchangeReport/FMTQIK` | `Date`、`TradeValue`(成交金額)、`TAIEX`、`Change`；近一個月，可做量能走勢 |
| 個股當日成交（全市場） | `https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL` | `Code`、`Name`、`ClosingPrice`、`Change`、`TradeValue`、`TradeVolume`；可排漲幅榜/爆量榜當熱門股 |

- 日期為民國格式：`1150617` = 2026/06/17，需轉換。
- 約 22:50 實測時 MI_INDEX 仍是前一交易日（06/17），STOCK_DAY_ALL 已是當日（06/18）；正式跑在 18:43，盤後資料通常已更新，仍需容忍偶發延遲。

### 櫃買（TPEX 櫃買中心 OpenAPI）— 可用
| 用途 | URL | 備註 |
|---|---|---|
| 上櫃個股報價 | `https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes` | 含 `Close`/`Change`/OHLC；櫃買指數另有對應端點待確認 |

### 美股指數（FRED 美國聯準會）— 取代失效的 stooq
| 指數 | URL（CSV，免金鑰） |
|---|---|
| 標普 500 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500` |
| 道瓊 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DJIA` |
| 那斯達克綜合 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=NASDAQCOM` |
| 那斯達克 100 | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=NASDAQ100` |
| CBOE VIX（情緒指標） | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS` |

- 回傳整段日線收盤（`觀測日,數值`），可做**收盤線圖**與算漲跌幅（今收 vs 前一日收）。
- ⚠️ **只有收盤價，無 OHLC**，故美股 K 線只能畫「收盤線圖」，畫不出蠟燭。
- 有約 1 個交易日延遲，且僅美國交易日有值（假日空白要過濾）。

## ❌ 失效 / 被擋（原計劃假設已不可用）

| 來源 | 狀態 | 影響 |
|---|---|---|
| **stooq**（原美股主力 CSV） | 加了 JavaScript PoW 驗證關卡，程式抓不到 | 美股指數改用 FRED ✅ |
| **Yahoo Finance** | 整段 IP 回 429 Too Many Requests，crumb 流程也被擋 | 不作主力，僅人工備援 |
| **CNN Fear & Greed** | 回 418「I'm a teapot. You're a bot.」擋爬蟲 | 不影響：情緒指標已改用 VIX（FRED 可取得）✅ |

## ⚠️ 無乾淨免費 API、改由分身每日 WebSearch 補

| 項目 | 原因 | 對策 |
|---|---|---|
| **費半 SOX** | FRED 無此序列，stooq/Yahoo 已死 | 分身每日跑排程時 WebSearch 當日 SOX 收盤與漲跌，寫入 JSON |
| **台指 VIX** | 無確認的免費 JSON 端點（TAIFEX 待查） | 同上，WebSearch 補；或僅以 CBOE VIX 呈現美股情緒、台股情緒改回漲跌家數近似 |
| **台股外資買賣超** | TWSE 三大法人 JSON 端點需再確認（測到的回 HTML/302） | 從 TWSE OpenAPI 目錄找正確端點；非阻塞 |
| **台股個股 K 線歷史** | FinMind 有額度限制 | 後續處理；當日熱門股先用 STOCK_DAY_ALL 即可 |

## 核心結論

1. **台股硬數據完全沒問題**（TWSE + TPEX 官方免費 OpenAPI）。
2. **美股四大指數**：標普/道瓊/那斯達克用 FRED 取得（線圖、漲跌幅 OK，無蠟燭）；**費半 SOX 需分身 WebSearch 補**。
3. **情緒指標**：CBOE VIX 用 FRED；台指 VIX 需 WebSearch 或退回漲跌家數近似。
4. 原計劃主力 **stooq 已死、Yahoo 被限流、CNN 擋爬蟲** —— 但因架構是「分身親自跑排程」，這些缺口可由我每天 WebSearch 直接補上，不必依賴脆弱爬蟲。這反而更貼合「甲方案：分身親自判讀」的決策。
