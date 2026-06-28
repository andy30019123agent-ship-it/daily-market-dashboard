import { useMemo, useState } from 'react'
import { createPortal } from 'react-dom'

// 象限分類（X=漲跌幅 pct、Y=法人淨買超 inst_net_yi）
// 左上 pct<0,inst>0 = 逆勢吸籌(準備發動) | 右上 = 同步買進 | 右下 = 漲高出貨 | 左下 = 賣壓失血
function quadKey(d) {
  if (d.inst_net_yi > 0) return d.pct < 0 ? 'acc' : 'up'   // 買超：跌=吸籌 / 漲=已動
  return d.pct > 0 ? 'dist' : 'weak'                       // 賣超：漲=出貨 / 跌=失血
}

// 四象限定義（買方由大到小、賣方由大到小）
const QUADS = [
  { key: 'acc',  emoji: '🟢', name: '逆勢吸籌', hint: '法人買、股價還沒漲（準備發動）', buy: true },
  { key: 'up',   emoji: '🟡', name: '同步買進', hint: '法人買、股價同步上漲',          buy: true },
  { key: 'dist', emoji: '🔴', name: '漲高出貨', hint: '法人賣、股價卻漲（出貨嫌疑）',   buy: false },
  { key: 'weak', emoji: '⚪', name: '賣壓失血', hint: '法人賣、股價也跌',              buy: false },
]

function Scatter({ items, onItem, activeQuad }) {
  const W = 320, H = 210, PAD = 26
  const maxX = Math.max(5, ...items.map((d) => Math.abs(d.pct)))
  const maxY = Math.max(1, ...items.map((d) => Math.abs(d.inst_net_yi)))
  const cx = PAD + (W - 2 * PAD) / 2
  const cy = PAD + (H - 2 * PAD) / 2
  const px = (v) => cx + (Math.max(-maxX, Math.min(maxX, v)) / maxX) * ((W - 2 * PAD) / 2)
  const py = (v) => cy - (Math.max(-maxY, Math.min(maxY, v)) / maxY) * ((H - 2 * PAD) / 2)
  const maxVal = Math.max(1, ...items.map((d) => d.value_yi || 1))
  return (
    <svg className="radar-svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="資金流象限圖">
      {/* 象限底色（選中的那象限加亮）*/}
      <rect x={PAD} y={PAD} width={cx - PAD} height={cy - PAD} className={'qbg q-acc' + (activeQuad === 'acc' ? ' on' : '')} />
      <rect x={cx} y={PAD} width={W - PAD - cx} height={cy - PAD} className={'qbg q-up' + (activeQuad === 'up' ? ' on' : '')} />
      <rect x={cx} y={cy} width={W - PAD - cx} height={H - PAD - cy} className={'qbg q-dist' + (activeQuad === 'dist' ? ' on' : '')} />
      <rect x={PAD} y={cy} width={cx - PAD} height={H - PAD - cy} className={'qbg q-weak' + (activeQuad === 'weak' ? ' on' : '')} />
      {/* 0 軸 */}
      <line x1={cx} y1={PAD} x2={cx} y2={H - PAD} className="radar-axis" />
      <line x1={PAD} y1={cy} x2={W - PAD} y2={cy} className="radar-axis" />
      {/* 象限標籤 */}
      <text x={PAD + 4} y={PAD + 12} className="qlbl acc">🟢 逆勢吸籌</text>
      <text x={W - PAD - 4} y={PAD + 12} className="qlbl up" textAnchor="end">🟡 同步買進</text>
      <text x={W - PAD - 4} y={H - PAD - 5} className="qlbl dist" textAnchor="end">🔴 漲高出貨</text>
      <text x={PAD + 4} y={H - PAD - 5} className="qlbl weak">⚪ 賣壓失血</text>
      {/* 軸名 */}
      <text x={W - PAD} y={cy - 4} className="qaxname" textAnchor="end">漲→</text>
      <text x={cx + 4} y={PAD - 6} className="qaxname">法人買超↑</text>
      {/* 點（非選中象限淡化）*/}
      {items.map((d, i) => {
        const r = 3 + 4 * Math.sqrt((d.value_yi || 1) / maxVal)
        const k = quadKey(d)
        const dim = activeQuad && k !== activeQuad
        return (
          <circle
            key={i} cx={px(d.pct)} cy={py(d.inst_net_yi)} r={r}
            className={'radar-dot q-' + k + (onItem ? ' clk' : '') + (dim ? ' dim' : '')}
            onClick={onItem ? () => onItem(d) : undefined}
          >
            <title>{d.name} {d.code || ''}　漲跌 {d.pct}%　法人 {d.inst_net_yi >= 0 ? '+' : ''}{d.inst_net_yi}億</title>
          </circle>
        )
      })}
    </svg>
  )
}

function RankRow({ d, onItem }) {
  return (
    <div className={'rk-row' + (onItem ? ' clk' : '')}
         onClick={onItem ? () => onItem(d) : undefined}>
      <span className="rk-nm">{d.name}{d.code && <span className="rk-code">{d.code}</span>}</span>
      <span className="rk-vals mono">
        <span className={d.inst_net_yi >= 0 ? 'up' : 'down'}>{d.inst_net_yi >= 0 ? '+' : ''}{d.inst_net_yi}億</span>
        <span className={'rk-pct ' + (d.pct >= 0 ? 'up' : 'down')}>{d.pct >= 0 ? '+' : ''}{d.pct}%</span>
      </span>
    </div>
  )
}

