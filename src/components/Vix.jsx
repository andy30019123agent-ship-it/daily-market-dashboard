// 市場情緒 VIX：大數字 + 恐慌→貪婪色階刻度
export default function Vix({ vix, label }) {
  const d = vix.change <= 0 ? 'down' : 'up'
  const pos = Math.max(0, Math.min(1, vix.gauge ?? 0.5)) * 100
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
        <div className="gauge" />
        <div className="gauge-mark"><i style={{ left: `${pos}%` }} /></div>
        <div className="gauge-scale"><span>恐慌</span><span>中性</span><span>貪婪</span></div>
      </div>
    </section>
  )
}
