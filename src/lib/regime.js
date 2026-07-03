// 市場紅綠燈（元件 A）前端用純函式，抽出方便單元測試（同 potential.js / radar.js 慣例）。

export const REGIME_LIGHT = {
  green: { emoji: '🟢', label: '偏多．綠燈', cls: 'up' },
  yellow: { emoji: '🟡', label: '中性．黃燈', cls: 'neu' },
  red: { emoji: '🔴', label: '偏空．紅燈', cls: 'down' },
}

// 未知/缺值燈號一律安全退回黃燈樣式，不讓畫面崩掉
export function lightMeta(light) {
  return REGIME_LIGHT[light] || REGIME_LIGHT.yellow
}

// 分項分數 -> 色調 class（沿用專案既有慣例：up=正向/紅、down=負向/綠、neu=中性）
export function scoreTone(score) {
  if (score > 0) return 'up'
  if (score < 0) return 'down'
  return 'neu'
}

// 分項顯示文字：missing 或缺物件一律顯示「資料缺」，不顯示 undefined/NaN
export function scoreText(component) {
  if (!component || component.missing) return '資料缺'
  const s = component.score
  return (s > 0 ? '+' : '') + s + ' 分'
}
