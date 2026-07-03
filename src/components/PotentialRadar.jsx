import { fmtPct, scoreTier, sparkPath } from '../lib/potential.js'

// 低基期潛力視圖：依「發動信心分數」排序的候選卡片（分數 badge + 一年走勢縮圖）。
export default function PotentialRadar({ potential, onOpen }) {
  const stocks = [...(potential?.stocks || [])].sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
  if (!stocks.length) {
    return (
      <div className="pot-empty">
        今日無低基期吸籌標的。<br />
        <span className="pot-note">（跡象非保證，研究起點）</span>
      </div>
    )
  }
  return (
    <div className="pot-wrap">
      <div className="pot-list">
        {stocks.map((s) => {
          const open = () => onOpen && onOpen({ code: s.code, name: s.name })
          return (
          <div
            key={s.code}
            className={'pot-card clk tier-' + scoreTier(s.score)}
            role="button"
            tabIndex={0}
            title="點看 K 線圖"
            onClick={open}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open() } }}
          >
            <div className="pot-head">
              <span className="pot-name">
                {s.name} <span className="pot-code">{s.code}</span>
              </span>
              <span className={'pot-score tier-' + scoreTier(s.score)}>{s.score ?? '—'} 分</span>
            </div>
            {s.spark && s.spark.length > 1 && (
              <svg className="pot-spark" viewBox="0 0 100 22" preserveAspectRatio="none" aria-label="近一年走勢">
                <polyline points={sparkPath(s.spark, 100, 22)} />
              </svg>
            )}
            <div className="pot-metrics">
              {s.theme && <span className="pot-tag">🏷️ {s.theme}</span>}
              <span>位置 {Math.round((s.price_pos ?? 0) * 100)}%</span>
              <span>近半年 {fmtPct(s.chg_6m)}</span>
              <span>法人 {(s.inst_net_yi ?? 0).toFixed(1)} 億</span>
            </div>
            {s.catalyst && <div className="pot-cat">🌱 {s.catalyst}</div>}
          </div>
          )
        })}
      </div>
      <div className="pot-note">分數＝籌碼＋價量結構＋題材綜合；跡象非保證，研究起點</div>
    </div>
  )
}
