// 點指數/個股 → K 線圖。
// 註：TradingView 免費嵌入 widget 不提供台股資料（顯示「此商品僅在 TradingView 上可用」），
// 瀏覽器直連 TWSE 又有 CORS，故改為「一鍵開啟外部免費 K 線圖」（新分頁、最可靠）。
const TW_INDEX = { '發行量加權股價指數': 'IX0001', '加權': 'IX0001' }
const US_TV = {
  '道瓊': 'DJ-DJI', '標普 500': 'SP-SPX', '那斯達克': 'NASDAQ-IXIC', '費城半導體': 'NASDAQ-SOX',
}

// 回傳該標的的外部 K 線連結清單 [{label, url}]
function chartLinks(t) {
  if (!t) return []
  const code = (t.code || '').trim()
  if (/^\d{4}$/.test(code)) {  // 台股個股
    return [
      { label: 'Goodinfo K 線', url: `https://goodinfo.tw/tw/ShowK_Chart.asp?STOCK_ID=${code}` },
      { label: 'WantGoo 玩股網', url: `https://www.wantgoo.com/stock/${code}/technical-chart` },
      { label: '鉅亨網', url: `https://www.cnyes.com/twstock/${code}/charts/technical-history` },
    ]
  }
  if (t.type === 'index') {
    if (TW_INDEX[t.name]) {  // 台股指數（加權）
      return [
        { label: 'Goodinfo 大盤 K 線', url: `https://goodinfo.tw/tw/ShowK_Chart.asp?STOCK_ID=${TW_INDEX[t.name]}` },
        { label: '鉅亨網 加權指數', url: `https://www.cnyes.com/twstock/${TW_INDEX[t.name]}/charts/technical-history` },
      ]
    }
    if (US_TV[t.name]) {  // 美股指數
      return [
        { label: 'TradingView', url: `https://www.tradingview.com/symbols/${US_TV[t.name]}/` },
        { label: 'Yahoo Finance', url: `https://finance.yahoo.com/quote/%5E${US_TV[t.name].split('-')[1]}` },
      ]
    }
  }
  if (code) {  // 美股個股 ticker
    return [
      { label: 'TradingView', url: `https://www.tradingview.com/symbols/${code}/` },
      { label: 'Yahoo Finance', url: `https://finance.yahoo.com/quote/${code}` },
    ]
  }
  return []
}

export default function ChartModal({ target, onClose }) {
  if (!target) return null
  const links = chartLinks(target)
  return (
    <div className="modal-back" onClick={onClose}>
      <div className="chart-box chart-box-links" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <span className="modal-title">
            {target.name}
            {target.code ? <span className="modal-sub">{target.code}</span> : null}
            <span className="modal-sub">K 線圖</span>
          </span>
          <button className="modal-x" onClick={onClose} aria-label="關閉">✕</button>
        </div>
        {links.length ? (
          <div className="chart-links">
            <div className="chart-links-hint">選一個免費看盤站開啟 K 線（新分頁）：</div>
            <div className="chart-links-btns">
              {links.map((l) => (
                <a key={l.url} className="chart-link-btn" href={l.url}
                   target="_blank" rel="noopener noreferrer">{l.label} ↗</a>
              ))}
            </div>
          </div>
        ) : (
          <div className="modal-empty">此標的暫無對應圖表</div>
        )}
        <div className="modal-foot">外部看盤站皆為免費；台股嵌入式即時 K 線受資料授權限制，故採外開。</div>
      </div>
    </div>
  )
}
