import { useState, useEffect, useLayoutEffect, useRef } from 'react'
import { Calendar, ChevronDown } from 'lucide-react'
import { dateWithWeekday, activate } from '../lib/format.js'

const WD = ['日', '一', '二', '三', '四', '五', '六']
const POP_MARGIN = 12 // popover 與視窗邊緣至少保留的距離

// 月曆 popover：有報告的日子可點、選中高亮、今天標記、其餘灰
export default function DatePicker({ dates, selected, onSelect }) {
  const [open, setOpen] = useState(false)
  const [view, setView] = useState(() => selected || dates[0] || '')
  const [pos, setPos] = useState(null) // popover 的 fixed 定位座標，依按鈕實際位置計算
  const ref = useRef(null)
  const btnRef = useRef(null)
  const popRef = useRef(null)

  useEffect(() => {
    const onDoc = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  // 依按鈕在畫面上的實際位置算 popover 座標（position:fixed），
  // 避免外層 flex-wrap 造成的錨點跳動把月曆裁出畫面外
  useLayoutEffect(() => {
    if (!open) return
    const place = () => {
      const btn = btnRef.current
      if (!btn) return
      const r = btn.getBoundingClientRect()
      const popW = popRef.current?.offsetWidth || 368
      const popH = popRef.current?.offsetHeight || 360
      let left = r.right - popW
      left = Math.min(left, window.innerWidth - popW - POP_MARGIN)
      left = Math.max(left, POP_MARGIN)
      let top = r.bottom + 8
      if (top + popH > window.innerHeight - POP_MARGIN) {
        top = Math.max(POP_MARGIN, r.top - 8 - popH)
      }
      setPos({ top, left })
    }
    place()
    window.addEventListener('resize', place)
    window.addEventListener('scroll', place, true)
    return () => {
      window.removeEventListener('resize', place)
      window.removeEventListener('scroll', place, true)
    }
  }, [open])

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
      <button ref={btnRef} className="datebtn" onClick={() => setOpen((o) => !o)}>
        <Calendar size={16} strokeWidth={1.75} />
        {dateWithWeekday(selected)}
        <ChevronDown size={14} strokeWidth={2} />
      </button>
      {open && (
        <div className="calpop" ref={popRef} style={pos ? { top: pos.top, left: pos.left } : { visibility: 'hidden' }}>
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
              const clickable = has.has(dayIso)
              let cls = 'calday'
              cls += clickable ? ' has' : ' muted'
              if (dayIso === selected) cls += ' sel'
              if (dayIso === todayIso) cls += ' today'
              if (!clickable) return <div className={cls} key={i} aria-disabled="true">{d}</div>
              return (
                <div className={cls} key={i}
                  {...activate(() => { onSelect(dayIso); setOpen(false) }, `查看 ${dateWithWeekday(dayIso)} 戰報`)}>
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
