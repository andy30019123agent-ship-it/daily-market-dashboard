# STATUS — 每日台美股戰略儀表板

> 最後更新：2026-06-20（台北）｜ 啟動觸發語：**「繼續台美股戰報專案」**

## 現況（一句話）
獨立網站，每個交易日台北 18:36 由 GitHub Actions 自動抓真實數據＋AI 產軟情報→部署→推 Telegram；已完整上線運作。

## 上次做到哪
- 8 區塊：今日總覽（台股加權/三大法人、美股四大指數+費半）、VIX 情緒、類股資金、熱門個股、消息（附來源）、本週日程、昨日回顧、台美分列綜合研判。
- 真實數據：台股 TWSE RWD、美股 Yahoo（^DJI/^GSPC/^IXIC/^SOX/^VIX）、費半真指數、AV/finviz 類股；K 線用 TradingView iframe。
- 自動化＝**GitHub Actions**（已放棄 Anthropic 雲端排程 CCR，因沙箱連不出 Telegram/證交所）。軟情報用 OpenAI `gpt-4o-search-preview`。防重複推播 notify_state。

## 下一步（1–3 件）
1. 觀察每日排程穩定度與產出正確性（AV 免費 25 次/日是脆弱點，備援 investing/finviz）。
2. 台指 VIX 目前沿用前值 → 要自動化得找 JS 渲染源/TAIFEX 端點。
3. 視情況微調研判與版面。

## 怎麼啟動 / 在哪
- 資料夾：`~/Desktop/agent/daily-market-dashboard/`；repo 同名。
- 線上：https://andy30019123agent-ship-it.github.io/daily-market-dashboard/
- 自動化：`.github/workflows/daily.yml`（cron 台北 18:36 一~五）；密鑰 OPENAI_API_KEY/AV_API_KEY/TG_BOT_TOKEN 在 GitHub Secret。
- 本機：`OPENAI_API_KEY=... python3 -m scripts.auto_daily --dry-run`；手動觸發 `gh workflow run daily.yml`。流程見 `RUNBOOK.md`。
- 詳細脈絡：專案記憶 `project_daily_market_dashboard.md`。
