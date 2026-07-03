# 低基期潛力分數：回測調整權重設計

- 日期：2026-07-04（Asia/Taipei）
- 狀態：approach 已 Andy 確認（做 B、題材不進回測、**不加類股、維持籌碼/價量/基本面三項**、資料源交我評估）；待 spec 審閱
- 前置：延續 `2026-07-04-radar-and-potential-upgrade-design.md`（發動信心分數）。本 spec 新增「回測調權重」離線研究工具。

## 背景與目標

目前發動信心分數的權重（籌碼 0.35／價量結構 0.35／題材 0.20／基本面 0.10）是人工拍板的。Andy 要求用**歷史回測**客觀決定各子分佔比。

**目標**：用過去 N 個月的歷史資料，量測「低基期候選股入選後的真實未來報酬」，找出讓「高分股報酬明顯贏過低分股」的最佳權重組合，出一份**建議報告**。

## 範圍與非目標

- **回測只調三項**：籌碼、價量結構、基本面（Andy 2026-07-04 決定不加類股、維持原三項）。
- **題材分不進回測**：AI 當下上網查的發酵點無法回溯到過去某天重算，硬湊會有「用未來資訊作弊」的偏誤。題材維持固定加分、不被回測調整。
- **離線研究工具**：獨立 CLI，手動執行，**不進每日 CI、不影響線上每日選股**。
- **不自動套用**：回測算出的權重是「建議」，出報告給 Andy 看，**由他確認後手動改 `potential.py DEFAULTS`**。
- **研究參考非保證**：回測是過去統計，不保證未來。報告須標註樣本數與過度配適風險。
- **先 spike 後放大**：先回測 2～3 個月驗證資料源與流程，OK 再拉長到 6～12 個月。
- 不新增評分子分、不動線上評分模型（只調既有三項權重的建議值）。

## 資料源（混用，全免費、皆快取）

| 資料 | 來源 | 取法 | 備註 |
|---|---|---|---|
| 三大法人買賣超（籌碼） | **TWSE 官方 T86**（`www.twse.com.tw/rwd/zh/fund/T86?date=YYYYMMDD&selectType=ALLBUT0999&response=json`） | 每交易日一次、回全市場所有個股 | 權威、對回測高效；上櫃另走 TPEX（spike 先做上市，上櫃列為延伸） |
| 歷史日 K（價量、報酬） | **FinMind** `TaiwanStockPrice` | 每檔一次回整段歷史 | 省工；上市+上櫃通用 |
| 月營收（基本面） | **FinMind** `TaiwanStockMonthRevenue` | 每檔一次 | 沿用線上既有 `finmind_revenue` |

- **快取**：`backtest/cache/`（gitignore）。per-date T86 JSON、per-stock 價量 JSON、per-stock 營收 JSON 抓過即存，不重抓。
- **節奏**：TWSE 用既有 `get_text`（curl `--http1.1 -4` 優先 + 重試退避 + 間隔）；FinMind 加 sleep。撞限流/維護回空→重試或跳過並記錄。

## 資料流與元件

1. **重建候選（每個 as-of 日期）**
   - 選一組回測基準日（視窗內每個交易日、或每週一次以省呼叫）。
   - 對每個基準日 D：用 D 往前 window 天的 T86 逐日資料，聚合各股法人淨買超＋買超天數 → 篩「近 N 日法人吸籌」候選（同線上 `pick_accumulators`）。
   - 對候選查 FinMind 一年日 K（**截止 D、不得用 D 之後資料**）算 price_pos/vol_ratio/above_ma60 → struct_s、低基期 gate；查月營收（截止 D）→ fund_s。
   - 產出每個候選的三子分（複用 `potential.py` 的 `chip_score / structure_score / fundamental_score`）。
2. **未來報酬**：`forward_return(price_rows, D, horizon)` = close(D+horizon 交易日)/close(D)−1，horizon 預設 20。資料不足（下市/停牌/缺）→ 該樣本剔除並計數。
3. **權重最佳化**：
   - 對權重單體（chip+struct+fund=1）以粗網格（步長 0.1）列舉組合（約 66 組）。
   - 每組：對每個候選算加權分數（題材分維持線上固定值或設 0，因不進回測）→ 計 metric。
   - **metric**：主用 Spearman 排序 IC（分數 vs 未來報酬），跨 as-of 日期取平均；輔以「高分五分位 − 低分五分位」平均報酬差。
   - 選 metric 最佳權重；報告列 Top 組合＋跨日期穩定度（變異）。
   - **過度配適防護**：把基準日切前後兩半，回報兩半各自最佳與交叉表現；報告明列樣本數與「僅研究參考」。

## 交付物

- `scripts/backtest_weights.py`（CLI：`--start --end --horizon --grid-step --rebalance {daily,weekly} --listed-only`）。
- 輸出 `backtest/report-<rundate>.md`（人看：建議三權重＋metric＋穩定度＋樣本數＋警語）與 `backtest/report-<rundate>.json`（機器讀：完整結果）。
- 純函式盡量複用 `potential.py`；回測專屬邏輯放 `scripts/lib/backtest.py`。

## 檔案影響

- `scripts/lib/backtest.py`（新）：`forward_return`、`rank_ic`、`quintile_spread`、`grid_search_weights`、`reconstruct_candidates`（純/可注入 fetch）。
- `scripts/lib/twse_hist.py`（新，或併入 backtest）：T86 逐日抓取＋快取。
- `scripts/backtest_weights.py`（新）：CLI 組裝＋抓取快取＋出報告。
- 測試：`scripts/tests/test_backtest.py`（純函式 TDD）。
- `.gitignore`：加 `backtest/cache/`。
- **`potential.py` 不改**（只回測既有三項權重，不動線上評分模型）。

## 測試策略

- 純函式 TDD：
  - `forward_return`：給定價序列與 D、horizon，回正確報酬；資料不足回 None。
  - `rank_ic`／`quintile_spread`：已知排序關係下數值正確。
  - `grid_search_weights`：**合成資料**——讓「籌碼高→未來報酬高」，驗證最佳權重確實偏向籌碼（優化器找得回真相）。
- 抓取函式：注入假 fetch，測快取命中/未命中、限流重試，**測試不打網路**。
- Spike 實跑：手動 2～3 個月，人工檢查報告產得出、權重合理、無明顯前視偏誤（截止日資料不含未來）。

## 待實作時確認/校準（非阻塞）

- 基準日頻率（每日 vs 每週）、horizon 天數、網格步長 → spike 後看呼叫量與訊號強度定。
- 上櫃是否納入（spike 先上市）。
- metric 主次（IC vs 五分位差）。

## 決策紀錄（已與 Andy 確認）

- 做法 B（歷史回測＋權重最佳化）；先 spike 再放大。
- **回測只調籌碼／價量結構／基本面三項**；題材固定不進回測；不加類股（維持原三項）。
- 資料源混用：法人 TWSE 官方 T86、價量/營收 FinMind（Andy 授權我評估後定案）。
- 離線研究工具、出建議報告、人工確認才套用、不碰線上每日選股。
