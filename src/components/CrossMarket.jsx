import { monthDay } from '../lib/format.js'

const TAGS = { pos: '利多', neg: '利空', neu: '中性' }

export function News({ news }) {
  return (
    <section className="card col-7" data-region="⑤ 影響股市消息">
      <div className="card-h"><span className="label">川普及影響股市消息</span></div>
      <div className="news">
        {news.map((n, i) => (
          <div className="newsrow" key={i}>
            <span className={'tag ' + n.tag}>{TAGS[n.tag] || '中性'}</span>
            <div className="body">
              <div className="ti">{n.title}</div>
              <div className="im">
                {n.impact}
                {n.source_url ? <> · <a href={n.source_url} target="_blank" rel="noreferrer">來源：{n.source_name}</a></> : null}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function EventRow({ ev, field }) {
  const { mm, dd } = monthDay(ev.date)
  return (
    <div className="evt">
      <div className="d"><div className="mm">{mm}</div><div className="dd">{dd}</div></div>
      <div><div className="ti">{ev.name}</div><div className="x">{ev[field]}</div></div>
    </div>
  )
}

export function UpcomingEvents({ events }) {
  return (
    <section className="card col-5" data-region="⑥ 本週重大日程">
      <div className="card-h"><span className="label">本週重大日程</span></div>
      {events.map((ev, i) => <EventRow ev={ev} field="analysis" key={i} />)}
    </section>
  )
}

export function PastReview({ events }) {
  return (
    <section className="card col-5" data-region="⑦ 昨日日程回顧">
      <div className="card-h"><span className="label">昨日日程回顧</span></div>
      {events.map((ev, i) => <EventRow ev={ev} field="result" key={i} />)}
    </section>
  )
}

// 跟著上方台股/美股分頁切換，只顯示當前市場的研判
export function Verdict({ verdict, tab = 'tw' }) {
  const v = verdict[tab] || verdict.tw || verdict
  const market = tab === 'us' ? '美股' : '台股'
  const flag = tab === 'us' ? '🇺🇸' : '🇹🇼'
  const cols = [
    { cls: 'good', ic: '＋', title: '利多', items: v.bullish },
    { cls: 'bad', ic: '－', title: '利空', items: v.bearish },
    { cls: 'risk', ic: '!', title: '隱憂', items: v.risks },
  ]
  const score = typeof v.score === 'number' ? Math.max(0, Math.min(100, v.score)) : null
  const tone = score == null ? '' : score >= 60 ? 'up' : score <= 40 ? 'down' : 'neu'
  return (
    <section className="card col-12" data-region="⑧ 今日綜合研判">
      <div className="card-h">
        <span className="label">今日綜合研判 · {flag} {market}</span>
        <span className="meta">跟隨上方分頁切換</span>
      </div>
      {v.stance && (
        <div className="stance">
          <div className="stance-top">
            <span className="stance-tag">{flag} {market}研判</span>
            <span className={'stance-label ' + tone}>{v.stance}</span>
          </div>
          {score != null && (
            <>
              <div className="stance-bar"><i style={{ left: `${score}%` }} /></div>
              <div className="stance-scale"><span>偏空</span><span>中性</span><span>偏多</span></div>
            </>
          )}
          {v.comment && <div className="stance-comment">{v.comment}</div>}
        </div>
      )}
      <div className="verdict">
        {cols.map((c) => (
          <div className={'vc ' + c.cls} key={c.cls}>
            <h3><span className="ic">{c.ic}</span>{c.title}</h3>
            {(c.items || []).map((it, i) => <li key={i}>{it}</li>)}
          </div>
        ))}
      </div>
    </section>
  )
}
