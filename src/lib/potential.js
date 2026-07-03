// 低基期潛力雷達前端純函式
export function isGolden(s, posMax = 0.4) {
  return (s?.price_pos ?? 1) <= posMax && (s?.inst_net_yi ?? 0) > 0
}

export function fmtPct(x) {
  const v = (x ?? 0) * 100
  return `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`
}

// 分數分級：≥70 hot、≥50 warm、其餘 cool
export function scoreTier(score) {
  const s = score ?? 0
  return s >= 70 ? 'hot' : s >= 50 ? 'warm' : 'cool'
}

// 數列 → SVG polyline points（x 均分 0..w，y 依 min..max 映射到 h..0）
export function sparkPath(points, w, h) {
  if (!points || points.length < 2) return ''
  const min = Math.min(...points)
  const max = Math.max(...points)
  const span = max - min || 1
  return points
    .map((v, i) => {
      const x = (i / (points.length - 1)) * w
      const y = h - ((v - min) / span) * h
      return `${+x.toFixed(1)},${+y.toFixed(1)}`
    })
    .join(' ')
}
