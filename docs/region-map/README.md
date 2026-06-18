# 區塊對照表（Region Map）

調整畫面時，用下列編號或名稱指定區塊，溝通更快。
標註圖：`region-map-desktop.png`（桌機）、`region-map-mobile.png`（手機）。

| 編號 / 名稱 | 內容 | 元件檔 |
|---|---|---|
| 標題列 / 日期選單 | 大標題、副標、更新時間、月曆回看 | `src/App.jsx`、`src/components/DatePicker.jsx` |
| 跑馬燈行情帶 | 頂部滾動行情（台美關鍵指數 + VIX）| `src/components/Ticker.jsx` |
| 台股 / 美股 分頁 | 行情分頁切換 | `src/App.jsx` |
| ① 今日總覽 | 主指數大數字 + 走勢線 + 子數據（台股）；四指數（美股）| `src/components/Overview.jsx` |
| ② 市場情緒 VIX | VIX 數值 + 恐慌→貪婪色階刻度 | `src/components/Vix.jsx` |
| ③ 板塊資金流向 | 資金流入/流出 Top 5 + 橫條 | `src/components/Sectors.jsx` |
| ④ 熱門個股 | 熱門個股漲跌 + 緣由 | `src/components/HotStocks.jsx` |
| ⑤ 影響股市消息 | 川普及影響股市消息（附來源）| `src/components/CrossMarket.jsx` |
| ⑥ 本週重大日程 | 事前預告 + 影響分析 | `src/components/CrossMarket.jsx` |
| ⑦ 昨日日程回顧 | 已過日程的事後回顧 | `src/components/CrossMarket.jsx` |
| ⑧ 今日綜合研判 | 利多 / 利空 / 隱憂 | `src/components/CrossMarket.jsx` |

## 重新產生標註圖

```bash
npm run build && npm run preview -- --port 4173 &
# 網址加 ?annotate 顯示框線
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars \
  --screenshot=docs/region-map/region-map-desktop.png --window-size=1280,1720 \
  "http://localhost:4173/daily-market-dashboard/?annotate"
```
