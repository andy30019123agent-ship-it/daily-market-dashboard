import { describe, it, expect } from 'vitest'
import { isGolden, fmtPct } from '../potential.js'

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
