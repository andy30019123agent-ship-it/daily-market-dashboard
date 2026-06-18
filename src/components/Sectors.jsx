function Col({ title, rows, side }) {
  return (
    <div className={'flowcol ' + side}>
      <h3>{side === 'in' ? '▲ 資金流入 Top 5' : '▼ 資金流出 Top 5'}</h3>
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

export default function Sectors({ sectors, meta }) {
  return (
    <section className="card col-7" data-region="③ 板塊資金流向">
      <div className="card-h"><span className="label">板塊資金流向</span><span className="meta">{meta}</span></div>
      <div className="flow2">
        <Col rows={sectors.in} side="in" />
        <Col rows={sectors.out} side="out" />
      </div>
    </section>
  )
}
