const base = import.meta.env.BASE_URL

// 日期由新到舊排序（YYYY-MM-DD 字串可直接字典序排序）
export const sortDatesDesc = (dates) => [...dates].sort().reverse()

export async function loadIndex() {
  const r = await fetch(`${base}data/index.json`)
  if (!r.ok) throw new Error(`index.json 載入失敗 (${r.status})`)
  const json = await r.json()
  return sortDatesDesc(json.dates || [])
}

export async function loadDay(date) {
  const r = await fetch(`${base}data/${date}.json`)
  if (!r.ok) throw new Error(`${date} 資料載入失敗 (${r.status})`)
  return r.json()
}
