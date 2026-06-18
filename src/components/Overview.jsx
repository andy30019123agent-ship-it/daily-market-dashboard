import Sparkline from './Sparkline.jsx'
import { fmtNum, dirClass, pctText } from '../lib/format.js'

const ChartIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" strokeWidth="2"><path d="M3 3v18h18" /><path d="M7 14l4-4 3 3 5-6" /></svg>
)

const COL = { up: '#FF4D5E', down: '#16C784' }

// 台股：主指數 hero + 子數據 tile
export function OverviewTW({ tw, onOpen }) {
  const f = tw.featured
  const fd = dirClass(f.change_pct)
  return (
    <section className="card col-8" data-region="① 今日總覽">
      <div className="card-h"><span className="label">台股今日總覽</span><span className="meta">收盤</span></div>
      <div className="hero" onClick={() => onOpen?.({ name: f.name, type: 'index' })}>
        <div className="lead">
          <div className="t">{f.name}</div>
          <div className="v mono">{fmtNum(Math.trunc(f.close))}<small>.{String(f.close.toFixed(2)).split('.')[1]}</small></div>
          <div className={'c mono ' + fd}>
            {pctText(f.change_pct)}{typeof f.change === 'number' ? `　${f.change >= 0 ? '+' : ''}${f.change}` : ''}
            {f.note ? <span className="lbl">　{f.note}</span> : null}
          </div>
        </div>
        <Sparkline points={f.spark || []} color={COL[fd]} />
      </div>
      <div className="tiles">
        {tw.stats.map((s, i) => {
          const d = dirClass(s.change_pct, s.dir)
          return (
            <div className="tile" key={i} onClick={() => onOpen?.({ name: s.name, type: 'index' })}>
              <div className="t">{s.name}</div>
              <div className={'v mono ' + (s.dir ? d : '')}>{s.value}</div>
              <div className={'c mono ' + d}>
                {typeof s.change_pct === 'number' ? pctText(s.change_pct) : (s.note || '')}
              </div>
            </div>
          )
        })}
      </div>
      <div className="taphint"><ChartIcon />點任一指數展開日 K 線圖</div>
    </section>
  )
}

// 美股：四指數 tile
export function OverviewUS({ us, onOpen }) {
  return (
    <section className="card col-8" data-region="① 今日總覽">
      <div className="card-h"><span className="label">美股今日總覽</span><span className="meta">收盤</span></div>
      <div className="idx4">
        {us.map((u, i) => {
          const d = dirClass(u.change_pct)
          return (
            <div className="tile" key={i} onClick={() => onOpen?.({ name: u.name, type: 'index' })}>
              <div className="t">{u.name}</div>
              <div className="v mono">{fmtNum(u.close)}</div>
              <div className={'c mono ' + d}>{pctText(u.change_pct)}</div>
            </div>
          )
        })}
      </div>
      <div className="taphint"><ChartIcon />點任一指數展開日 K 線圖</div>
    </section>
  )
}
