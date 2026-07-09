import { Link2 } from 'lucide-react'
import { dirClass } from '../lib/format.js'

// 市場連動指標：美元/台幣、美10年債、黃金、原油、比特幣
function fmtVal(m) {
  const dec = typeof m.dec === 'number' ? m.dec : 2
  const raw = Number(m.value)
  if (!Number.isFinite(raw)) return '—'
  const num = raw.toLocaleString('en-US', { maximumFractionDigits: dec, minimumFractionDigits: m.unit === '%' ? dec : 0 })
  if (m.unit === '$') return '$' + num
  if (m.unit === '%') return num + '%'
  return num
}

export default function MarketLinks({ markets }) {
  if (!markets || markets.length === 0) return null
  return (
    <section className="card col-span-2" data-region="⑨ 市場連動指標">
      <div className="card-h">
        <span className="badge-pill label"><Link2 size={14} strokeWidth={1.75} />市場連動指標</span>
        <span className="meta">匯率 / 公債 / 商品 / 加密</span>
      </div>
      <div className="mktgrid">
        {markets.map((m, i) => {
          const d = dirClass(m.change_pct)
          return (
            <div className="tile" key={i} style={{ cursor: 'default' }}>
              <div className="t">{m.name}</div>
              <div className="v mono">{fmtVal(m)}</div>
              <div className={'c mono ' + d}>{Number.isFinite(m.change_pct) ? `${m.change_pct >= 0 ? '+' : ''}${m.change_pct}%` : '—'}</div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
