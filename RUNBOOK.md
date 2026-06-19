# 每日執行手冊（RUNBOOK）

> 給每天 18:43（台北）被喚醒的 AI 分身照著做。目標：產出當日完整儀表板資料、部署上線、Telegram 推播摘要。任一步失敗都要通知，不可靜默。

## 前置

- 時區一律台北（Asia/Taipei）。先 `date` 確認。
- 工作目錄：`~/Desktop/agent/daily-market-dashboard`
- 需要：Alpha Vantage 金鑰在 `scripts/secrets.json`（或環境變數 `AV_API_KEY`）。

## 步驟

### 1. 抓硬數據
```bash
python3 scripts/fetch_hard_data.py
```
- 產生 `public/data/<最新交易日>.partial.json`。
- 內含（皆真實）：台股加權/成交金額/三大法人(外資投信自營,大盤金額+個股買賣超雙榜)/類股漲跌/漲幅榜；美股道瓊/標普/那斯達克(FRED)+費半SOX(SOXX)+美股熱門股+美股11類股(AV)；美股 VIX(FRED)。
- 檢查終端輸出的 `errors`（理想為空）與 `missing`。記下 `_meta.trade_date`（= 報告日期）。

### 2. 軟情報（分身親自上網判讀）
產出一個 `soft` dict，餵給 merge：
- **news**：用 WebSearch 找**最近 24 小時內**的台股盤後、美股、影響股市消息（川普/聯準會/關稅/AI/地緣）。每條：`{tag(pos/neg/neu), title, impact, source_name, source_url}`，**source_url 必須是該篇文章本身**，不可用首頁。3~4 則。
- **台指 VIX**（`vix_tw`）：WebFetch `https://www.wantgoo.com/index/vixtwn` 取最新 VIXTWN 值與漲跌；gauge = `clamp(1-(值-10)/30, 0, 1)`。
- **vix_us**：補 state/note（數值已由硬數據帶入）。gauge 同公式。
- **hot_tw_reasons**：`{股票代號: 緣由}`，依當日新聞補（漲停可寫「亮燈漲停」）。
- **upcoming_events / past_events_review**：用 `scripts/lib/events.py` 比對本週重大日（四巫日等），FOMC/CPI/非農/台積電法說等用 WebSearch 確認日期；過去的寫事後回顧。
- **verdict**：`{stance, score, comment, bullish[], bearish[], risks[]}`。
  - `bullish/bearish/risks`：條列利多/利空/隱憂。
  - **`stance`**：綜合所有蒐集資訊後的多空總評，用詞如「偏多 / 中性偏多 / 中性 / 中性偏空 / 偏空」。
  - **`score`**：0~100（0 極空、50 中性、100 極多），給多空儀表用。
  - **`comment`**：1~2 句綜述，說明為何下這個多空判斷（整合硬數據 + 新聞 + 風險）。
- **summary**：3~5 句，台美兩地重點，給 Telegram 用。

### 3. 合併 + 驗證
```python
from scripts.merge_day import merge_day, update_index
from scripts.lib.schema import validate_day
day = merge_day(partial, soft, date, updated_at="<台北 YYYY-MM-DD HH:MM>")
assert validate_day(day) == []          # 不通過就修，別上線壞資料
# 寫 public/data/<date>.json、update_index(date)
```

### 4. 部署
```bash
npm run deploy        # vite build + gh-pages
```
等 GitHub Pages 生效（約 1~2 分），可選擇截圖驗證。

### 5. Telegram 推播
```python
from scripts.notify import build_summary_text
text = build_summary_text(day)     # 摘要 + 連結
# 用 telegram reply 工具發給 chat_id 542348223
```

## 失敗處理（重要）

任一步驟拋錯：
```python
from scripts.notify import build_failure_text
# 用 telegram reply 發 build_failure_text(原因) 給 chat_id 542348223
```
**絕不靜默失敗。** 硬數據部分失敗（errors 非空）但仍可出刊時，照常出刊並在 Telegram 註明哪些缺漏。

## 規則速記
- 軟情報每條附真實來源連結。
- 數據以官方/實測為準，寧缺勿假。
- 中文與英數間加半形空格。
- Alpha Vantage 免費版 25 次/日、5 次/分；fetch 已內建間隔，勿短時間重跑多次。
