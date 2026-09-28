import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { MiniappScreenData } from '@/types/domain'

vi.mock('@tarojs/taro', () => ({
  default: {
    getStorageSync: () => undefined,
  },
}))

import { useMiniappScreenData } from './useMiniappScreenData'

const data: MiniappScreenData = {
  screen_id: 'S11',
  summary: { title: '项目详情', subtitle: '真实数据' },
  items: [{ id: 'project-42', entity_type: 'project', title: '真实项目', status: 'active', context: { project_id: 42 } }],
  options: {},
  context: {},
  empty_state: null,
}

describe('useMiniappScreenData', () => {
  it('sends only the screen required context and normalizes returned items', async () => {
    const fetchScreen = vi.fn().mockResolvedValue(data)
    const { result } = renderHook(() => useMiniappScreenData({
      screenId: 'S11',
      context: { project_id: 42, task_id: 9 },
      fetchScreen,
    }))

    await waitFor(() => expect(result.current.state).toBe('success'))
    expect(fetchScreen).toHaveBeenCalledWith('S11', { project_id: 42 })
    expect(result.current.items[0]).toMatchObject({ title: '真实项目', status: '进行中' })
  })

  it('keeps a missing-context response on the current page', async () => {
    const fetchScreen = vi.fn().mockRejectedValue({ statusCode: 422 })
    const onRedirect = vi.fn()
    const { result } = renderHook(() => useMiniappScreenData({ screenId: 'S11', context: {}, onRedirect, fetchScreen }))

    await waitFor(() => expect(result.current.state).toBe('error'))
    expect(result.current.message).toContain('缺少打开当前页面')
    expect(onRedirect).not.toHaveBeenCalled()
  })

  it('redirects authentication and permission failures through the caller', async () => {
    const fetchScreen = vi.fn().mockRejectedValue({ statusCode: 403 })
    const onRedirect = vi.fn()
    renderHook(() => useMiniappScreenData({ screenId: 'S11', context: {}, onRedirect, fetchScreen }))

    await waitFor(() => expect(onRedirect).toHaveBeenCalledWith('S77'))
  })
})
