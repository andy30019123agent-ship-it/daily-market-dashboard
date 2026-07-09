// 市場紅綠燈（元件 A）前端用純函式，抽出方便單元測試（同 potential.js / radar.js 慣例）。

// 標籤只講多空、不再寫「綠燈/紅燈」：本站行情鐵則為紅漲綠跌（偏多=紅、偏空=綠），
// 若標籤寫「紅燈」卻上綠色會與全站顏色語意打架，故一律以多空文字＋對應漲跌色呈現。
export const REGIME_LIGHT = {
  green: { label: '偏多', cls: 'up' },
  yellow: { label: '中性', cls: 'neu' },
  red: { label: '偏空', cls: 'down' },
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
  if (!component || component.missing || !Number.isFinite(component.score)) return '資料缺'
  const s = component.score
  return (s > 0 ? '+' : '') + s + ' 分'
}
