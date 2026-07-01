// 把多天的 radar 累加成「近 N 日」視圖：
// 法人淨買超（inst_net_yi）加總、漲跌幅（pct）累計、成交值（value_yi）加總。
// days：day 物件陣列，最新在前；只取有 radar 的天。名稱/代號/類別以最新一筆為準。
export function aggregateRadar(days) {
  const round2 = (n) => Math.round(n * 100) / 100
  const accumulate = (pickArr, keyOf) => {
    const m = new Map()
    for (const d of days) {
      for (const it of pickArr(d)) {
        const k = keyOf(it)
        if (k == null) continue
        const cur = m.get(k)
        if (cur) {
          cur.inst_net_yi += it.inst_net_yi || 0
          cur.pct += it.pct || 0
          cur.value_yi += it.value_yi || 0
        } else {
          // 首見（最新那天）→ 以它的名稱/代號/類別為準，數值歸零後累加
          m.set(k, { ...it, inst_net_yi: it.inst_net_yi || 0, pct: it.pct || 0, value_yi: it.value_yi || 0 })
        }
      }
    }
    return [...m.values()].map((x) => ({
      ...x,
      inst_net_yi: round2(x.inst_net_yi),
      pct: round2(x.pct),
      value_yi: round2(x.value_yi),
    }))
  }
  return {
    stocks: accumulate((d) => (d.radar && d.radar.stocks) || [], (s) => s.code),
    sectors: accumulate((d) => (d.radar && d.radar.sectors) || [], (s) => s.name),
  }
}
