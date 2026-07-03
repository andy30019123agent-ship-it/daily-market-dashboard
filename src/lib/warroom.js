// 作戰室分組：觀察中（今日在榜）/ 發動中（近日觸發發動）/ 已淘汰（近日掉出榜）
function daysBetween(a, b) {
  const d = (new Date(b) - new Date(a)) / 86400000
  return Number.isFinite(d) ? d : Infinity
}

export function groupWarRoom(history, todayStocks, date, opts = {}) {
  const launchDays = opts.launchDays ?? 5
  const dropDays = opts.dropDays ?? 5
  const stocks = (history && history.stocks) || {}
  const todayCodes = new Set((todayStocks || []).map((s) => s.code))
  const watching = [...(todayStocks || [])]
  const launched = []
  const dropped = []
  for (const [code, rec] of Object.entries(stocks)) {
    if (rec.alerted_date && daysBetween(rec.alerted_date, date) <= launchDays) {
      launched.push({ code, ...rec })
    }
    if (!todayCodes.has(code) && rec.last_date &&
        daysBetween(rec.last_date, date) <= dropDays) {
      dropped.push({ code, ...rec })
    }
  }
  return { watching, launched, dropped }
}
