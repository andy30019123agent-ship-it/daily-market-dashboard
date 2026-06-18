import { useState } from 'react'

// 三大法人個股買超 / 賣超 Top 5（台股；單位：張）— 買超/賣超分頁切換
const GROUPS = [
  { key: 'foreign', label: '外資' },
  { key: 'trust', label: '投信' },
  { key: 'dealer', label: '自營商' },
]

// 相容兩種格式：舊 {foreign:[...]} 與新 {foreign:{buy,sell}}
function sides(g) {
  if (!g) return { buy: [], sell: [] }
  return Array.isArray(g) ? { buy: g, sell: [] } : { buy: g.buy || [], sell: g.sell || [] }
}

export default function InstTop({ instTop, onOpen }) {
  const [side, setSide] = useState('buy')
  if (!instTop) return null
  const hasAny = GROUPS.some((g) => {
    const s = sides(instTop[g.key]); return s.buy.length || s.sell.length
  })
  if (!hasAny) return null

  const tone = side === 'buy' ? 'up' : 'down'

  return (
    <section className="card col-12" data-region="法人買賣超 Top5">
      <div className="card-h">
        <span className="label">三大法人個股 {side === 'buy' ? '買超' : '賣超'} Top 5</span>
        <div className="seg">
          <button className={'seg-btn' + (side === 'buy' ? ' on up' : '')} onClick={() => setSide('buy')}>買超</button>
          <button className={'seg-btn' + (side === 'sell' ? ' on down' : '')} onClick={() => setSide('sell')}>賣超</button>
        </div>
      </div>
      <div className="inst3">
        {GROUPS.map((g) => {
          const rows = sides(instTop[g.key])[side]
          return (
            <div className="instcol" key={g.key}>
              <h3>{g.label}</h3>
              {rows.length ? rows.map((s, i) => (
                <div className="instrow" key={i} onClick={() => onOpen?.({ name: s.name, code: s.code, type: 'stock' })}>
                  <span className="nm">{s.name}<span className="code">{s.code}</span></span>
                  <span className={'zh mono ' + tone}>{s.zhang.toLocaleString('en-US')}</span>
                </div>
              )) : <div className="inst-empty">—</div>}
            </div>
          )
        })}
      </div>
    </section>
  )
}
