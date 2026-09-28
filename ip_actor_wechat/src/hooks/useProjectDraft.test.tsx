import { renderHook, act } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const storage = new Map<string, unknown>()

vi.mock('@tarojs/taro', () => ({
  default: {
    getStorageSync: (key: string) => storage.get(key),
    setStorageSync: (key: string, value: unknown) => storage.set(key, value),
  },
}))

import { useProjectDraft } from './useProjectDraft'

describe('useProjectDraft', () => {
  beforeEach(() => storage.clear())

  it('hydrates the stored draft and persists typed field changes', () => {
    storage.set('starhub-project-draft', { name: '南京站', artist_fee: 100 })
    const { result } = renderHook(() => useProjectDraft())

    expect(result.current.draft.name).toBe('南京站')
    act(() => result.current.updateDraft('artist_fee', '120'))
    expect(result.current.draft.artist_fee).toBe(120)
    expect(storage.get('starhub-project-draft')).toMatchObject({ artist_fee: 120 })
  })

  it('applies only supported scalar candidate patch fields', () => {
    const { result } = renderHook(() => useProjectDraft())

    act(() => result.current.applyCandidatePatch({
      artist_id: 7,
      artist_name: '周杰伦',
      venue: '南京奥体中心',
      unsupported: 'ignored',
      nested: { value: 'ignored' },
    } as never))

    expect(result.current.draft).toMatchObject({
      artist_id: 7,
      artist_name: '周杰伦',
      venue: '南京奥体中心',
    })
    expect(result.current.draft).not.toHaveProperty('unsupported')
    expect(result.current.draft).not.toHaveProperty('nested')
  })
})
