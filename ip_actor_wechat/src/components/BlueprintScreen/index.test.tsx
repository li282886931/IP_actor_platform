import React from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { MiniappScreenData } from '@/types/domain'

const taroMocks = vi.hoisted(() => ({
  getMiniappScreen: vi.fn(),
  navigateTo: vi.fn(),
  redirectTo: vi.fn(),
  switchTab: vi.fn(),
  stopPullDownRefresh: vi.fn(),
  storage: new Map<string, unknown>(),
  params: {} as Record<string, string>,
}))

vi.mock('@tarojs/components', () => ({
  Button: ({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) => <button {...props}>{children}</button>,
  Input: (props: React.InputHTMLAttributes<HTMLInputElement>) => <input {...props} />,
  ScrollView: ({ children }: React.HTMLAttributes<HTMLDivElement>) => <div>{children}</div>,
  Text: ({ children, ...props }: React.HTMLAttributes<HTMLSpanElement>) => <span {...props}>{children}</span>,
  View: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => <div {...props}>{children}</div>,
}))

vi.mock('@tarojs/taro', () => ({
  default: {
    ENV_TYPE: { WEAPP: 'WEAPP' },
    getEnv: () => 'WEB',
    getStorageSync: (key: string) => taroMocks.storage.get(key),
    setStorageSync: (key: string, value: unknown) => taroMocks.storage.set(key, value),
    removeStorageSync: (key: string) => taroMocks.storage.delete(key),
    navigateTo: taroMocks.navigateTo,
    redirectTo: taroMocks.redirectTo,
    switchTab: taroMocks.switchTab,
    stopPullDownRefresh: taroMocks.stopPullDownRefresh,
  },
  usePullDownRefresh: vi.fn(),
  useRouter: () => ({ params: taroMocks.params }),
}))

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api')
  return {
    ...actual,
    getApiBase: () => 'http://127.0.0.1:8000',
    api: {
      ...actual.api,
      getMiniappScreen: taroMocks.getMiniappScreen,
    },
  }
})

import { ApiError } from '@/services/api'
import BlueprintScreen from './index'

const response = (overrides: Partial<MiniappScreenData> = {}): MiniappScreenData => ({
  screen_id: 'S10',
  summary: {
    title: '服务端项目标题',
    subtitle: '服务端项目副标题',
    highlight: '7 个进行中',
  },
  items: [{
    id: '42',
    entity_type: 'project',
    title: '真实项目',
    description: '数据库项目',
    status: '进行中',
    value: '负责人甲',
    details: null,
    context: { project_id: 42 },
  }],
  options: {},
  context: {},
  empty_state: null,
  ...overrides,
})

