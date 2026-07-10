import { useState, useEffect, useCallback } from 'react'
import { AlertTriangle, Globe2 } from 'lucide-react'
import { loadIndex, loadDay, loadAccuracy } from './lib/loadDay.js'
import Hero from './components/Hero.jsx'
import { OverviewTW, OverviewUS } from './components/Overview.jsx'
import Vix from './components/Vix.jsx'
import Sectors from './components/Sectors.jsx'
import HotStocks from './components/HotStocks.jsx'
import InstTop from './components/InstTop.jsx'
import Radar from './components/Radar.jsx'
import WarRoom from './components/WarRoom.jsx'
import MarketLinks from './components/MarketLinks.jsx'
import RegimeTile from './components/RegimeTile.jsx'
import { News, UpcomingEvents, PastReview, Verdict } from './components/CrossMarket.jsx'
import ChartModal from './components/ChartModal.jsx'

// 資料完整度：只在「有缺漏」時顯示提示條（完整就不干擾），誠實告知哪塊沒抓到、勿當市場訊號
function DataHealth({ warnings }) {
  if (!Array.isArray(warnings) || !warnings.length) return null
  return (
    <div className="datahealth" role="status">
      <AlertTriangle size={16} strokeWidth={1.75} />
      <span>今日部分資料缺漏：<b>{warnings.join('、')}</b> · 其餘照常，缺漏處以「—」顯示，請勿當市場訊號解讀</span>
    </div>
  )
}

export default function App() {
  const [dates, setDates] = useState([])
  const [date, setDate] = useState(null)
  const [day, setDay] = useState(null)
  const [accuracy, setAccuracy] = useState(null)
  const [tab, setTab] = useState(() =>
    typeof window !== 'undefined' && window.location.hash.includes('us') ? 'us' : 'tw')

  const switchTab = (t) => {
    setTab(t)
    if (typeof window !== 'undefined') window.location.hash = t === 'us' ? 'us' : ''
  }
  const [status, setStatus] = useState('loading') // loading | ready | error
  const [err, setErr] = useState('')

  const boot = useCallback(async () => {
    setStatus('loading'); setErr('')
    try {
      const idx = await loadIndex()
      if (!idx.length) throw new Error('目前沒有任何報告資料')
      setDates(idx)
      const latest = idx[0]
      setDate(latest)
      setDay(await loadDay(latest))
      setStatus('ready')
    } catch (e) {
      setErr(e.message || '載入失敗'); setStatus('error')
    }
  }, [])

  useEffect(() => { boot() }, [boot])

  // 研判成績單獨立於主戰報載入，失敗不影響戰報顯示
  useEffect(() => { loadAccuracy().then(setAccuracy) }, [])

  // 標註模式：網址帶 ?annotate 顯示各區塊框線與名稱（方便溝通要調整哪一區）
  useEffect(() => {
    if (/annotate/.test(window.location.search) || /annotate/.test(window.location.hash)) {
      document.body.classList.add('annotate')
    }
  }, [])

  const pick = async (d) => {
    setStatus('loading')
    try {
      setDate(d)
      setDay(await loadDay(d))
      setStatus('ready')
    } catch (e) {
      setErr(e.message || '載入失敗'); setStatus('error')
    }
  }

  const [chartTarget, setChartTarget] = useState(() => {
    if (typeof window === 'undefined') return null
    const s = window.location.search
    if (s.includes('demochartus')) return { name: '費城半導體', type: 'index' }
    if (s.includes('demochart')) return { name: '台積電', code: '2330', type: 'stock' }
    return null
  })
  const openChart = (target) => setChartTarget(target)

  if (status === 'loading' && !day) {
    return <div className="wrap"><div className="center-state"><div><div className="spin" />載入今日戰報中…</div></div></div>
  }
  if (status === 'error') {
    return (
      <div className="wrap"><div className="center-state">
        <div>
          <div className="icon-lg"><AlertTriangle size={32} strokeWidth={1.75} /></div>
          <div style={{ fontSize: 16, color: 'var(--ink)', fontWeight: 700 }}>資料載入失敗</div>
          <div style={{ marginTop: 8 }}>{err}</div>
          <button className="retry" onClick={boot}>重試</button>
        </div>
      </div></div>
    )
  }

  const ov = day.overview

  return (
    <div className="wrap">
      <Hero day={day} dates={dates} date={date} onSelect={pick} />

      <DataHealth warnings={day._warnings} />

      <RegimeTile regime={day.regime} />

      <div className="tabbar" data-region="台股 / 美股 分頁">
        <button className={'tab' + (tab === 'tw' ? ' active' : '')} onClick={() => switchTab('tw')}>台股</button>
        <button className={'tab' + (tab === 'us' ? ' active' : '')} onClick={() => switchTab('us')}>美股</button>
      </div>

      {tab === 'tw' ? (
        <div className="pane" key="tw">
          <div className="grid">
            <OverviewTW tw={ov.tw} onOpen={openChart} />
            <Vix vix={ov.vix.tw} label="台股情緒" />
            <Sectors sectors={day.sectors.tw} title="類股漲跌幅" meta="各產業類指數"
              inLabel="▲ 強勢類股 Top 5" outLabel="▼ 弱勢類股 Top 5" />
            <HotStocks stocks={day.hot_stocks.tw} onOpen={openChart} />
            <WarRoom potential={day.potential} date={date} onOpen={openChart} />
            <InstTop instTop={day.inst_top} flow={day.inst_flow} concentration={day.buy_concentration} onOpen={openChart} />
            <Radar radar={day.radar} potential={day.potential} volumeAnomalies={day.volume_anomalies} dates={dates} date={date} onOpen={openChart} />
          </div>
        </div>
      ) : (
        <div className="pane" key="us">
          <div className="grid">
            <OverviewUS us={ov.us} onOpen={openChart} />
            <Vix vix={ov.vix.us} label="美股情緒" />
            <Sectors sectors={day.sectors.us} title="類股漲跌幅" meta="11 大類股 ETF"
              inLabel="▲ 強勢類股 Top 5" outLabel="▼ 弱勢類股 Top 5" />
            <div className="col-span-2"><HotStocks stocks={day.hot_stocks.us} onOpen={openChart} /></div>
          </div>
        </div>
      )}

      <div className="section-head" data-region="跨市場戰略">
        <span className="badge-pill"><Globe2 size={14} strokeWidth={1.75} />Cross-Market</span>
        <h2>跨市場戰略</h2>
      </div>
      <div className="grid">
        <MarketLinks markets={day.markets} />
        <News news={day.news} />
        <UpcomingEvents events={day.upcoming_events} earnings={day.earnings_tomorrow} />
        <PastReview events={day.past_events_review} />
        <Verdict verdict={day.verdict} tab={tab} accuracy={accuracy} />
      </div>

      <footer>
        <div className="foot-main">
          ※ 數據為每日 18:36 自動更新並 Telegram 推送 · 軟情報每條附來源連結<br />
          {day.summary}
        </div>
        <div className="ai-disclaimer">本內容由 AI 自動彙整生成，僅供研究參考，不構成投資建議</div>
      </footer>

      <ChartModal target={chartTarget} onClose={() => setChartTarget(null)} />
    </div>
  )
}
