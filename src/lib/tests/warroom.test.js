import { describe, it, expect } from 'vitest'
import { groupWarRoom } from '../warroom.js'

describe('groupWarRoom', () => {
  it('分成 觀察中/發動中/已淘汰', () => {
    const history = {
      last_date: '2026-07-03',
      stocks: {
        2603: { name: '長榮', streak: 3, last_date: '2026-07-03' },
        1101: { name: '台泥', last_date: '2026-07-03', alerted_date: '2026-07-02' }, // 發動中
        1216: { name: '統一', last_date: '2026-06-30' }, // 已淘汰（近日掉出）
      },
    }
    const today = [{ code: '2603', name: '長榮', score: 80, streak: 3 }]
    const g = groupWarRoom(history, today, '2026-07-03', { launchDays: 5, dropDays: 5 })
    expect(g.watching.map((s) => s.code)).toContain('2603')
    expect(g.launched.map((s) => s.code)).toContain('1101')
    expect(g.dropped.map((s) => s.code)).toContain('1216')
  })

  it('無歷史時 watching 仍等於今日清單', () => {
    const g = groupWarRoom(null, [{ code: '2330', name: '台積電' }], '2026-07-03')
    expect(g.watching).toHaveLength(1)
    expect(g.launched).toHaveLength(0)
    expect(g.dropped).toHaveLength(0)
  })
})
