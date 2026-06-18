import { fmtNum, pctText } from '../lib/format.js'

// 從當日資料組出跑馬燈項目（台美關鍵指數 + VIX）
function buildItems(day) {
  const items = []
  const tw = day?.overview?.tw
  if (tw?.featured) items.push({ n: '加權', p: fmtNum(tw.featured.close), pct: tw.featured.change_pct })
  for (const s of tw?.stats || []) {
    if (typeof s.change_pct === 'number') items.push({ n: s.name.replace(/\s.*/, ''), p: s.value, pct: s.change_pct })
  }
  for (const u of day?.overview?.us || []) items.push({ n: u.name, p: fmtNum(u.close), pct: u.change_pct })
  const vus = day?.overview?.vix?.us
  if (vus) items.push({ n: 'VIX', p: vus.value, pct: vus.change })
  return items
}

function Row({ items }) {
  return (
    <div className="track" aria-hidden="true">
      {items.map((it, i) => (
        <span className="tk" key={i}>
          <span className="n">{it.n}</span>
          <span className="p mono">{it.p}</span>
          <span className={'c mono ' + (it.pct >= 0 ? 'up' : 'down')}>
            {it.pct >= 0 ? '+' : ''}{typeof it.pct === 'number' ? it.pct.toFixed(2) : it.pct}%
          </span>
        </span>
      ))}
    </div>
  )
}

export default function Ticker({ day }) {
  const items = buildItems(day)
  if (!items.length) return null
  return (
    <div className="ticker" data-region="跑馬燈行情帶">
      <div className="tracks">
        <Row items={items} />
        <Row items={items} />
      </div>
    </div>
  )
}
