// 顯示用格式化工具
const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

export const fmtNum = (n) =>
  typeof n === 'number' ? n.toLocaleString('en-US', { maximumFractionDigits: 2 }) : n

// 漲跌方向：正→up（紅）、負→down（綠）；dir 可強制覆寫
export const dirClass = (pct, dir) => {
  if (dir === 'up' || dir === 'down') return dir
  return (pct ?? 0) >= 0 ? 'up' : 'down'
}

export const pctText = (pct) => {
  if (typeof pct !== 'number') return ''
  const arrow = pct >= 0 ? '▲' : '▼'
  const sign = pct >= 0 ? '+' : ''
  return `${arrow} ${sign}${pct.toFixed(2)}%`
}

// "2026-06-18" → {mm:"JUN", dd:"18"}
export const monthDay = (iso) => {
  const [, m, d] = (iso || '').split('-')
  return { mm: MONTHS[Number(m) - 1] || '', dd: d || '' }
}

// "2026-06-18" → "2026-06-18（四）"
export const dateWithWeekday = (iso) => {
  if (!iso) return ''
  const wk = ['日', '一', '二', '三', '四', '五', '六']
  const [y, m, d] = iso.split('-').map(Number)
  const dt = new Date(Date.UTC(y, m - 1, d))
  return `${iso}（${wk[dt.getUTCDay()] ?? ''}）`
}
