import { useState, useEffect, useCallback } from 'react'
import { loadIndex, loadDay } from './lib/loadDay.js'
import Ticker from './components/Ticker.jsx'
import { OverviewTW, OverviewUS } from './components/Overview.jsx'
import Vix from './components/Vix.jsx'
import Sectors from './components/Sectors.jsx'
import HotStocks from './components/HotStocks.jsx'
import InstTop from './components/InstTop.jsx'
import { News, UpcomingEvents, PastReview, Verdict } from './components/CrossMarket.jsx'
import DatePicker from './components/DatePicker.jsx'

export default function App() {
  const [dates, setDates] = useState([])
  const [date, setDate] = useState(null)
  const [day, setDay] = useState(null)
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

  // K 線 modal 之後 Task 接上；先佔位
  const openChart = (target) => {
    console.log('open chart', target)
  }

  if (status === 'loading' && !day) {
    return <div className="wrap"><div className="center-state"><div><div className="spin" />載入今日戰報中…</div></div></div>
  }
  if (status === 'error') {
    return (
      <div className="wrap"><div className="center-state">
        <div>
          <div style={{ fontSize: 15, color: 'var(--ink)' }}>⚠️ 資料載入失敗</div>
          <div style={{ marginTop: 8 }}>{err}</div>
          <button className="retry" onClick={boot}>重試</button>
        </div>
      </div></div>
    )
  }

  const ov = day.overview

  return (
    <div className="wrap">
      <header className="masthead" data-region="標題列 / 日期選單">
        <div>
          <div className="eyebrow">Market Briefing · 盤後戰報</div>
          <h1>每日台美股<b>戰略</b>儀表板</h1>
          <div className="subtitle">收盤後由 AI 分身彙整 · 一頁掌握台美兩地戰況</div>
        </div>
        <div className="head-right">
          <span className="status"><span className="live" />更新於 {day.updated_at}</span>
          <DatePicker dates={dates} selected={date} onSelect={pick} />
        </div>
      </header>
      <div className="hairline" />

      <Ticker day={day} />

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
            <InstTop instTop={day.inst_top} onOpen={openChart} />
          </div>
        </div>
      ) : (
        <div className="pane" key="us">
          <div className="grid">
            <OverviewUS us={ov.us} onOpen={openChart} />
            <Vix vix={ov.vix.us} label="美股情緒" />
            <Sectors sectors={day.sectors.us} title="類股漲跌幅" meta="11 大類股 ETF"
              inLabel="▲ 強勢類股 Top 5" outLabel="▼ 弱勢類股 Top 5" />
            <HotStocks stocks={day.hot_stocks.us} onOpen={openChart} />
          </div>
        </div>
      )}

      <div className="divider"><span className="tx">跨市場戰略 · Cross-Market</span></div>
      <div className="grid">
        <News news={day.news} />
        <UpcomingEvents events={day.upcoming_events} />
        <PastReview events={day.past_events_review} />
        <Verdict verdict={day.verdict} tab={tab} />
      </div>

      <footer>
        ※ 數據為每日 18:43 自動更新並 Telegram 推送 · 軟情報每條附來源連結<br />
        {day.summary}
      </footer>
    </div>
  )
}
