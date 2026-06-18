// 三大法人個股買超 Top 5（台股；單位：張）
const GROUPS = [
  { key: 'foreign', label: '外資' },
  { key: 'trust', label: '投信' },
  { key: 'dealer', label: '自營商' },
]

export default function InstTop({ instTop, onOpen }) {
  if (!instTop) return null
  const hasAny = GROUPS.some((g) => (instTop[g.key] || []).length)
  if (!hasAny) return null

  return (
    <section className="card col-12" data-region="法人買超 Top5">
      <div className="card-h">
        <span className="label">三大法人個股買超 Top 5</span>
        <span className="meta">單位：張</span>
      </div>
      <div className="inst3">
        {GROUPS.map((g) => {
          const rows = instTop[g.key] || []
          return (
            <div className="instcol" key={g.key}>
              <h3>{g.label}</h3>
              {rows.length ? rows.map((s, i) => (
                <div className="instrow" key={i} onClick={() => onOpen?.({ name: s.name, code: s.code, type: 'stock' })}>
                  <span className="nm">{s.name}<span className="code">{s.code}</span></span>
                  <span className="zh mono">{s.zhang.toLocaleString('en-US')}</span>
                </div>
              )) : <div className="inst-empty">—</div>}
            </div>
          )
        })}
      </div>
    </section>
  )
}
