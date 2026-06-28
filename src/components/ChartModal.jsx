import { useEffect, useRef, useState } from 'react'
import { createChart } from 'lightweight-charts'

// 台股 K 線：用免費 FinMind 抓日 K，TradingView 開源套件 lightweight-charts 直接畫在彈窗裡。
// 美股 FinMind 無資料 → 維持外開看盤站；台股抓不到 → 退回外開連結當保險。
const TW_INDEX = { '發行量加權股價指數': 'TAIEX', '加權': 'TAIEX' }
const US_TV = { '道瓊': 'DJ-DJI', '標普 500': 'SP-SPX', '那斯達克': 'NASDAQ-IXIC', '費城半導體': 'NASDAQ-SOX' }

// 回傳 FinMind 可抓的台股代碼（個股 4 碼 / 加權 TAIEX），非台股回 null
function finmindId(t) {
  const code = (t.code || '').trim()
  if (/^\d{4}$/.test(code)) return code
  if (t.type === 'index' && TW_INDEX[t.name]) return TW_INDEX[t.name]
  return null
}

// 外部免費看盤站連結（美股用 / 台股抓不到時的保險）
function chartLinks(t) {
  if (!t) return []
  const code = (t.code || '').trim()
  if (/^\d{4}$/.test(code)) return [
    { label: 'Goodinfo K 線', url: `https://goodinfo.tw/tw/ShowK_Chart.asp?STOCK_ID=${code}` },
    { label: 'WantGoo 玩股網', url: `https://www.wantgoo.com/stock/${code}/technical-chart` },
    { label: '鉅亨網', url: `https://www.cnyes.com/twstock/${code}/charts/technical-history` },
  ]
  if (t.type === 'index') {
    if (TW_INDEX[t.name]) return [
      { label: 'Goodinfo 大盤 K 線', url: 'https://goodinfo.tw/tw/ShowK_Chart.asp?STOCK_ID=IX0001' },
      { label: '鉅亨網 加權指數', url: 'https://www.cnyes.com/twstock/IX0001/charts/technical-history' },
    ]
    if (US_TV[t.name]) return [
      { label: 'TradingView', url: `https://www.tradingview.com/symbols/${US_TV[t.name]}/` },
      { label: 'Yahoo Finance', url: `https://finance.yahoo.com/quote/%5E${US_TV[t.name].split('-')[1]}` },
    ]
  }
  if (code) return [
    { label: 'TradingView', url: `https://www.tradingview.com/symbols/${code}/` },
    { label: 'Yahoo Finance', url: `https://finance.yahoo.com/quote/${code}` },
  ]
  return []
}

function startDate(months = 8) {
  const d = new Date(); d.setMonth(d.getMonth() - months)
  return d.toISOString().slice(0, 10)
}

// 簡單移動平均（給 MA 線用）
function sma(rows, n) {
  const out = []
  for (let i = n - 1; i < rows.length; i++) {
    let s = 0
    for (let j = i - n + 1; j <= i; j++) s += rows[j].close
    out.push({ time: rows[i].time, value: +(s / n).toFixed(2) })
  }
  return out
}

function LinksView({ links }) {
  return (
    <div className="chart-links">
      <div className="chart-links-hint">選一個免費看盤站開啟 K 線（新分頁）：</div>
      <div className="chart-links-btns">
        {links.map((l) => (
          <a key={l.url} className="chart-link-btn" href={l.url} target="_blank" rel="noopener noreferrer">{l.label} ↗</a>
        ))}
      </div>
    </div>
  )
}

// 台股：抓 FinMind → 畫蠟燭圖
function TWKChart({ id, links }) {
  const wrapRef = useRef(null)
  const [state, setState] = useState('loading') // loading | ready | error

  useEffect(() => {
    let chart, cancelled = false
    async function run() {
      setState('loading')
      try {
        const url = `https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&data_id=${id}&start_date=${startDate()}`
        const res = await fetch(url)
        if (!res.ok) throw new Error('quota')
        const json = await res.json()
        const rows = (json.data || [])
          .map((d) => ({ time: d.date, open: d.open, high: d.max, low: d.min, close: d.close }))
          .filter((d) => d.open != null && d.close != null)
        if (cancelled) return
        if (!rows.length) throw new Error('empty')

        const host = wrapRef.current
        if (!host) return
        host.replaceChildren()
        chart = createChart(host, {
          autoSize: true,
          layout: { background: { color: 'transparent' }, textColor: '#6b5566', fontFamily: 'inherit' },
          grid: { vertLines: { color: 'rgba(150,90,140,.08)' }, horzLines: { color: 'rgba(150,90,140,.08)' } },
          rightPriceScale: { borderColor: 'rgba(150,90,140,.18)' },
          timeScale: { borderColor: 'rgba(150,90,140,.18)', timeVisible: false },
          crosshair: { mode: 1 },
          localization: { locale: 'zh-TW' },
        })
        // 台股漲紅跌綠
        const candle = chart.addCandlestickSeries({
          upColor: '#E23B4E', downColor: '#16A34A',
          wickUpColor: '#E23B4E', wickDownColor: '#16A34A', borderVisible: false,
        })
        candle.setData(rows)
        if (rows.length >= 20) {
          const ma = chart.addLineSeries({ color: '#D9881C', lineWidth: 2, priceLineVisible: false, lastValueVisible: false })
          ma.setData(sma(rows, 20))
        }
        chart.timeScale().fitContent()
        setState('ready')
      } catch (e) {
        if (!cancelled) setState('error')
      }
    }
    run()
    return () => { cancelled = true; if (chart) chart.remove() }
  }, [id])

  if (state === 'error') {
    return (
      <div className="chart-links">
        <div className="chart-links-hint">⚠️ 即時 K 線資料抓取失敗（可能是免費額度暫滿），改用外部看盤站：</div>
        <div className="chart-links-btns">
          {links.map((l) => (
            <a key={l.url} className="chart-link-btn" href={l.url} target="_blank" rel="noopener noreferrer">{l.label} ↗</a>
          ))}
        </div>
      </div>
    )
  }
  return (
    <div className="chart-canvas-wrap">
      {state === 'loading' && <div className="chart-loading"><div className="spin" />載入 K 線中…</div>}
      <div className="chart-canvas" ref={wrapRef} />
    </div>
  )
}

export default function ChartModal({ target, onClose }) {
  if (!target) return null
  const id = finmindId(target)
  const links = chartLinks(target)
  const drawable = !!id
  return (
    <div className="modal-back" onClick={onClose}>
      <div className={'chart-box ' + (drawable ? 'chart-box-draw' : 'chart-box-links')} onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <span className="modal-title">
            {target.name}
            {target.code ? <span className="modal-sub">{target.code}</span> : null}
            <span className="modal-sub">日 K 線{drawable ? ' · 近 8 個月' : ''}</span>
          </span>
          <button className="modal-x" onClick={onClose} aria-label="關閉">✕</button>
        </div>
        {drawable
          ? <TWKChart id={id} links={links} />
          : (links.length ? <LinksView links={links} /> : <div className="modal-empty">此標的暫無對應圖表</div>)}
        <div className="modal-foot">
          {drawable
            ? <>資料來源：FinMind · 漲<b style={{ color: '#E23B4E' }}>紅</b>跌<b style={{ color: '#16A34A' }}>綠</b> · 橘線＝20 日均線</>
            : '外部看盤站皆為免費；美股／加權嵌入式即時 K 線受資料授權限制，故採外開。'}
        </div>
      </div>
    </div>
  )
}
