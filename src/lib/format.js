// 顯示用格式化工具
const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

export const fmtNum = (n) => {
  if (typeof n !== 'number') return n
  return Number.isFinite(n) ? n.toLocaleString('en-US', { maximumFractionDigits: 2 }) : '—'
}

// 漲跌方向：正→up（紅）、負→down（綠）；缺值/非數字→flat（灰），不再誤染成紅漲；dir 可強制覆寫
export const dirClass = (pct, dir) => {
  if (dir === 'up' || dir === 'down' || dir === 'flat') return dir
  if (!Number.isFinite(pct)) return 'flat'
  return pct >= 0 ? 'up' : 'down'
}

export const pctText = (pct) => {
  if (!Number.isFinite(pct)) return '—'
  const arrow = pct >= 0 ? '▲' : '▼'
  const sign = pct >= 0 ? '+' : ''
  return `${arrow} ${sign}${pct.toFixed(2)}%`
}

// "2026-06-18" → {mm:"JUN", dd:"18"}
export const monthDay = (iso) => {
  const [, m, d] = (iso || '').split('-')
  return { mm: MONTHS[Number(m) - 1] || '', dd: d || '' }
}

// 讓「用 div 做的可點元素」具備鍵盤與讀屏可及性：套上 role/tabIndex 並讓 Enter/Space 觸發。
// 用法：<div {...activate(() => doSomething())}>；label 可選，給讀屏更清楚的名稱。
export const activate = (fn, label) => ({
  role: 'button',
  tabIndex: 0,
  'aria-label': label,
  onClick: fn,
  onKeyDown: (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fn() }
  },
})

// "2026-06-18" → "2026-06-18（四）"
export const dateWithWeekday = (iso) => {
  if (!iso) return ''
  const wk = ['日', '一', '二', '三', '四', '五', '六']
  const [y, m, d] = iso.split('-').map(Number)
  const dt = new Date(Date.UTC(y, m - 1, d))
  return `${iso}（${wk[dt.getUTCDay()] ?? ''}）`
}
