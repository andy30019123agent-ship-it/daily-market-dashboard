import { isGolden, fmtPct } from '../lib/potential.js'

// 低基期潛力視圖：散佈圖（X=股價位置、Y=法人吸籌）+ 候選卡片。
export default function PotentialRadar({ potential, onOpen }) {
  const stocks = potential?.stocks || []
  if (!stocks.length) {
    return (
      <div className="pot-empty">
        今日無低基期吸籌標的。<br />
        <span className="pot-note">（跡象非保證，研究起點）</span>
      </div>
    )
  }
  const maxInst = Math.max(...stocks.map((s) => s.inst_net_yi || 0), 1)
  return (
    <div className="pot-wrap">
      <svg className="pot-scatter" viewBox="0 0 100 60" preserveAspectRatio="none">
        <rect x="0" y="0" width="40" height="30" className="pot-gold" />
        {stocks.map((s) => {
          const x = Math.min(1, Math.max(0, s.price_pos ?? 1)) * 100
          const y = 60 - ((s.inst_net_yi || 0) / maxInst) * 58
          return (
            <circle
              key={s.code}
              cx={x}
              cy={y}
              r="1.6"
              className={isGolden(s) ? 'pot-dot on' : 'pot-dot'}
              onClick={() => onOpen && onOpen(s.code)}
            />
          )
        })}
      </svg>
      <div className="pot-axis"><span>← 低基期</span><span>法人吸籌 ↑</span></div>

      <div className="pot-list">
        {stocks.map((s) => (
          <div key={s.code} className={isGolden(s) ? 'pot-card gold' : 'pot-card'}>
            <div className="pot-head">
              <button className="pot-name" onClick={() => onOpen && onOpen(s.code)}>
                {s.name} <span className="pot-code">{s.code}</span>
              </button>
              {s.theme && <span className="pot-tag">🏷️ {s.theme}</span>}
            </div>
            <div className="pot-metrics">
              <span>位置 {Math.round((s.price_pos ?? 0) * 100)}%</span>
              <span>近半年 {fmtPct(s.chg_6m)}</span>
              <span>法人 {(s.inst_net_yi ?? 0).toFixed(1)} 億</span>
            </div>
            {s.catalyst && <div className="pot-cat">🌱 {s.catalyst}</div>}
          </div>
        ))}
      </div>
      <div className="pot-note">跡象非保證，研究起點</div>
    </div>
  )
}
