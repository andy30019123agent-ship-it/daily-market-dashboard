// 點指數/個股 → 跳出 TradingView 蠟燭圖（互動、含均線/週期切換/縮放）
const INDEX_SYMBOLS = {
  '發行量加權股價指數': 'TWSE:TAIEX',
  '加權': 'TWSE:TAIEX',
  '道瓊': 'DJ:DJI',
  '標普 500': 'SP:SPX',
  '那斯達克': 'NASDAQ:IXIC',
  '費城半導體': 'NASDAQ:SOX',
}

// 台股代號（4 碼數字）→ TWSE:xxxx；美股 → ticker 直接用
function resolveSymbol(t) {
  if (!t) return null
  if (t.type === 'index') return INDEX_SYMBOLS[t.name] || null
  const code = (t.code || '').trim()
  if (/^\d{4}$/.test(code)) return `TWSE:${code}`
  return code || null
}

export default function ChartModal({ target, onClose }) {
  if (!target) return null
  const symbol = resolveSymbol(target)
  const src = symbol
    ? `https://s.tradingview.com/widgetembed/?symbol=${encodeURIComponent(symbol)}` +
      `&interval=D&theme=light&style=1&timezone=Asia/Taipei&withdateranges=1` +
      `&hide_side_toolbar=1&locale=zh_TW&studies=%5B%22MASimple%40tv-basicstudies%22%5D`
    : null

  return (
    <div className="modal-back" onClick={onClose}>
      <div className="chart-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <span className="modal-title">
            {target.name}
            {target.code ? <span className="modal-sub">{target.code}</span> : null}
            <span className="modal-sub">日 K 線</span>
          </span>
          <button className="modal-x" onClick={onClose} aria-label="關閉">✕</button>
        </div>
        {src ? (
          <iframe className="chart-frame" src={src} title={`${target.name} K線`}
            allow="clipboard-write" loading="lazy" />
        ) : (
          <div className="modal-empty">此標的暫無對應圖表</div>
        )}
        <div className="modal-foot">資料來源：TradingView · 可切換週期、縮放、加指標</div>
      </div>
    </div>
  )
}
