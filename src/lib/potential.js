// 低基期潛力雷達前端純函式
export function isGolden(s, posMax = 0.4) {
  return (s?.price_pos ?? 1) <= posMax && (s?.inst_net_yi ?? 0) > 0
}

export function fmtPct(x) {
  const v = (x ?? 0) * 100
  return `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`
}
