import { describe, it, expect } from 'vitest'
import { isGolden, fmtPct, scoreTier, sparkPath } from '../potential.js'

describe('potential helpers', () => {
  it('isGolden: 低基期且法人買', () => {
    expect(isGolden({ price_pos: 0.2, inst_net_yi: 3 })).toBe(true)
    expect(isGolden({ price_pos: 0.8, inst_net_yi: 3 })).toBe(false)
    expect(isGolden({ price_pos: 0.2, inst_net_yi: -1 })).toBe(false)
  })
  it('fmtPct', () => {
    expect(fmtPct(0.06)).toBe('+6.0%')
    expect(fmtPct(-0.153)).toBe('-15.3%')
  })
})

describe('scoreTier', () => {
  it('分級', () => {
    expect(scoreTier(80)).toBe('hot')
    expect(scoreTier(55)).toBe('warm')
    expect(scoreTier(30)).toBe('cool')
  })
})

describe('sparkPath', () => {
  it('產生 polyline points，端點對齊', () => {
    const s = sparkPath([1, 2, 3], 100, 20)
    const pts = s.split(' ')
    expect(pts.length).toBe(3)
    expect(pts[0].startsWith('0,')).toBe(true) // 第一點 x=0
    expect(pts[2].startsWith('100,')).toBe(true) // 最後一點 x=w
  })
  it('點數不足回空字串', () => {
    expect(sparkPath([5], 100, 20)).toBe('')
  })
})
