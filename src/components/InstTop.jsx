import { useState } from 'react'
import { Building2 } from 'lucide-react'
import { activate } from '../lib/format.js'

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

const FLOW_ORDER = ['外資', '投信', '自營']

// 三大法人「連續買賣超天數」摘要：買=紅、賣=綠（與全站紅漲綠跌一致），只顯示連 2 天以上
function FlowStrip({ flow }) {
  if (!flow) return null
  const chips = FLOW_ORDER
    .map((k) => [k, flow[k]])
    .filter(([, v]) => v && v.side && v.streak >= 2)
  if (!chips.length) return null
  return (
    <div className="inst-flow">
      {chips.map(([k, v]) => (
        <span key={k} className={'ifchip ' + (v.side === 'buy' ? 'up' : 'down')}>
          {k} 連 {v.streak} {v.side === 'buy' ? '買' : '賣'}
        </span>
      ))}
      <span className="inst-flow-note">連續同向天數</span>
    </div>
  )
}

// 買超集中度：前 N 大買超個股佔全市場法人買超金額比重（高＝少數權值撐盤、低＝廣泛買盤）
function Concentration({ c }) {
  if (!c || !Number.isFinite(c.ratio)) return null
  const tone = c.ratio >= 60 ? '集中在少數權值股' : c.ratio <= 35 ? '買盤相當廣泛' : '買盤分布中等'
  return (
    <div className="conc">
      <span className="conc-k">買超集中度</span>
      <span className="conc-v mono">{c.ratio}%</span>
      <span className="conc-note">前 {c.n} 大個股佔全市場法人買超金額 · {tone}</span>
    </div>
  )
}

export default function InstTop({ instTop, flow, concentration, onOpen }) {
  const [side, setSide] = useState('buy')
  if (!instTop) return null
  const hasAny = GROUPS.some((g) => {
    const s = sides(instTop[g.key]); return s.buy.length || s.sell.length
  })
  if (!hasAny) return null

  const tone = side === 'buy' ? 'up' : 'down'

  return (
    <section className="card col-span-2" data-region="法人買賣超 Top5">
      <div className="card-h">
        <span className="badge-pill label"><Building2 size={14} strokeWidth={1.75} />三大法人個股 {side === 'buy' ? '買超' : '賣超'} Top 5</span>
        <div className="seg">
          <button className={'seg-btn' + (side === 'buy' ? ' on up' : '')} onClick={() => setSide('buy')}>買超</button>
          <button className={'seg-btn' + (side === 'sell' ? ' on down' : '')} onClick={() => setSide('sell')}>賣超</button>
        </div>
      </div>
      <FlowStrip flow={flow} />
      <Concentration c={concentration} />
      <div className="inst3">
        {GROUPS.map((g) => {
          const rows = sides(instTop[g.key])[side]
          return (
            <div className="instcol" key={g.key}>
              <h3>{g.label}</h3>
              {rows.length ? rows.map((s, i) => (
                <div className="instrow" key={i} {...activate(() => onOpen?.({ name: s.name, code: s.code, type: 'stock' }), `${s.name} ${s.code} 看 K 線`)}>
                  <span className="nm">{s.name}<span className="code">{s.code}</span></span>
                  <span className={'zh mono ' + tone}>{Number.isFinite(Number(s.zhang)) ? Number(s.zhang).toLocaleString('en-US') : '—'}</span>
                </div>
              )) : <div className="inst-empty">—</div>}
            </div>
          )
        })}
      </div>
    </section>
  )
}
