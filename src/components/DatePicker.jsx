import { useState, useEffect, useRef } from 'react'
import { dateWithWeekday } from '../lib/format.js'

const WD = ['日', '一', '二', '三', '四', '五', '六']

// 月曆 popover：有報告的日子可點、選中高亮、今天標記、其餘灰
export default function DatePicker({ dates, selected, onSelect }) {
  const [open, setOpen] = useState(false)
  const [view, setView] = useState(() => selected || dates[0] || '')
  const ref = useRef(null)

  useEffect(() => {
    const onDoc = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  const has = new Set(dates)
  const [vy, vm] = (view || selected || '2026-01').split('-').map(Number)
  const first = new Date(Date.UTC(vy, vm - 1, 1)).getUTCDay()
  const dim = new Date(Date.UTC(vy, vm, 0)).getUTCDate()
  const todayIso = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Taipei' })

  const cells = []
  for (let i = 0; i < first; i++) cells.push(null)
  for (let d = 1; d <= dim; d++) cells.push(d)

  const iso = (d) => `${vy}-${String(vm).padStart(2, '0')}-${String(d).padStart(2, '0')}`
  const shiftMonth = (delta) => {
    const dt = new Date(Date.UTC(vy, vm - 1 + delta, 1))
    setView(`${dt.getUTCFullYear()}-${String(dt.getUTCMonth() + 1).padStart(2, '0')}-01`)
  }

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button className="datebtn" onClick={() => setOpen((o) => !o)}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M3 9h18M8 2v4M16 2v4" /></svg>
        {dateWithWeekday(selected)}
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#76829A" strokeWidth="2.5"><path d="M6 9l6 6 6-6" /></svg>
      </button>
      {open && (
        <div className="calpop">
          <div className="calhead">
            <button onClick={() => shiftMonth(-1)}>‹</button>
            <div className="m">{vy} 年 {vm} 月</div>
            <button onClick={() => shiftMonth(1)}>›</button>
          </div>
          <div className="calgrid">
            {WD.map((w) => <div className="w" key={w}>{w}</div>)}
            {cells.map((d, i) => {
              if (d == null) return <div className="calday" key={i} />
              const dayIso = iso(d)
              let cls = 'calday'
              if (has.has(dayIso)) cls += ' has'
              else cls += ' muted'
              if (dayIso === selected) cls += ' sel'
              if (dayIso === todayIso) cls += ' today'
              return (
                <div className={cls} key={i}
                  onClick={() => { if (has.has(dayIso)) { onSelect(dayIso); setOpen(false) } }}>
                  {d}
                </div>
              )
            })}
          </div>
          <div className="callegend"><i /> 有報告可點 · 灰色為休市 / 未來</div>
        </div>
      )}
    </div>
  )
}
