import { monthDay } from '../lib/format.js'

const TAGS = { pos: '利多', neg: '利空', neu: '中性' }

// 只信任 http(s) 連結，擋掉 javascript: 等注入
const safeUrl = (u) => (/^https?:\/\//i.test(u || '') ? u : null)

export function News({ news }) {
  return (
    <section className="card col-7" data-region="⑤ 影響股市消息">
      <div className="card-h"><span className="label">川普及影響股市消息</span></div>
      <div className="news">
        {(news && news.length > 0) ? news.map((n, i) => (
          <div className="newsrow" key={i}>
            <span className={'tag ' + n.tag}>{TAGS[n.tag] || '中性'}</span>
            <div className="body">
              <div className="ti">{n.title}</div>
              <div className="im">
                {n.impact}
                {safeUrl(n.source_url) ? <> · <a href={safeUrl(n.source_url)} target="_blank" rel="noreferrer">來源：{n.source_name}</a></> : null}
              </div>
            </div>
          </div>
        )) : (
          <div style={{ color: 'var(--muted)', fontSize: 13, lineHeight: 1.7, padding: '14px 2px' }}>
            今日無符合條件的即時新聞<br />（寧缺勿錯：已濾掉別天舊聞與影片／社群來源）
          </div>
        )}
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

const emptyStyle = { color: 'var(--muted)', fontSize: 13, lineHeight: 1.7, padding: '10px 2px' }

export function UpcomingEvents({ events }) {
  return (
    <section className="card col-5" data-region="⑥ 本週重大日程">
      <div className="card-h"><span className="label">本週重大日程</span></div>
      {(events && events.length > 0)
        ? events.map((ev, i) => <EventRow ev={ev} field="analysis" key={i} />)
        : <div style={emptyStyle}>本週暫無重大財經日程</div>}
    </section>
  )
}

export function PastReview({ events }) {
  return (
    <section className="card col-5" data-region="⑦ 昨日日程回顧">
      <div className="card-h"><span className="label">昨日日程回顧</span></div>
      {(events && events.length > 0)
        ? events.map((ev, i) => <EventRow ev={ev} field="result" key={i} />)
        : <div style={emptyStyle}>近日無已發生的重大日程回顧</div>}
    </section>
  )
}

// 研判成績單：命中率回測結果（accuracy.json 讀不到或該市場尚無樣本就不顯示）
function AccuracyBox({ accuracy, tab }) {
  const a = accuracy && accuracy[tab]
  if (!a || !a.total) return null
  return (
    <div className="accuracy-box">
      <div className="accuracy-h">📊 研判成績單</div>
      <div>
        命中率 <b className="mono">{a.hit_rate}%</b>（{a.hit}/{a.total} 次）
        {a.recent30_rate != null && <>，近 30 次 <b className="mono">{a.recent30_rate}%</b></>}
        {a.total < 20 && <span className="accuracy-note">樣本尚少，僅供參考</span>}
      </div>
    </div>
  )
}

// 跟著上方台股/美股分頁切換，只顯示當前市場的研判
export function Verdict({ verdict, tab = 'tw', accuracy }) {
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
          <AccuracyBox accuracy={accuracy} tab={tab} />
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
      <div className="ai-disclaimer">本研判由 AI 自動彙整生成，僅供研究參考，不構成投資建議</div>
    </section>
  )
}
