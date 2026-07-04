import { useEffect, useState } from 'react'
import { Target, Eye, Rocket, Archive } from 'lucide-react'
import { loadPotentialHistory } from '../lib/loadDay.js'
import { groupWarRoom } from '../lib/warroom.js'

// 潛力股作戰室：把追蹤中的股分成 觀察中／發動中／已淘汰 三組。
export default function WarRoom({ potential, date, onOpen }) {
  const [history, setHistory] = useState(null)
  useEffect(() => {
    let ok = true
    loadPotentialHistory().then((h) => { if (ok) setHistory(h) }).catch(() => {})
    return () => { ok = false }
  }, [])

  const today = potential?.stocks || []
  const { watching, launched, dropped } = groupWarRoom(history, today, date)
  if (!watching.length && !launched.length && !dropped.length) return null

  const Group = ({ icon: Icon, title, items, tag }) => items.length ? (
    <div className="wr-group">
      <div className="wr-title"><Icon size={14} strokeWidth={1.75} />{title}</div>
      <div className="wr-rows">
        {items.map((s) => (
          <button key={s.code} className="wr-row" onClick={() => onOpen && onOpen({ code: s.code, name: s.name })}>
            <span className="wr-nm">{s.name}<span className="wr-code">{s.code}</span></span>
            <span className="wr-meta">{tag(s)}</span>
          </button>
        ))}
      </div>
    </div>
  ) : null

  return (
    <section className="card" data-region="⑩ 潛力股作戰室">
      <div className="card-h"><span className="badge-pill label"><Target size={14} strokeWidth={1.75} />潛力股作戰室</span></div>
      <Group icon={Eye} title="觀察中" items={watching} tag={(s) => `在榜 ${s.streak ?? 1} 天 · ${s.score ?? '—'} 分`} />
      <Group icon={Rocket} title="發動中" items={launched} tag={() => '近日發動'} />
      <Group icon={Archive} title="已淘汰" items={dropped} tag={() => '已掉出榜'} />
      <div className="wr-note">跡象非保證，研究起點</div>
    </section>
  )
}