describe('BlueprintScreen aggregated loading', () => {
  beforeEach(() => {
    taroMocks.getMiniappScreen.mockReset()
    taroMocks.navigateTo.mockReset()
    taroMocks.redirectTo.mockReset()
    taroMocks.switchTab.mockReset()
    taroMocks.stopPullDownRefresh.mockReset()
    taroMocks.storage.clear()
    taroMocks.params = {}
  })

  it('loads a screen once and renders response summary and item count', async () => {
    taroMocks.getMiniappScreen.mockResolvedValue(response())

    render(<BlueprintScreen screenId='S10' />)

    expect(await screen.findByText('服务端项目标题')).toBeInTheDocument()
    expect(screen.getByText('服务端项目副标题')).toBeInTheDocument()
    expect(screen.getByText('7 个进行中')).toBeInTheDocument()
    expect(screen.getByText('1 项')).toBeInTheDocument()
    expect(screen.getByText('真实项目')).toBeInTheDocument()
    expect(taroMocks.getMiniappScreen).toHaveBeenCalledTimes(1)
    expect(taroMocks.getMiniappScreen).toHaveBeenCalledWith('S10', {})
  })

  it('only sends cached entity context required by the current screen', async () => {
    taroMocks.storage.set('starhub-project-id', 42)
    taroMocks.getMiniappScreen.mockResolvedValue(response())
    const view = render(<BlueprintScreen screenId='S10' />)
    await screen.findByText('真实项目')

    expect(taroMocks.getMiniappScreen).toHaveBeenLastCalledWith('S10', {})

    taroMocks.getMiniappScreen.mockResolvedValue(response({
      screen_id: 'S11',
      summary: { title: '项目详情' },
    }))
    view.rerender(<BlueprintScreen screenId='S11' />)

    await screen.findByText('项目详情')
    expect(taroMocks.getMiniappScreen).toHaveBeenLastCalledWith('S11', { project_id: 42 })
  })

  it('clears items from the previous screen before the next request resolves', async () => {
    let resolveNext: ((value: MiniappScreenData) => void) | undefined
    taroMocks.getMiniappScreen
      .mockResolvedValueOnce(response())
      .mockImplementationOnce(() => new Promise((resolve) => {
        resolveNext = resolve
      }))
    const view = render(<BlueprintScreen screenId='S10' />)
    await screen.findByText('真实项目')

    view.rerender(<BlueprintScreen screenId='S11' />)

    await waitFor(() => {
      expect(screen.queryByText('真实项目')).not.toBeInTheDocument()
      expect(screen.getByText('正在连接决策服务...')).toBeInTheDocument()
    })
    resolveNext?.(response({
      screen_id: 'S11',
      summary: { title: '项目详情' },
      items: [],
    }))
    expect(await screen.findByText('项目详情')).toBeInTheDocument()
  })

  it('renders the server empty state when a successful response has no items', async () => {
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      items: [],
      empty_state: {
        title: '还没有项目',
        description: '创建项目后会显示在这里。',
        action: { label: '创建项目', target_screen: 'S13' },
      },
    }))

    render(<BlueprintScreen screenId='S10' />)

    expect(await screen.findByText('还没有项目')).toBeInTheDocument()
    expect(screen.getByText('创建项目后会显示在这里。')).toBeInTheDocument()
    expect(screen.queryByText('星河计划·南京站')).not.toBeInTheDocument()
  })

  it('shows a retry action after a network failure without fixture data', async () => {
    taroMocks.getMiniappScreen
      .mockRejectedValueOnce(new Error('network down'))
      .mockResolvedValueOnce(response())

    render(<BlueprintScreen screenId='S10' />)

    expect(await screen.findByText('页面数据加载失败，请重试。')).toBeInTheDocument()
    expect(screen.queryByText('星河计划·南京站')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '重新加载' }))

    expect(await screen.findByText('真实项目')).toBeInTheDocument()
    expect(taroMocks.getMiniappScreen).toHaveBeenCalledTimes(2)
  })

  it.each([
    [401, 'S81'],
    [403, 'S77'],
    [409, 'S78'],
  ])('routes HTTP %s failures to %s', async (statusCode, target) => {
    taroMocks.getMiniappScreen.mockRejectedValue(new ApiError(`HTTP_${statusCode}`, statusCode))

    render(<BlueprintScreen screenId='S11' />)

    await waitFor(() => {
      expect(taroMocks.redirectTo).toHaveBeenCalledWith({ url: `/pages/${target.toLowerCase()}/index` })
    })
  })

  it('keeps HTTP 422 on the page and explains the missing context', async () => {
    taroMocks.getMiniappScreen.mockRejectedValue(new ApiError('HTTP_422', 422))

    render(<BlueprintScreen screenId='S11' />)

    expect(await screen.findByText('缺少打开当前页面所需的项目、版本或任务信息。')).toBeInTheDocument()
    expect(taroMocks.redirectTo).not.toHaveBeenCalled()
  })

  it('uses the task id from aggregated item context for task navigation', async () => {
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      screen_id: 'S55',
      summary: { title: '任务列表' },
      items: [{
        id: 'task-42',
        entity_type: 'task',
        title: '真实任务',
        description: '来自聚合接口',
        status: 'pending',
        context: { task_id: 42 },
      }],
    }))

    render(<BlueprintScreen screenId='S55' />)
    fireEvent.click(await screen.findByText('真实任务'))

    expect(taroMocks.storage.get('starhub-task-id')).toBe(42)
    expect(taroMocks.redirectTo).toHaveBeenCalledWith({ url: '/pages/s56/index' })
  })
})
