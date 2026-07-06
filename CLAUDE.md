> 🧠 開工前先讀 `~/Desktop/agent/harness/thinking-core.md`（開工協定＋宣稱前防幻覺查核）；活大就派 subagent（`~/Desktop/agent/harness/model-dispatch.md` 紅線）。
> 回報、提問、要 Andy 選擇：一律照根目錄 `~/Desktop/agent/CLAUDE.md` 鐵則用 reply 工具發到頻道（純文字編號清單）；時間一律台北時間。
> 本專案現況與雷點以下文為準；改前先讀檔，改後實跑驗證才算完成。

# daily-market-dashboard

每日台美股戰略儀表板網站，給 Andy 看盤用：抓真實台美股數據＋AI 產軟情報，每個交易日自動推送。

**技術棧**：Vite + React（lightweight-charts、lucide-react）
**指令**：`npm run dev` / `npm run build` / `npm run preview` / `npm test`（vitest run）
**部署**：`npm run deploy`（`vite build && gh-pages -d dist`）

專案現況與踩雷紀錄見記憶檔 `project_daily_market_dashboard.md`。

有 GitHub Actions 每個交易日台北 18:36 自動抓資料＋產軟情報＋部署＋推 TG，正在線上運作中——改排程前先看記憶檔，別動到正在跑的排程。
