import { describe, it, expect } from 'vitest'
import { sortDatesDesc } from '../loadDay.js'

describe('sortDatesDesc', () => {
  it('新到舊排序', () => {
    expect(sortDatesDesc(['2026-06-17', '2026-06-18', '2026-06-16']))
      .toEqual(['2026-06-18', '2026-06-17', '2026-06-16'])
  })

  it('不修改原陣列', () => {
    const src = ['2026-06-17', '2026-06-18']
    sortDatesDesc(src)
    expect(src).toEqual(['2026-06-17', '2026-06-18'])
  })
})
