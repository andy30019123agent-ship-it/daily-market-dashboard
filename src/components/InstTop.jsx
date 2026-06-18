// 三大法人個股買超 / 賣超 Top 5（台股；單位：張）
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

function List({ title, rows, tone, onOpen }) {
  return (
    <div className="instlist">
      <div className={'instlabel ' + tone}>{title}</div>
      {rows.length ? rows.map((s, i) => (
        <div className="instrow" key={i} onClick={() => onOpen?.({ name: s.name, code: s.code, type: 'stock' })}>
          <span className="nm">{s.name}<span className="code">{s.code}</span></span>
          <span className={'zh mono ' + tone}>{s.zhang.toLocaleString('en-US')}</span>
        </div>
      )) : <div className="inst-empty">—</div>}
    </div>
  )
}

export default function InstTop({ instTop, onOpen }) {
  if (!instTop) return null
  const hasAny = GROUPS.some((g) => {
    const s = sides(instTop[g.key]); return s.buy.length || s.sell.length
  })
  if (!hasAny) return null

  return (
    <section className="card col-12" data-region="法人買賣超 Top5">
      <div className="card-h">
        <span className="label">三大法人個股買超 / 賣超 Top 5</span>
        <span className="meta">單位：張</span>
      </div>
      <div className="inst3">
        {GROUPS.map((g) => {
          const s = sides(instTop[g.key])
          return (
            <div className="instcol" key={g.key}>
              <h3>{g.label}</h3>
              <List title="▲ 買超" rows={s.buy} tone="up" onOpen={onOpen} />
              <List title="▼ 賣超" rows={s.sell} tone="down" onOpen={onOpen} />
            </div>
          )
        })}
      </div>
    </section>
  )
}
