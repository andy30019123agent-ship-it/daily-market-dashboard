import { monthDay } from '../lib/format.js'

const TAGS = { pos: '利多', neg: '利空', neu: '中性' }

export function News({ news }) {
  return (
    <section className="card col-7">
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
    <section className="card col-5">
      <div className="card-h"><span className="label">本週重大日程</span></div>
      {events.map((ev, i) => <EventRow ev={ev} field="analysis" key={i} />)}
    </section>
  )
}

export function PastReview({ events }) {
  return (
    <section className="card col-5">
      <div className="card-h"><span className="label">昨日日程回顧</span></div>
      {events.map((ev, i) => <EventRow ev={ev} field="result" key={i} />)}
    </section>
  )
}

export function Verdict({ verdict }) {
  const cols = [
    { cls: 'good', ic: '＋', title: '利多', items: verdict.bullish },
    { cls: 'bad', ic: '－', title: '利空', items: verdict.bearish },
    { cls: 'risk', ic: '!', title: '隱憂', items: verdict.risks },
  ]
  return (
    <section className="card col-7">
      <div className="card-h"><span className="label">今日綜合研判</span></div>
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
