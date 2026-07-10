import { Tag, Sprout, AlertTriangle } from 'lucide-react'
import { fmtPct, scoreTier, sparkPath } from '../lib/potential.js'

// 潛力股風險提示：用既有欄位標出「值得留意」處，幫使用者別只看分數就追。
// 位階偏高＝已離低基期；法人未同步＝籌碼沒跟上；營收衰退＝基本面轉弱。
function riskFlags(s) {
  const f = []
  if (Number.isFinite(s.price_pos) && s.price_pos >= 0.7) f.push('位階偏高')
  if (Number.isFinite(s.inst_net_yi) && s.inst_net_yi <= 0) f.push('法人未同步')
  if (Number.isFinite(s.fund_yoy) && s.fund_yoy < 0) f.push('營收衰退')
  return f
}

// 題材文字可能夾帶產生器留下的 markdown 連結或裸網址，畫面上只留來源名稱，避免長網址撐爆卡片
const cleanCatalyst = (t) =>
  t
    .replace(/\[([^\]]+)\]\(https?:\/\/[^)]*\)/g, '$1')
    .replace(/https?:\/\/\S+/g, '')
    .replace(/[（(]\s*[)）]/g, '')
    .trim()

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
          const open = () => onOpen && onOpen({ code: s.code, name: s.name, type: 'stock' })
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
              {s.theme && <span className="pot-tag"><Tag size={12} strokeWidth={1.75} />{s.theme}</span>}
              <span>位置 {Number.isFinite(s.price_pos) ? Math.round(s.price_pos * 100) + '%' : '—'}</span>
              <span>近半年 {Number.isFinite(s.chg_6m) ? fmtPct(s.chg_6m) : '—'}</span>
              <span>法人 {Number.isFinite(s.inst_net_yi) ? s.inst_net_yi.toFixed(1) + ' 億' : '—'}</span>
              {typeof s.fund_yoy === 'number' && <span>營收 YoY {fmtPct(s.fund_yoy)}</span>}
              {s.streak != null && <span className="pot-streak">在榜 {s.streak} 天</span>}
            </div>
            {riskFlags(s).length > 0 && (
              <div className="pot-risks">
                <AlertTriangle size={13} strokeWidth={2} />
                {riskFlags(s).map((f, i) => <span className="pot-riskf" key={i}>{f}</span>)}
              </div>
            )}
            {s.catalyst && <div className="pot-cat"><Sprout size={14} strokeWidth={1.75} />{cleanCatalyst(s.catalyst)}</div>}
          </div>
          )
        })}
      </div>
      <div className="pot-note">分數＝籌碼＋價量結構＋題材綜合；跡象非保證，研究起點</div>
    </div>
  )
}
