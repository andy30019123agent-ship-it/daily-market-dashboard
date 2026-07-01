import { describe, it, expect } from 'vitest'
import { aggregateRadar } from '../radar.js'

const mk = (stocks, sectors = []) => ({ radar: { stocks, sectors } })

describe('aggregateRadar 近 N 日累加', () => {
  it('法人淨買超加總、漲跌幅累計、成交值加總', () => {
    const days = [
      mk([{ code: '2330', name: '台積電', sector: '半導體', inst_net_yi: 10, pct: 2, value_yi: 100 }]),
      mk([{ code: '2330', name: '台積電', sector: '半導體', inst_net_yi: -3, pct: -1, value_yi: 50 }]),
    ]
    const { stocks } = aggregateRadar(days)
    expect(stocks).toHaveLength(1)
    expect(stocks[0].inst_net_yi).toBe(7)   // 10 + (-3)
    expect(stocks[0].pct).toBe(1)           // 2 + (-1)
    expect(stocks[0].value_yi).toBe(150)    // 100 + 50
  })

  it('名稱以最新一筆（最前）為準；只出現在某天的股也納入', () => {
    const days = [
      mk([{ code: '2330', name: '台積電-新', inst_net_yi: 5, pct: 1, value_yi: 10 }]),
      mk([
        { code: '2330', name: '台積電-舊', inst_net_yi: 5, pct: 1, value_yi: 10 },
        { code: '2317', name: '鴻海', inst_net_yi: 8, pct: 3, value_yi: 20 },
      ]),
    ]
    const { stocks } = aggregateRadar(days)
    const tsmc = stocks.find((s) => s.code === '2330')
    const hon = stocks.find((s) => s.code === '2317')
    expect(tsmc.name).toBe('台積電-新')   // 最新在前
    expect(tsmc.inst_net_yi).toBe(10)
    expect(hon.inst_net_yi).toBe(8)        // 只出現在舊那天也保留
  })

  it('類股依名稱累加、缺 radar 的天略過', () => {
    const days = [
      mk([], [{ name: '半導體', inst_net_yi: 20, pct: 2, value_yi: 500 }]),
      { radar: null },
      mk([], [{ name: '半導體', inst_net_yi: 10, pct: 1, value_yi: 300 }]),
    ]
    const { sectors } = aggregateRadar(days)
    expect(sectors).toHaveLength(1)
    expect(sectors[0].inst_net_yi).toBe(30)
    expect(sectors[0].value_yi).toBe(800)
  })
})
