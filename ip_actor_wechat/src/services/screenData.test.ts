import Taro from '@tarojs/taro'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, api } from './api'

vi.mock('@tarojs/taro', () => ({
  default: {
    getStorageSync: vi.fn(),
    request: vi.fn(),
  },
}))

const requestMock = vi.mocked(Taro.request)

describe('getMiniappScreen', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(Taro.getStorageSync).mockReturnValue('')
  })

  it('builds the screen URL without undefined context values', async () => {
    requestMock.mockResolvedValue({
      statusCode: 200,
      data: {
        code: 0,
        message: 'ok',
        data: {
          screen_id: 'S11',
          summary: { title: '真实项目', subtitle: null, highlight: null },
          items: [],
          options: {},
          context: { project_id: 42 },
          empty_state: null,
        },
      },
    } as never)

    const result = await api.getMiniappScreen('S11', {
      project_id: 42,
      version_id: undefined,
      keyword: '',
    })

    expect(requestMock).toHaveBeenCalledWith(expect.objectContaining({
      url: expect.stringMatching(/\/miniapp\/screens\/S11\?project_id=42$/),
    }))
    expect(result.items).toEqual([])
    expect(result.summary.title).toBe('真实项目')
  })

  it.each([401, 403, 409, 422])('preserves HTTP %s as an ApiError code', async (statusCode) => {
    requestMock.mockResolvedValue({
      statusCode,
      data: { detail: 'request failed' },
    } as never)

    await expect(api.getMiniappScreen('S11', { project_id: 42 })).rejects.toMatchObject({
      name: 'ApiError',
      code: `HTTP_${statusCode}`,
      statusCode,
    } satisfies Partial<ApiError>)
  })
})

describe('getMiniappEntityDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(Taro.getStorageSync).mockReturnValue('')
  })

  it('requests the encoded entity detail path', async () => {
    requestMock.mockResolvedValue({
      statusCode: 200,
      data: {
        code: 0,
        message: 'ok',
        data: {
          entity_type: 'show',
          entity_id: 3,
          title: '真实演出',
          fields: [],
          sections: [],
          related_items: [],
          actions: [],
        },
      },
    } as never)

    const result = await api.getMiniappEntityDetail('show', 3)

    expect(requestMock).toHaveBeenCalledWith(expect.objectContaining({
      url: expect.stringMatching(/\/miniapp\/entities\/show\/3$/),
    }))
    expect(result.entity_id).toBe(3)
  })
})

describe('searchMiniappEntities', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(Taro.getStorageSync).mockReturnValue('')
  })

  it('encodes the normalized keyword and preserves grouped entity ids', async () => {
    requestMock.mockResolvedValue({
      statusCode: 200,
      data: {
        code: 0,
        message: 'ok',
        data: {
          keyword: '南京',
          groups: [{
            entity_type: 'venue',
            label: '场馆',
            items: [{
              entity_type: 'venue',
              entity_id: 9,
              label: '南京体育中心',
              description: '南京',
              value: { id: 9 },
            }],
          }],
        },
      },
    } as never)

    const result = await api.searchMiniappEntities(' 南京 ')

    expect(requestMock).toHaveBeenCalledWith(expect.objectContaining({
      url: expect.stringMatching(/\/miniapp\/search\?q=%E5%8D%97%E4%BA%AC$/),
    }))
    expect(result.groups[0].items[0].entity_id).toBe(9)
  })
})
