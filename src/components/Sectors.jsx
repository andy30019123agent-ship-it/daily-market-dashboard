import { useState } from 'react'
import { createPortal } from 'react-dom'

function Col({ rows, side, label, onPick }) {
  return (
    <div className={'flowcol ' + side}>
      <h3>{label}</h3>
      {rows.map((r, i) => (
        <div className="flowrow flowrow-click" key={i} onClick={() => onPick(r)}>
          <div className="top">
            <span>{r.name}<span className="flow-more">查成分 ›</span></span>
            <span className={'amt ' + (side === 'in' ? 'up' : 'down')}>{r.amount}</span>
          </div>
          <div className="bar"><i style={{ width: `${Math.round((r.weight ?? 0) * 100)}%` }} /></div>
        </div>
      ))}
    </div>
  )
}

function ConstituentModal({ sector, onClose }) {
  if (!sector) return null
  const list = sector.constituents || []
  // 用 portal 渲染到 body，避開卡片 backdrop-filter 造成的 fixed 定位錯位
  return createPortal((
    <div className="modal-back" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <span className="modal-title">{sector.name}<span className="modal-sub">成分股 · {sector.amount}</span></span>
          <button className="modal-x" onClick={onClose} aria-label="關閉">✕</button>
        </div>
        {list.length ? (
          <div className="modal-list">
            {list.map((s, i) => {
              const has = typeof s.change_pct === 'number'
              const dir = has ? (s.change_pct >= 0 ? 'up' : 'down') : ''
              return (
                <div className="modal-row" key={i}>
                  <span className="mr-nm">{s.name}<span className="mr-code">{s.code}</span></span>
                  {has && <span className={'mr-pct mono ' + dir}>{s.change_pct >= 0 ? '+' : ''}{s.change_pct}%</span>}
                </div>
              )
            })}
          </div>
        ) : <div className="modal-empty">查無成分股資料</div>}
        <div className="modal-foot">{list.some(s => typeof s.change_pct === 'number') ? '依成交值排序 · 數字為當日漲跌' : 'ETF 主要成分股'}</div>
      </div>
    </div>
  ), document.body)
}

export default function Sectors({ sectors, title = '板塊資金流向', meta, inLabel = '▲ 資金流入 Top 5', outLabel = '▼ 資金流出 Top 5' }) {
  const [pick, setPick] = useState(typeof window !== 'undefined' && window.location.search.includes('demomodal') ? (sectors.in && sectors.in[0]) : null)
  return (
    <section className="card col-7" data-region="③ 類股 / 資金流向">
      <div className="card-h"><span className="label">{title}</span><span className="meta">{meta}</span></div>
      <div className="flow2">
        <Col rows={sectors.in} side="in" label={inLabel} onPick={setPick} />
        <Col rows={sectors.out} side="out" label={outLabel} onPick={setPick} />
      </div>
      <ConstituentModal sector={pick} onClose={() => setPick(null)} />
    </section>
  )
}
