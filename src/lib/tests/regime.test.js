import { describe, it, expect } from 'vitest'
import { lightMeta, scoreTone, scoreText, REGIME_LIGHT } from '../regime.js'

describe('regime helpers', () => {
  it('lightMeta: 已知燈號回對應樣式', () => {
    expect(lightMeta('green')).toEqual(REGIME_LIGHT.green)
    expect(lightMeta('red')).toEqual(REGIME_LIGHT.red)
    expect(lightMeta('yellow')).toEqual(REGIME_LIGHT.yellow)
  })

  it('lightMeta: 未知/缺值燈號安全退回黃燈，不炸', () => {
    expect(lightMeta('unknown')).toEqual(REGIME_LIGHT.yellow)
    expect(lightMeta(undefined)).toEqual(REGIME_LIGHT.yellow)
  })

  it('scoreTone: 正分 up、負分 down、0 中性', () => {
    expect(scoreTone(1)).toBe('up')
    expect(scoreTone(-1)).toBe('down')
    expect(scoreTone(0)).toBe('neu')
  })

  it('scoreText: 有分數時顯示帶正負號', () => {
    expect(scoreText({ score: 1, missing: false })).toBe('+1 分')
    expect(scoreText({ score: -1, missing: false })).toBe('-1 分')
    expect(scoreText({ score: 0, missing: false })).toBe('0 分')
  })

  it('scoreText: missing 或缺物件顯示「資料缺」', () => {
    expect(scoreText({ score: 1, missing: true })).toBe('資料缺')
    expect(scoreText(null)).toBe('資料缺')
    expect(scoreText(undefined)).toBe('資料缺')
  })
})
