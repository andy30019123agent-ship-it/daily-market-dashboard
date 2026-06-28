// 點指數/個股 → 跳出 TradingView 蠟燭圖（現行 Advanced Chart widget，舊 widgetembed 已被限制）
import { useEffect, useRef } from 'react'

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

function TVChart({ symbol }) {
  const ref = useRef(null)
  useEffect(() => {
    const host = ref.current
    if (!host || !symbol) return
    host.replaceChildren()
    const widget = document.createElement('div')
    widget.className = 'tradingview-widget-container__widget'
    widget.style.height = '100%'
    widget.style.width = '100%'
    host.appendChild(widget)
    const script = document.createElement('script')
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js'
    script.async = true
    script.type = 'text/javascript'
    script.text = JSON.stringify({
      symbol,
      interval: 'D',
      timezone: 'Asia/Taipei',
      theme: 'light',
      style: '1',
      locale: 'zh_TW',
      autosize: true,
      withdateranges: true,
      allow_symbol_change: false,
      hide_side_toolbar: true,
      studies: ['MASimple@tv-basicstudies'],
      support_host: 'https://www.tradingview.com',
    })
    host.appendChild(script)
    return () => { host.replaceChildren() }
  }, [symbol])
  return <div className="tradingview-widget-container chart-frame" ref={ref} />
}

export default function ChartModal({ target, onClose }) {
  if (!target) return null
  const symbol = resolveSymbol(target)
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
        {symbol ? (
          <TVChart symbol={symbol} />
        ) : (
          <div className="modal-empty">此標的暫無對應圖表</div>
        )}
        <div className="modal-foot">
          資料來源：TradingView · 可切換週期、縮放、加指標 ·{' '}
          <a href={`https://www.tradingview.com/chart/?symbol=${encodeURIComponent(symbol || '')}`}
             target="_blank" rel="noopener noreferrer">在 TradingView 開啟 ↗</a>
        </div>
      </div>
    </div>
  )
}