// 點類股 → 列出該類股個股，依法人淨買超（吸籌）由高到低
function SectorStocksModal({ sector, stocks, onClose, onOpen }) {
  if (!sector) return null
  const list = (stocks || []).filter((s) => s.sector === sector)
    .sort((a, b) => b.inst_net_yi - a.inst_net_yi)
  // 用 portal 渲染到 body，避開卡片 backdrop-filter 造成的 fixed 定位錯位
  return createPortal((
    <div className="modal-back" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <span className="modal-title">{sector}<span className="modal-sub">個股 · 依法人淨買超排序 · 共 {list.length} 檔</span></span>
          <button className="modal-x" onClick={onClose} aria-label="關閉">✕</button>
        </div>
        {list.length ? (
          <div className="modal-list">
            {list.map((s, i) => (
              <div className="modal-row clk" key={i} onClick={() => onOpen({ code: s.code, name: s.name })}>
                <span className="mr-nm">{s.name}<span className="mr-code">{s.code}</span></span>
                <span className="rk-vals mono">
                  <span className={s.inst_net_yi >= 0 ? 'up' : 'down'}>{s.inst_net_yi >= 0 ? '+' : ''}{s.inst_net_yi}億</span>
                  <span className={'rk-pct ' + (s.pct >= 0 ? 'up' : 'down')}>{s.pct >= 0 ? '+' : ''}{s.pct}%</span>
                </span>
              </div>
            ))}
          </div>
        ) : <div className="modal-empty">查無個股資料</div>}
        <div className="modal-foot">🟢 吸籌（法人淨買超為正）在上、🔴 撤離在下 · 點個股看 K 線</div>
      </div>
    </div>
  ), document.body)
}

export default function Radar({ radar, onOpen }) {
  const [level, setLevel] = useState('sectors') // sectors | stocks
  const [quad, setQuad] = useState('acc')        // 選中的象限
  const [secSel, setSecSel] = useState(null)     // 下鑽中的類股名

  const data = useMemo(() => {
    if (!radar) return null
    const sectors = radar.sectors || []
    // 個股濾流動性（成交值≥2億）避免雞蛋水餃雜訊
    const stocks = (radar.stocks || []).filter((s) => (s.value_yi || 0) >= 2)
    const pick = level === 'sectors' ? sectors : stocks
    const counts = { acc: 0, up: 0, dist: 0, weak: 0 }
    pick.forEach((d) => { counts[quadKey(d)]++ })
    return { pick, counts }
  }, [radar, level])

  if (!radar || !data) {
    return (
      <section className="card col-12" data-region="⑨ 資金流雷達">
        <div className="card-h"><span className="label">🛰️ 資金流雷達</span></div>
        <div className="rk-empty" style={{ padding: '18px 0' }}>今日無資金流資料</div>
      </section>
    )
  }

  // 類股模式：點擊下鑽看成分個股；個股模式：點擊看 K 線
  const onItem = level === 'sectors'
    ? (d) => setSecSel(d.name)
    : (d) => onOpen({ code: d.code, name: d.name })
  const cur = QUADS.find((q) => q.key === quad)
  const list = data.pick.filter((d) => quadKey(d) === quad)
    .sort((a, b) => cur.buy ? b.inst_net_yi - a.inst_net_yi : a.inst_net_yi - b.inst_net_yi)
  const unit = level === 'sectors' ? '類股' : '個股'

  return (
    <section className="card col-12" data-region="⑨ 資金流雷達">
      <div className="card-h">
        <span className="label">🛰️ 資金流雷達<span className="meta"> · 法人買超 × 漲幅</span></span>
        <div className="seg">
          <button className={'seg-btn' + (level === 'sectors' ? ' on' : '')} onClick={() => setLevel('sectors')}>類股</button>
          <button className={'seg-btn' + (level === 'stocks' ? ' on' : '')} onClick={() => setLevel('stocks')}>個股</button>
        </div>
      </div>
      <div className="radar-wrap">
        <Scatter items={data.pick} onItem={onItem} activeQuad={quad} />
        <div className="rk-one">
          {/* 象限選擇器 */}
          <div className="quad-sel">
            {QUADS.map((q) => (
              <button key={q.key} className={'quad-chip ' + q.key + (quad === q.key ? ' on' : '')} onClick={() => setQuad(q.key)}>
                <span className="qc-name">{q.emoji} {q.name}</span>
                <span className="qc-cnt">{data.counts[q.key]}</span>
              </button>
            ))}
          </div>
          <div className="quad-hint">{cur.hint}　·　依法人淨買超排序</div>
          <div className="quad-list">
            {list.length ? list.map((d, i) => <RankRow key={i} d={d} onItem={onItem} />)
              : <div className="rk-empty">此象限目前無{unit}</div>}
          </div>
        </div>
      </div>
      <div className="radar-foot">🔮 資金面早期跡象、屬推測，非保證會漲跌；法人淨買超＝三大法人合計 × 收盤價。{level === 'sectors' ? '點類股看成分個股。' : '點個股看 K 線。'}</div>
      <SectorStocksModal sector={secSel} stocks={radar.stocks} onClose={() => setSecSel(null)} onOpen={onOpen} />
    </section>
  )
}
