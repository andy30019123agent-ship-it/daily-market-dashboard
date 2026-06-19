// 市場情緒 VIX：大數字 + 恐慌→貪婪色階刻度
export default function Vix({ vix, label }) {
  const d = vix.change <= 0 ? 'down' : 'up'
  const g = Math.max(0, Math.min(1, vix.gauge ?? 0.5))
  const pos = g * 100
  // 情緒位置（gauge 0=恐慌、1=貪婪）；VIX 越高→越恐慌
  const zone = g <= 0.33 ? { t: '偏恐慌', c: 'down' } : g <= 0.66 ? { t: '中性', c: 'gold' } : { t: '偏貪婪', c: 'up' }
  return (
    <section className="card col-4" data-region="② 市場情緒 VIX">
      <div className="card-h"><span className="label">{label} · VIX</span></div>
      <div className="vixbox">
        <div className="vix-top">
          <span className="vix-num mono">{vix.value}</span>
          <span className="vix-unit">{label.includes('台') ? '台指 VIX' : 'CBOE VIX'}</span>
        </div>
        <div className={'vix-state mono ' + d}>
          {vix.change <= 0 ? '▼' : '▲'} {Math.abs(vix.change)}　{vix.state}
        </div>
        <div className="vix-sub">{vix.note}</div>
        <div className="gauge-now">情緒位置：<b className={zone.c}>{zone.t}</b><span className="gauge-hint">（VIX 越高越恐慌）</span></div>
        <div className="gauge" />
        <div className="gauge-mark"><i style={{ left: `${pos}%` }} /></div>
        <div className="gauge-scale"><span>恐慌</span><span>中性</span><span>貪婪</span></div>
      </div>
    </section>
  )
}
