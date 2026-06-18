import { dirClass, pctText } from '../lib/format.js'

export default function HotStocks({ stocks, onOpen }) {
  return (
    <section className="card col-5" data-region="④ 熱門個股">
      <div className="card-h"><span className="label">熱門個股</span><span className="meta">成交 / 漲幅</span></div>
      <div className="hot">
        {stocks.map((s, i) => {
          const d = dirClass(s.change_pct)
          return (
            <div className="hotrow" key={i} onClick={() => onOpen?.({ name: s.name, code: s.code, type: 'stock' })}>
              <span className="nm">{s.name}<span className="code">{s.code}</span></span>
              <span className="rt">
                <span className={'pct ' + d}>{s.change_pct >= 0 ? '+' : ''}{s.change_pct}%</span>
                <span className="rs">{s.reason}</span>
              </span>
            </div>
          )
        })}
      </div>
    </section>
  )
}
