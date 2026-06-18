function Col({ rows, side, label }) {
  return (
    <div className={'flowcol ' + side}>
      <h3>{label}</h3>
      {rows.map((r, i) => (
        <div className="flowrow" key={i}>
          <div className="top">
            <span>{r.name}</span>
            <span className={'amt ' + (side === 'in' ? 'up' : 'down')}>{r.amount}</span>
          </div>
          <div className="bar"><i style={{ width: `${Math.round((r.weight ?? 0) * 100)}%` }} /></div>
        </div>
      ))}
    </div>
  )
}

export default function Sectors({ sectors, title = '板塊資金流向', meta, inLabel = '▲ 資金流入 Top 5', outLabel = '▼ 資金流出 Top 5' }) {
  return (
    <section className="card col-7" data-region="③ 類股 / 資金流向">
      <div className="card-h"><span className="label">{title}</span><span className="meta">{meta}</span></div>
      <div className="flow2">
        <Col rows={sectors.in} side="in" label={inLabel} />
        <Col rows={sectors.out} side="out" label={outLabel} />
      </div>
    </section>
  )
}
