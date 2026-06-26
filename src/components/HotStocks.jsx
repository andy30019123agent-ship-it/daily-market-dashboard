import { dirClass } from '../lib/format.js'

function Row({ s, onOpen }) {
  const d = dirClass(s.change_pct)
  return (
    <div className="hotrow" onClick={() => onOpen?.({ name: s.name, code: s.code, type: 'stock' })}>
      <span className="nm">{s.name}<span className="code">{s.code}</span></span>
      <span className="rt">
        <span className={'pct ' + d}>{s.change_pct >= 0 ? '+' : ''}{s.change_pct}%</span>
        {s.reason ? <span className="rs">{s.reason}</span> : null}
      </span>
    </div>
  )
}

export default function HotStocks({ stocks, onOpen }) {
  const listed = (stocks || []).filter((s) => s.mkt === '上市')
  const otc = (stocks || []).filter((s) => s.mkt === '上櫃')
  const grouped = listed.length > 0 && otc.length > 0
  return (
    <section className="card col-5" data-region="④ 熱門個股">
      <div className="card-h"><span className="label">熱門個股</span><span className="meta">漲幅 Top</span></div>
      <div className="hot">
        {grouped ? (
          <>
            <h3 className="hot-grp">上市 Top {listed.length}</h3>
            {listed.map((s, i) => <Row key={'l' + i} s={s} onOpen={onOpen} />)}
            <h3 className="hot-grp" style={{ marginTop: 16 }}>上櫃 Top {otc.length}</h3>
            {otc.map((s, i) => <Row key={'o' + i} s={s} onOpen={onOpen} />)}
          </>
        ) : (
          (stocks || []).map((s, i) => <Row key={i} s={s} onOpen={onOpen} />)
        )}
      </div>
    </section>
  )
}
