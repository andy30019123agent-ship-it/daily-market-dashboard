// 迷你走勢線（平滑面積 + 收尾點）
export default function Sparkline({ points = [], color = '#FF4D5E', width = 220, height = 86 }) {
  if (!points.length) return null
  const min = Math.min(...points)
  const max = Math.max(...points)
  const pad = 8
  const X = (i) => (i / (points.length - 1)) * width
  const Y = (v) => pad + ((max - v) / (max - min || 1)) * (height - pad * 2)
  const line = 'M' + points.map((v, i) => `${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(' L')
  const area = `${line} L${width},${height} L0,${height} Z`
  const gid = `spk-${color.replace('#', '')}-${points.length}`
  return (
    <svg className="spark" width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity=".28" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gid})`} />
      <path d={line} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={width} cy={Y(points[points.length - 1]).toFixed(1)} r="3.2" fill={color} />
    </svg>
  )
}
