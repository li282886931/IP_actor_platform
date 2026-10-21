import React from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { MiniappScreenData } from '@/types/domain'

const taroMocks = vi.hoisted(() => ({
  getMiniappScreen: vi.fn(),
  calculateShow: vi.fn(),
  navigateTo: vi.fn(),
  navigateBack: vi.fn(),
  redirectTo: vi.fn(),
  switchTab: vi.fn(),
  stopPullDownRefresh: vi.fn(),
  getEnv: vi.fn(() => 'WEB'),
  login: vi.fn(),
  getSystemInfoSync: vi.fn(() => ({ platform: 'ios' })),
  wechatLogin: vi.fn(),
  phoneNumberDetail: {} as { code?: string, errMsg?: string },
  storage: new Map<string, unknown>(),
  params: {} as Record<string, string>,
}))

vi.mock('@tarojs/components', () => ({
  Button: ({ children, onGetPhoneNumber, openType, onClick, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & {
    onGetPhoneNumber?: (event: { detail?: { code?: string, errMsg?: string } }) => void
    openType?: string
  }) => (
    <button
      {...props}
      onClick={(event) => {
        if (openType === 'getPhoneNumber' && onGetPhoneNumber) {
          onGetPhoneNumber({ detail: taroMocks.phoneNumberDetail })
          return
        }
        onClick?.(event)
      }}
    >
      {children}
    </button>
  ),
  Input: (props: React.InputHTMLAttributes<HTMLInputElement>) => <input {...props} />,
  ScrollView: ({ children }: React.HTMLAttributes<HTMLDivElement>) => <div>{children}</div>,
  Text: ({ children, ...props }: React.HTMLAttributes<HTMLSpanElement>) => <span {...props}>{children}</span>,
  View: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => <div {...props}>{children}</div>,
}))

vi.mock('@tarojs/taro', () => ({
  default: {
    ENV_TYPE: { WEAPP: 'WEAPP' },
    getEnv: taroMocks.getEnv,
    login: taroMocks.login,
    getSystemInfoSync: taroMocks.getSystemInfoSync,
    getStorageSync: (key: string) => taroMocks.storage.get(key),
    setStorageSync: (key: string, value: unknown) => taroMocks.storage.set(key, value),
    removeStorageSync: (key: string) => taroMocks.storage.delete(key),
    navigateTo: taroMocks.navigateTo,
    navigateBack: taroMocks.navigateBack,
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
      calculateShow: taroMocks.calculateShow,
      wechatLogin: taroMocks.wechatLogin,
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
    taroMocks.calculateShow.mockReset()
    taroMocks.navigateTo.mockReset()
    taroMocks.navigateBack.mockReset()
    taroMocks.redirectTo.mockReset()
    taroMocks.switchTab.mockReset()
    taroMocks.stopPullDownRefresh.mockReset()
    taroMocks.getEnv.mockReset()
    taroMocks.getEnv.mockReturnValue('WEB')
    taroMocks.login.mockReset()
    taroMocks.getSystemInfoSync.mockReset()
    taroMocks.getSystemInfoSync.mockReturnValue({ platform: 'ios' })
    taroMocks.wechatLogin.mockReset()
    taroMocks.phoneNumberDetail = {}
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

  it('renders real value evidence returned for the discovery homepage', async () => {
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      screen_id: 'S04',
      summary: { title: '这场演出，值得做吗？' },
      options: {
        value_evidence: [{
          title: '杭州现场演出',
          metric: '480-1280',
          source_label: '当前机会',
        }],
      },
      items: [],
    }))

    render(<BlueprintScreen screenId='S04' />)

    expect(await screen.findByText('价值证据')).toBeInTheDocument()
    expect(screen.getByText('杭州现场演出')).toBeInTheDocument()
    expect(screen.getByText('当前机会')).toBeInTheDocument()
  })

  it('renders the server-provided project work plan and human gate state', async () => {
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      screen_id: 'S53',
      summary: { title: '项目工作计划' },
      options: {
        project_work: {
          plan_version: 3,
          open_alert_count: 2,
          recommendation: '等待负责人核验后再推进。',
          human_gate: '财务与审批由负责人确认',
        },
      },
      items: [],
    }))

    render(<BlueprintScreen screenId='S53' />)

    expect(await screen.findByText('项目工作')).toBeInTheDocument()
    expect(screen.getByText('计划 V3')).toBeInTheDocument()
    expect(screen.getByText('待处理预警 2 项')).toBeInTheDocument()
    expect(screen.getByText('等待负责人核验后再推进。')).toBeInTheDocument()
    expect(screen.getByText('财务与审批由负责人确认')).toBeInTheDocument()
  })

  it('renders persisted project statuses with Chinese labels', async () => {
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      items: [{
        id: 'project-42',
        entity_type: 'project',
        title: '待确认项目',
        description: '真实数据库项目',
        status: 'pending_confirmation',
        context: { project_id: 42 },
      }],
    }))

    render(<BlueprintScreen screenId='S10' />)

    expect(await screen.findByText('待确认')).toBeInTheDocument()
    expect(screen.queryByText('pending_confirmation')).not.toBeInTheDocument()
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

  it('applies a database venue candidate patch to the project draft', async () => {
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      screen_id: 'S14',
      summary: { title: '地点与时间' },
      items: [],
      options: {
        candidate_groups: [{
          key: 'venues',
          label: '高频场馆',
          field: 'venue',
          search_mode: 'remote',
          items: [{
            key: 'venue-12',
            label: '南京奥体中心',
            description: '南京 · 容量 12000',
            entity_type: 'venue',
            entity_id: 12,
            patch: {
              venue_id: 12,
              venue: '南京奥体中心',
              city: '南京',
              venue_capacity: 12000,
            },
          }],
        }],
      },
    }))

    render(<BlueprintScreen screenId='S14' />)
    const input = await screen.findByPlaceholderText('搜索场馆名称或城市')
    fireEvent.focus(input)
    fireEvent.click(await screen.findByText('南京奥体中心'))

    expect(taroMocks.storage.get('starhub-project-draft')).toMatchObject({
      venue_id: 12,
      venue: '南京奥体中心',
      city: '南京',
      venue_capacity: 12000,
    })
  })

  it('returns a non-tab page through the back control', async () => {
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      screen_id: 'S14',
      summary: { title: '地点与时间' },
      items: [],
    }))

    render(<BlueprintScreen screenId='S14' />)
    fireEvent.click(await screen.findByRole('button', { name: '返回' }))

    expect(taroMocks.navigateBack).toHaveBeenCalledWith({ delta: 1 })
    expect(screen.queryByRole('button', { name: '主页' })).not.toBeInTheDocument()
  })

  it('does not show the back control on a tab page', async () => {
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      screen_id: 'S04',
      summary: { title: '发现演出' },
      items: [],
    }))

    render(<BlueprintScreen screenId='S04' />)
    await screen.findByText('发现演出')

    expect(screen.queryByRole('button', { name: '返回' })).not.toBeInTheDocument()
  })

  it('uses local placeholder login codes in WeChat developer tools', async () => {
    taroMocks.getEnv.mockReturnValue('WEAPP')
    taroMocks.getSystemInfoSync.mockReturnValue({ platform: 'devtools' })
    taroMocks.wechatLogin.mockResolvedValue({
      token: 'dev-token',
      user: { id: 3, account: 'b_user' },
      current_tenant: { id: 1, name: '锐音场默认空间' },
    })
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      screen_id: 'S01',
      summary: { title: '登录' },
      items: [],
    }))

    render(<BlueprintScreen screenId='S01' />)
    fireEvent.click(await screen.findByRole('button', { name: '微信安全登录' }))

    await waitFor(() => {
      expect(taroMocks.wechatLogin).toHaveBeenCalledWith({
        code: 'local-devtools-login-code',
        phone_code: 'local-devtools-phone-code',
        name: '微信用户',
      })
    })
    expect(taroMocks.login).not.toHaveBeenCalled()
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

  it('uses the task detail reference for task navigation', async () => {
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
        detail_ref: { entity_type: 'task', entity_id: 42 },
      }],
    }))

    render(<BlueprintScreen screenId='S55' />)
    fireEvent.click(await screen.findByText('真实任务'))

    expect(taroMocks.storage.get('starhub-task-id')).toBe(42)
    expect(taroMocks.navigateTo).toHaveBeenCalledWith({
      url: '/pages/entity-detail/index?entityType=task&entityId=42',
    })
  })

  it('opens the unified detail page for a persisted list entity', async () => {
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      screen_id: 'S04',
      summary: { title: '发现演出' },
      items: [{
        id: 'show-3',
        entity_type: 'show',
        title: '真实演出',
        description: '数据库演出',
        status: 'on_sale',
        context: { show_id: 3 },
        detail_ref: { entity_type: 'show', entity_id: 3 },
      }],
    }))

    render(<BlueprintScreen screenId='S04' />)
    fireEvent.click(await screen.findByText('真实演出'))

    expect(taroMocks.navigateTo).toHaveBeenCalledWith({
      url: '/pages/entity-detail/index?entityType=show&entityId=3',
    })
  })

  it('does not navigate when a derived list item has no detail reference', async () => {
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      screen_id: 'S25',
      summary: { title: '财务指标' },
      items: [{
        id: 'finance-profit',
        entity_type: 'finance_metric',
        title: '预计利润',
        status: 'calculated',
        context: { metric: 'profit' },
      }],
    }))

    render(<BlueprintScreen screenId='S25' />)
    fireEvent.click(await screen.findByText('预计利润'))

    expect(taroMocks.navigateTo).not.toHaveBeenCalled()
  })

  it('runs the complete show calculation from the finance screen and stores the returned version', async () => {
    taroMocks.storage.set('starhub-project-id', 42)
    taroMocks.storage.set('starhub-project-draft', {
      name: '测算项目',
      type: 'concert',
      artist_name: '',
      city: '',
      venue: '',
      schedule: '',
      artist_fee: 1800000,
      venue_cost: 700000,
      marketing_cost: 400000,
      production_cost: 900000,
    })
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      screen_id: 'S25',
      summary: { title: '完整演出测算' },
      items: [],
    }))
    taroMocks.calculateShow.mockResolvedValue({ version_id: 88, status: 'calculated' })

    render(<BlueprintScreen screenId='S25' />)
    fireEvent.click(await screen.findByRole('button', { name: '保存并计算三种情景' }))

    await waitFor(() => {
      expect(taroMocks.calculateShow).toHaveBeenCalledWith(expect.objectContaining({
        project_id: 42,
        artist_fee: 1800000,
        venue_cost: 700000,
        marketing_cost: 400000,
        production_cost: 900000,
        tax_fee_rate: 0.06,
        ticketing_fee_rate: 0.04,
      }))
    })
    expect(taroMocks.storage.get('starhub-version-id')).toBe(88)
  })

  it('stores the S52 default project before opening the agent plan', async () => {
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      screen_id: 'S52',
      summary: { title: '今日工作' },
      items: [],
      options: {
        default_project_id: 42,
        available_projects: [{ id: 42, name: '真实项目', status: 'active' }],
      },
    }))

    render(<BlueprintScreen screenId='S52' />)
    await screen.findByText('今日工作')
    fireEvent.click(screen.getByRole('button', { name: '查看今日计划' }))

    expect(taroMocks.storage.get('starhub-project-id')).toBe(42)
    expect(taroMocks.redirectTo).toHaveBeenCalledWith({ url: '/pages/s53/index' })
  })

  it('does not replace an existing project selection with the S52 default', async () => {
    taroMocks.storage.set('starhub-project-id', 99)
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      screen_id: 'S52',
      summary: { title: '今日工作' },
      items: [],
      options: {
        default_project_id: 42,
        available_projects: [{ id: 42, name: '真实项目', status: 'active' }],
      },
    }))

    render(<BlueprintScreen screenId='S52' />)
    await screen.findByText('今日工作')

    expect(taroMocks.storage.get('starhub-project-id')).toBe(99)
  })

  it('renders KPI metric cards on the discovery homepage from real show statuses', async () => {
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      screen_id: 'S04',
      summary: { title: '发现演出' },
      items: [
        { id: 'show-1', entity_type: 'show', title: '售票演出', description: '', status: 'on_sale', context: {} },
        { id: 'show-2', entity_type: 'show', title: '完成案例', description: '', status: 'completed', context: {} },
      ],
    }))

    render(<BlueprintScreen screenId='S04' />)
    await screen.findByText('发现演出')

    expect(screen.getByText('全部演出')).toBeInTheDocument()
    expect(screen.getAllByText('售票中').length).toBe(2)
    expect(screen.getByText('已完成案例')).toBeInTheDocument()
    expect(screen.getByText('待评估机会')).toBeInTheDocument()
  })

  it('renders project portfolio KPI cards on the project tab', async () => {
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      screen_id: 'S10',
      summary: { title: '我的项目' },
      items: [
        { id: 'project-1', entity_type: 'project', title: '已测算项目', description: '', status: 'calculated', context: {} },
        { id: 'project-2', entity_type: 'project', title: '待确认项目', description: '', status: 'pending_confirmation', context: {} },
        { id: 'project-3', entity_type: 'project', title: '归档项目', description: '', status: 'archived', context: {} },
      ],
    }))

    render(<BlueprintScreen screenId='S10' />)
    await screen.findByText('我的项目')

    expect(screen.getByText('全部项目')).toBeInTheDocument()
    expect(screen.getByText('进行中')).toBeInTheDocument()
    expect(screen.getAllByText('已测算').length).toBe(2)
    expect(screen.getAllByText('待确认').length).toBe(2)
  })

  it('renders the S52 work KPI cards from the briefing payload', async () => {
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      screen_id: 'S52',
      summary: { title: '今日工作' },
      items: [],
      options: {
        default_project_id: 42,
        available_projects: [{ id: 42, name: '南京站', status: 'active' }],
        work_briefing: {
          today_change_count: 2,
          active_project_count: 1,
          top_task: { title: '确认场馆报价', status: 'pending', project_name: '南京站' },
        },
      },
    }))

    render(<BlueprintScreen screenId='S52' />)
    await screen.findByText('今日工作')

    expect(screen.getByText('待办任务')).toBeInTheDocument()
    expect(screen.getByText('进行中项目')).toBeInTheDocument()
    expect(screen.getByText('今日首要')).toBeInTheDocument()
    expect(screen.getAllByText('确认场馆报价').length).toBeGreaterThan(0)
  })

  it('uses S52 metric cards as quick entries to the task list and project tab', async () => {
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      screen_id: 'S52',
      summary: { title: '今日工作' },
      items: [],
      options: {
        default_project_id: 42,
        available_projects: [{ id: 42, name: '南京站', status: 'active' }],
        work_briefing: {
          today_change_count: 2,
          active_project_count: 1,
          top_task: { title: '确认场馆报价', status: 'pending', project_name: '南京站' },
        },
      },
    }))

    render(<BlueprintScreen screenId='S52' />)
    await screen.findByText('今日工作')

    fireEvent.click(screen.getByText('待办任务'))
    expect(taroMocks.navigateTo).toHaveBeenCalledWith({ url: '/pages/s55/index' })

    fireEvent.click(screen.getByText('进行中项目'))
    expect(taroMocks.switchTab).toHaveBeenCalledWith({ url: '/pages/s10/index' })

    fireEvent.click(screen.getByText('今日首要'))
    expect(taroMocks.navigateTo).toHaveBeenLastCalledWith({ url: '/pages/s55/index' })
  })

  it('renders the breakeven progress ring and scenario bars on the finance screen', async () => {
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      screen_id: 'S25',
      summary: { title: '三种情况，分别怎么算' },
      items: [],
      options: {
        project: { venue_capacity: 12000 },
        finance_cockpit: {
          status: 'calculated',
          breakeven_attendance: 7581,
          neutral_profit: 1181900,
          missing_fields: [],
          scenarios: {
            conservative: { profit: 128600, attendance: 6500 },
            neutral: { profit: 1181900, attendance: 9600 },
            optimistic: { profit: 2235300, attendance: 11400 },
          },
        },
      },
    }))

    render(<BlueprintScreen screenId='S25' />)
    await screen.findByText('三种情况，分别怎么算')

    expect(screen.getByRole('img', { name: '保本上座率 63%' })).toBeInTheDocument()
    expect(screen.getByText('保本上座率')).toBeInTheDocument()
    expect(screen.getByText('三情景利润对比')).toBeInTheDocument()
    expect(screen.getByText('12.9万')).toBeInTheDocument()
    expect(screen.getByText('118.2万')).toBeInTheDocument()
    expect(screen.getByText('223.5万')).toBeInTheDocument()
  })

  it('does not fabricate a breakeven ring when venue capacity is missing', async () => {
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      screen_id: 'S25',
      summary: { title: '财务测算' },
      items: [],
      options: {
        finance_cockpit: {
          status: 'pending_input',
          breakeven_attendance: null,
          missing_fields: ['expected_attendance'],
          scenarios: {},
        },
      },
    }))

    render(<BlueprintScreen screenId='S25' />)
    await screen.findByText('财务测算')

    expect(screen.queryByRole('img')).not.toBeInTheDocument()
    expect(screen.queryByText('三情景利润对比')).not.toBeInTheDocument()
  })

  it('renders the S64 ticketing progress ring against the neutral forecast', async () => {
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      screen_id: 'S64',
      summary: { title: '售票进度' },
      items: [],
      options: {
        ticketing_loop: {
          forecast_attendance: 8000,
          current_sold_count: 7619,
          attendance_variance: -381,
        },
      },
    }))

    render(<BlueprintScreen screenId='S64' />)
    await screen.findByText('售票进度')

    expect(screen.getByRole('img', { name: '售票进度 · 对比中性预计 95%' })).toBeInTheDocument()
    expect(screen.getByText(/已售 7,619/)).toBeInTheDocument()
    expect(screen.getByText(/偏差 -381/)).toBeInTheDocument()
  })

  it('returns from S52 to the project list when no project is available', async () => {
    taroMocks.getMiniappScreen.mockResolvedValue(response({
      screen_id: 'S52',
      summary: { title: '今日工作' },
      items: [],
      options: {
        default_project_id: null,
        available_projects: [],
      },
    }))

    render(<BlueprintScreen screenId='S52' />)
    await screen.findByText('今日工作')
    fireEvent.click(screen.getByRole('button', { name: '查看今日计划' }))

    expect(taroMocks.switchTab).toHaveBeenCalledWith({ url: '/pages/s10/index' })
    expect(taroMocks.redirectTo).not.toHaveBeenCalledWith({ url: '/pages/s53/index' })
  })
})
