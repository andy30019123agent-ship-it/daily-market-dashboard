import { Newspaper } from 'lucide-react'
import { fmtNum } from '../lib/format.js'
import DatePicker from './DatePicker.jsx'

// 從當日資料組出大數字統計列（台美關鍵指數 + VIX），取代原本的跑馬燈
function buildStats(day) {
  const items = []
  const tw = day?.overview?.tw
  if (tw?.featured) items.push({ n: '加權', p: fmtNum(tw.featured.close), pct: tw.featured.change_pct })
  for (const s of tw?.stats || []) {
    if (typeof s.change_pct === 'number') items.push({ n: s.name.replace(/\s.*/, ''), p: s.value, pct: s.change_pct })
  }
  for (const u of day?.overview?.us || []) items.push({ n: u.name, p: fmtNum(u.close), pct: u.change_pct })
  const vus = day?.overview?.vix?.us
  // 美股 VIX 的 change 由 _yahoo_quote 產生，實為「當日漲跌百分比」（非點數），故直接當 % 顯示才正確
  if (vus) items.push({ n: 'VIX', p: vus.value, pct: vus.change })
  return items
}

export default function Hero({ day, dates, date, onSelect }) {
  const stats = buildStats(day)
  return (
    <section className="hero" data-region="Hero / 標題與大數字統計">
      <span className="hero-blob b1" aria-hidden="true" />
      <span className="hero-blob b2" aria-hidden="true" />
      <span className="hero-blob b3" aria-hidden="true" />
      <div className="hero-top">
        <div className="hero-titles">
          <span className="badge-pill"><Newspaper size={14} strokeWidth={1.75} />盤後戰報 · Market Briefing</span>
          <h1 style={{ marginTop: 14 }}>每日台美股戰略儀表板</h1>
          <div className="subtitle">收盤後由 AI 分身彙整 · 一頁掌握台美兩地戰況</div>
        </div>
        <div className="hero-right">
          <span className="updated-pill"><span className="live-dot" />更新於 {day.updated_at}</span>
          <DatePicker dates={dates} selected={date} onSelect={onSelect} />
        </div>
      </div>
      {stats.length > 0 && (
        <div className="stat-grid">
          {stats.map((it, i) => (
            <div className="stat-tile" key={i}>
              <div className="st-name">{it.n}</div>
              <div className="st-value mono">{it.p}</div>
              <span className={'stat-chip ' + (Number.isFinite(it.pct) ? (it.pct >= 0 ? 'up' : 'down') : 'flat')}>
                {Number.isFinite(it.pct) ? `${it.pct >= 0 ? '+' : ''}${it.pct.toFixed(2)}%` : '—'}
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
