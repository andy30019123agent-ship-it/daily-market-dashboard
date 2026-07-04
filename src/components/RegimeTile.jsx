import { useState } from 'react'
import { lightMeta, scoreTone, scoreText } from '../lib/regime.js'

// 市場紅綠燈（元件 A）：regime = {light, score, components:{trend,breadth,vix,chips}}
// 舊資料檔沒有 regime 欄 -> 不渲染，不炸。

const ITEMS = [
  { key: 'trend', label: '趨勢', hint: '收盤 vs MA20/MA60' },
  { key: 'breadth', label: '寬度', hint: '上漲家數佔比' },
  { key: 'vix', label: '波動', hint: '台指 VIX' },
  { key: 'chips', label: '籌碼', hint: '三大法人近 5 日' },
]

export default function RegimeTile({ regime }) {
  const [open, setOpen] = useState(false)
  if (!regime || !regime.light) return null
  const meta = lightMeta(regime.light)

  return (
    <section className="card regime-card" data-region="⓪ 市場紅綠燈">
      <button className="regime-main" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <span className={'regime-dot ' + meta.cls} aria-hidden="true" />
        <span className="regime-title">市場紅綠燈</span>
        <span className={'regime-badge ' + meta.cls}>{meta.label}</span>
        <span className="regime-score mono">{regime.score} 分</span>
        <span className="regime-toggle">{open ? '收合分項 ▲' : '分項明細 ▼'}</span>
      </button>
      {open && (
        <div className="regime-detail">
          {ITEMS.map(({ key, label, hint }) => {
            const c = regime.components && regime.components[key]
            return (
              <div className="regime-item" key={key}>
                <div className="k">{label}<span className="hint">{hint}</span></div>
                <div className={'v mono ' + (c && !c.missing ? scoreTone(c.score) : '')}>{scoreText(c)}</div>
              </div>
            )
          })}
        </div>
      )}
      <div className="regime-foot">規則式量化訊號，非個股買賣建議</div>
    </section>
  )
}
