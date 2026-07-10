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

// 趨勢訊號歷史勝率：用加權收盤回測「站上/跌破 MA20」後 N 日方向命中率
function BacktestNote({ backtest }) {
  const parts = ['5', '20'].map((h) => backtest[h]).filter(Boolean)
  if (!parts.length) return null
  const sampled = parts[0].total
  return (
    <div className="regime-bt">
      <div className="regime-bt-h">趨勢訊號歷史勝率<span className="regime-bt-sub">站上/跌破 MA20 後方向命中</span></div>
      <div className="regime-bt-rows">
        {parts.map((r) => (
          <span className="regime-bt-item" key={r.horizon}>
            <span className="regime-bt-k">{r.horizon} 日</span>
            <b className="mono">{r.rate}%</b>
          </span>
        ))}
        <span className="regime-bt-n">回測 {sampled} 筆</span>
      </div>
    </div>
  )
}

export default function RegimeTile({ regime, backtest }) {
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
          {backtest && <BacktestNote backtest={backtest} />}
        </div>
      )}
      <div className="regime-foot">規則式量化訊號，非個股買賣建議</div>
    </section>
  )
}
