import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import Home from './Home'
import {
  calculateFinance,
  createDecision,
  createProject,
  createTask,
  getDashboardAnalytics,
  getShowRecommendations,
  getTicketingSummary,
  listProjects,
  listShows,
  listTasks,
  shareReport,
  submitTask,
} from '../api'

vi.mock('../api', () => ({
  calculateFinance: vi.fn(),
  createDecision: vi.fn(),
  createProject: vi.fn(),
  createTask: vi.fn(),
  getDashboardAnalytics: vi.fn(),
  getShowRecommendations: vi.fn(),
  getTicketingSummary: vi.fn(),
  listProjects: vi.fn(),
  listShows: vi.fn(),
  listTasks: vi.fn(),
  shareReport: vi.fn(),
  submitTask: vi.fn(),
}))

describe('Home', () => {
  beforeEach(() => {
    getDashboardAnalytics.mockResolvedValue({
      data: {
        data: {
          summary: {
            active_projects: 1,
            calculated_projects: 1,
            pending_confirmation_projects: 0,
            pending_tasks: 1,
            reservations: 42,
            on_sale_shows: 3,
            neutral_profit_total: 270000,
            evidence_count: 8,
            external_jobs: 5,
          },
          metrics: [],
        },
      },
    })
    getTicketingSummary.mockResolvedValue({
      data: {
        data: {
          summary: {
            total_shows: 3,
            on_sale_shows: 3,
            reservation_count: 42,
          },
          shows: [
            { id: 1, title: '周杰伦·北京演唱会', city: '北京', status: 'on_sale', reservation_count: 42 },
          ],
          orders: [],
        },
      },
    })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('shows a visible error when show data cannot be loaded', async () => {
    getShowRecommendations.mockRejectedValue(new Error('offline'))
    listShows.mockRejectedValue(new Error('offline'))

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Home role="C" currentUser={{ phone: '13800000000' }} />
      </MemoryRouter>,
    )

    expect(await screen.findByText('演出数据暂时不可用')).toBeInTheDocument()
  })

  it('shows personalized recommendations for audience users from order history', async () => {
    getShowRecommendations.mockResolvedValue({
      data: {
        data: [
          {
            id: 8,
            title: '周杰伦·上海加场',
            artist_name: '周杰伦',
            city: '上海',
            venue: '上海体育场',
            date: '2026-10-01',
            price: '580-1580',
            status: 'on_sale',
            poster_url: 'https://oss.example.com/posters/jay-shanghai.jpg',
            recommendation_reason: '你预约过周杰伦相关演出',
          },
        ],
      },
    })

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Home role="C" currentUser={{ phone: '13800000000' }} />
      </MemoryRouter>,
    )

    expect(await screen.findByText('为你推荐')).toBeInTheDocument()
    expect(screen.getByText('周杰伦·上海加场')).toBeInTheDocument()
    expect(screen.getByAltText('周杰伦·上海加场现场')).toHaveAttribute('src', 'https://oss.example.com/posters/jay-shanghai.jpg')
    expect(screen.getByText('你预约过周杰伦相关演出')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: '生成专属推荐' })).not.toBeInTheDocument()
    expect(getShowRecommendations).toHaveBeenCalledWith('13800000000')
    expect(listShows).not.toHaveBeenCalled()
  })

  it('loads Phase 1 projects and tasks for the business workbench', async () => {
    listProjects.mockResolvedValue({
      data: {
        data: [
          {
            id: 1,
            name: '北京大型演唱会测算',
            artist_name: '周杰伦',
            city: '北京',
            venue: '国家体育场',
            status: 'calculated',
            current_version_id: 2,
          },
        ],
      },
    })
    listTasks.mockResolvedValue({
      data: {
        data: [
          {
            id: 1,
            project_id: 1,
            title: '确认场地安全资料',
            status: 'pending',
            due_date: '2026-08-01',
            description: '补齐场地方安全承诺与消防批复',
            result: '',
            evidence_ids: [9, 10],
          },
        ],
      },
    })

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Home role="B" />
      </MemoryRouter>,
    )

    expect(await screen.findByText('北京大型演唱会测算')).toBeInTheDocument()
    expect(screen.getAllByText('确认场地安全资料').length).toBeGreaterThanOrEqual(2)
    expect(document.querySelector('.task-panel-icon')).not.toBeInTheDocument()
    expect(screen.getByText('日程与待办')).toBeInTheDocument()
    expect(screen.getByText('团队动态')).toBeInTheDocument()
    expect(screen.getByText('北京大型演唱会测算 · 截止 2026-08-01')).toBeInTheDocument()
    expect(screen.getByText('补齐场地方安全承诺与消防批复')).toBeInTheDocument()
    expect(screen.getAllByText('待处理').length).toBe(2)
    expect(screen.getByText('证据 2 份')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '查看项目' })).toHaveAttribute('href', '/projects/1')
    expect(listProjects).toHaveBeenCalled()
    expect(listTasks).toHaveBeenCalled()
    expect(getDashboardAnalytics).toHaveBeenCalled()
    expect(getTicketingSummary).toHaveBeenCalled()
    expect(screen.getByText('中性利润合计')).toBeInTheDocument()
    expect(screen.getByText('¥270,000')).toBeInTheDocument()
    expect(screen.getByText('预约人数')).toBeInTheDocument()
    expect(screen.getByText('42 人')).toBeInTheDocument()
    expect(screen.getByText('票务预约汇总')).toBeInTheDocument()

    expect(screen.getByText('项目推进')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: '任务完成率 0%' })).toBeInTheDocument()
    expect(screen.getByText('已完成 0 / 共 1 项任务')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: '测算覆盖率 100%' })).toBeInTheDocument()
    expect(screen.getByText('项目状态分布')).toBeInTheDocument()
    expect(screen.getAllByText('已测算').length).toBe(2)
    expect(screen.queryByText('推进中 / 草稿')).not.toBeInTheDocument()
  })

  it('renders quick action cards that open modules and focus the create form', async () => {
    const user = userEvent.setup()
    listProjects.mockResolvedValue({ data: { data: [] } })
    listTasks.mockResolvedValue({ data: { data: [] } })

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Home role="B" />
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: '艺人智策' })).toBeInTheDocument()
    const moduleLinks = screen.getAllByRole('link', { name: /进入模块/ })
    expect(moduleLinks[0]).toHaveAttribute('href', '/artist')
    expect(moduleLinks[1]).toHaveAttribute('href', '/generate')
    await user.click(screen.getByRole('button', { name: /填写项目信息/ }))
    expect(screen.getByLabelText('项目名称')).toHaveFocus()
  })

  it('opens the project more-menu and shares the project report', async () => {
    const user = userEvent.setup()
    shareReport.mockResolvedValue({
      data: { data: { share_url: '/shared/reports/abc123', expires_in_days: 7 } },
    })
    listProjects.mockResolvedValue({
      data: {
        data: [{
          id: 1,
          name: '北京大型演唱会测算',
          artist_name: '周杰伦',
          city: '北京',
          venue: '国家体育场',
          status: 'calculated',
        }],
      },
    })
    listTasks.mockResolvedValue({ data: { data: [] } })

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Home role="B" />
      </MemoryRouter>,
    )

    await screen.findByText('北京大型演唱会测算')
    await user.click(screen.getByRole('button', { name: '北京大型演唱会测算更多操作' }))

    expect(screen.getByRole('menuitem', { name: '查看详情' })).toHaveAttribute('href', '/projects/1')
    await user.click(screen.getByRole('menuitem', { name: '分享报告' }))

    await waitFor(() => {
      expect(shareReport).toHaveBeenCalledWith(1, { expires_in_days: 7 })
    })
    expect(await screen.findByText(/报告分享链接已生成/)).toBeInTheDocument()
  })

  it('closes the project more-menu when clicking outside', async () => {
    const user = userEvent.setup()
    listProjects.mockResolvedValue({
      data: {
        data: [{ id: 1, name: '北京大型演唱会测算', status: 'draft' }],
      },
    })
    listTasks.mockResolvedValue({ data: { data: [] } })

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Home role="B" />
      </MemoryRouter>,
    )

    await screen.findByText('北京大型演唱会测算')
    await user.click(screen.getByRole('button', { name: '北京大型演唱会测算更多操作' }))
    expect(screen.getByRole('menu')).toBeInTheDocument()

    await user.click(document.body)
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })

  it('checks off a pending task with a result and moves it into the completed group', async () => {
    const user = userEvent.setup()
    listProjects.mockResolvedValue({
      data: {
        data: [{
          id: 1,
          name: '北京大型演唱会测算',
          artist_name: '周杰伦',
          city: '北京',
          venue: '国家体育场',
          status: 'calculated',
        }],
      },
    })
    listTasks.mockResolvedValue({
      data: {
        data: [{
          id: 11,
          project_id: 1,
          title: '确认场地安全资料',
          description: '补齐场地方安全承诺',
          status: 'pending',
          due_date: '2026-08-01',
        }],
      },
    })
    submitTask.mockResolvedValue({
      data: {
        data: {
          id: 11,
          project_id: 1,
          title: '确认场地安全资料',
          description: '补齐场地方安全承诺',
          status: 'submitted',
          due_date: '2026-08-01',
          result: '资料已上传',
        },
      },
    })

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Home role="B" />
      </MemoryRouter>,
    )

    await screen.findByText('日程与待办')
    expect(screen.getByText('已完成 0 / 共 1 项任务')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '标记「确认场地安全资料」完成' }))

    const resultInput = screen.getByLabelText('确认场地安全资料完成结果')
    await user.type(resultInput, '资料已上传')
    await user.click(screen.getByRole('button', { name: '提交完成' }))

    await waitFor(() => {
      expect(submitTask).toHaveBeenCalledWith(11, { result: '资料已上传', evidence_ids: [] })
    })
    expect(await screen.findByText('任务「确认场地安全资料」已提交，等待负责人核验。')).toBeInTheDocument()
    expect(screen.getByText('已完成 1 / 共 1 项任务')).toBeInTheDocument()
  })

  it('keeps showing projects when dashboard or ticketing summary is unavailable', async () => {
    listProjects.mockResolvedValue({
      data: {
        data: [
          {
            id: 1,
            name: '北京大型演唱会测算',
            artist_name: '周杰伦',
            city: '北京',
            venue: '国家体育场',
            status: 'calculated',
            current_version_id: 2,
          },
        ],
      },
    })
    listTasks.mockResolvedValue({ data: { data: [] } })
    getDashboardAnalytics.mockRejectedValue(new Error('not found'))
    getTicketingSummary.mockRejectedValue(new Error('not found'))

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Home role="B" />
      </MemoryRouter>,
    )

    expect(await screen.findByText('北京大型演唱会测算')).toBeInTheDocument()
    expect(screen.queryByText('项目数据暂时不可用')).not.toBeInTheDocument()
    expect(screen.getByText('票务预约汇总')).toBeInTheDocument()
  })

  it('renders task project name from the task API payload instead of relying on the project list', async () => {
    listProjects.mockResolvedValue({ data: { data: [] } })
    listTasks.mockResolvedValue({
      data: {
        data: [
          {
            id: 9,
            project_id: 88,
            project_name: '数据库真实项目',
            assignee_name: '超级管理员',
            title: '确认艺人授权',
            description: '补齐授权书与宣发素材许可范围',
            due_date: '2026-09-30',
            status: 'pending',
            result: '',
            evidence_ids: [1, 2, 3],
            evidence_count: 3,
          },
        ],
      },
    })

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Home role="B" />
      </MemoryRouter>,
    )

    await screen.findByText('日程与待办')
    expect(screen.getAllByText('确认艺人授权').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('数据库真实项目 · 截止 2026-09-30')).toBeInTheDocument()
    expect(screen.getByText('补齐授权书与宣发素材许可范围')).toBeInTheDocument()
    expect(screen.getByText('证据 3 份')).toBeInTheDocument()
    expect(screen.getAllByTitle('超级管理员').length).toBeGreaterThanOrEqual(2)
  })

  it('creates a Phase 1 project from the business workbench', async () => {
    const user = userEvent.setup()
    listProjects.mockResolvedValue({ data: { data: [] } })
    listTasks.mockResolvedValue({ data: { data: [] } })
    createProject.mockResolvedValue({
      data: {
        data: {
          id: 2,
          name: '上海巡演项目',
          artist_name: '五月天',
          city: '上海',
          venue: '梅赛德斯-奔驰文化中心',
          status: 'draft',
        },
      },
    })

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Home role="B" />
      </MemoryRouter>,
    )

    const createForm = screen.getByRole('button', { name: '创建项目' }).closest('form')
    expect(createForm).toHaveClass('project-create-form')
    expect(createForm).not.toHaveClass('generator-form')

    await user.type(screen.getByLabelText('项目名称'), '上海巡演项目')
    await user.type(screen.getByLabelText('艺人'), '五月天')
    await user.type(screen.getByLabelText('城市'), '上海')
    await user.type(screen.getByLabelText('场馆'), '梅赛德斯-奔驰文化中心')
    await user.click(screen.getByRole('button', { name: '创建项目' }))

    await waitFor(() => {
      expect(createProject).toHaveBeenCalledWith(expect.objectContaining({
        name: '上海巡演项目',
        artist_name: '五月天',
        city: '上海',
        venue: '梅赛德斯-奔驰文化中心',
      }))
    })
    expect(await screen.findByText('上海巡演项目')).toBeInTheDocument()
  })

  it('calculates finance and submits an advance decision for a project', async () => {
    const user = userEvent.setup()
    listProjects.mockResolvedValue({
      data: {
        data: [
          {
            id: 1,
            name: '北京大型演唱会测算',
            artist_name: '周杰伦',
            city: '北京',
            venue: '国家体育场',
            status: 'draft',
            current_version_id: 1,
            expected_attendance: 48000,
            avg_ticket_price: 680,
            artist_fee: 12000000,
            venue_cost: 3600000,
            marketing_cost: 1800000,
            production_cost: 5200000,
          },
        ],
      },
    })
    listTasks.mockResolvedValue({ data: { data: [] } })
    calculateFinance.mockResolvedValue({
      data: {
        data: {
          version_id: 2,
          project_status: 'calculated',
          scenarios: {
            neutral: {
              revenue: 32640000,
              profit: 10040000,
            },
          },
          breakeven_attendance: 33236,
        },
      },
    })
    createDecision.mockResolvedValue({
      data: {
        data: {
          id: 8,
          project_id: 1,
          version_id: 2,
          decision_type: 'advance',
          conditions: '完成政策审批、场地安全、艺人授权与资金合同确认后推进。',
          project_status: 'pending_confirmation',
        },
      },
    })
    createTask.mockResolvedValue({
      data: {
        data: {
          id: 11,
          project_id: 1,
          title: '发起政策审批',
          description: '基于推进决策 V2，确认政策审批材料、申报路径和责任人。',
          status: 'pending',
          due_date: '',
        },
      },
    })

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Home role="B" />
      </MemoryRouter>,
    )

    expect(await screen.findByText('北京大型演唱会测算')).toBeInTheDocument()
    const financeButton = screen.getByRole('button', { name: '计算盈亏' })
    const decisionButton = screen.getByRole('button', { name: '提交推进决策' })
    expect(financeButton.closest('.project-row-actions')).toBeInTheDocument()
    expect(decisionButton.closest('.project-row-actions')).toBeInTheDocument()
    expect(financeButton.closest('.project-list-row')).toContainElement(decisionButton)

    await user.click(financeButton)

    await waitFor(() => {
      expect(calculateFinance).toHaveBeenCalledWith(expect.objectContaining({ project_id: 1 }))
    })
    expect(await screen.findByText('测算结果')).toBeInTheDocument()
    expect(screen.getByText('中性收入')).toBeInTheDocument()
    expect(screen.getByText('¥32,640,000')).toBeInTheDocument()
    expect(await screen.findByText('中性利润 ¥10,040,000')).toBeInTheDocument()
    expect(screen.getByText('保本人数 33,236')).toBeInTheDocument()
    expect(screen.getByText('测算版本')).toBeInTheDocument()
    expect(screen.getAllByText('V2').length).toBeGreaterThan(0)

    await user.click(decisionButton)

    await waitFor(() => {
      expect(createDecision).toHaveBeenCalledWith({
        project_id: 1,
        version_id: 2,
        decision_type: 'advance',
        conditions: '完成政策审批、场地安全、艺人授权与资金合同确认后推进。',
      })
    })
    expect(await screen.findByText('已提交推进决策')).toBeInTheDocument()
    expect(screen.getByText('推进结果')).toBeInTheDocument()
    expect(screen.getByText('决策状态')).toBeInTheDocument()
    expect(screen.getAllByText('待确认').length).toBeGreaterThan(0)
    expect(screen.getByText('推进条件')).toBeInTheDocument()
    expect(screen.getByText('完成政策审批、场地安全、艺人授权与资金合同确认后推进。')).toBeInTheDocument()
    expect(screen.getByText('下一步操作')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '发起政策审批' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '确认场地安全' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '确认艺人授权' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '确认资金合同' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '发起政策审批' }))

    await waitFor(() => {
      expect(createTask).toHaveBeenCalledWith({
        project_id: 1,
        title: '发起政策审批',
        description: '基于推进决策 V2，确认政策审批材料、申报路径和责任人。',
      })
    })
    expect(await screen.findByText('发起政策审批')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '已安排' })).toBeDisabled()
  })

  it('does not create duplicate next-step tasks after an advance decision', async () => {
    const user = userEvent.setup()
    listProjects.mockResolvedValue({
      data: {
        data: [
          {
            id: 3,
            name: '广州巡演推进',
            artist_name: '林俊杰',
            city: '广州',
            venue: '广州体育馆',
            status: 'calculated',
            current_version_id: 7,
            expected_attendance: 12000,
            avg_ticket_price: 580,
            artist_fee: 6000000,
            venue_cost: 1000000,
            marketing_cost: 800000,
            production_cost: 1200000,
          },
        ],
      },
    })
    listTasks.mockResolvedValue({
      data: {
        data: [
          { id: 31, project_id: 3, title: '确认场地安全', status: 'pending', due_date: '' },
        ],
      },
    })
    createDecision.mockResolvedValue({
      data: {
        data: {
          id: 18,
          project_id: 3,
          version_id: 7,
          decision_type: 'advance',
          conditions: '完成政策审批、场地安全、艺人授权与资金合同确认后推进。',
          project_status: 'pending_confirmation',
        },
      },
    })

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Home role="B" />
      </MemoryRouter>,
    )

    expect(await screen.findByText('广州巡演推进')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '提交推进决策' }))

    const scheduledButtons = await screen.findAllByRole('button', { name: '已安排' })
    expect(scheduledButtons.length).toBe(1)
    expect(screen.getByText('确认场地安全')).toBeInTheDocument()
    await user.click(scheduledButtons[0])
    expect(createTask).not.toHaveBeenCalled()
  })

  it('does not show zero finance results when required calculation inputs are missing', async () => {
    const user = userEvent.setup()
    listProjects.mockResolvedValue({
      data: {
        data: [
          {
            id: 9,
            name: '赵雅芝大秀市场分析',
            artist_name: '赵雅芝',
            city: '待定',
            venue: '待定',
            status: 'draft',
            current_version_id: 14,
          },
        ],
      },
    })
    listTasks.mockResolvedValue({ data: { data: [] } })
    calculateFinance.mockResolvedValue({
      data: {
        data: {
          version_id: 15,
          project_status: 'draft',
          status: 'pending_input',
          missing_fields: ['expected_attendance', 'avg_ticket_price', 'artist_fee', 'venue_cost', 'marketing_cost', 'production_cost'],
          scenarios: {},
          breakeven_attendance: null,
          total_cost: null,
        },
      },
    })

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Home role="B" />
      </MemoryRouter>,
    )

    expect(await screen.findByText('赵雅芝大秀市场分析')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '计算盈亏' }))

    expect(await screen.findByText('待补齐真实测算参数')).toBeInTheDocument()
    expect(screen.getByText('预计人数、平均票价、艺人费、场地成本、宣发成本、制作成本')).toBeInTheDocument()
    expect(screen.queryByText('¥0')).not.toBeInTheDocument()
  })

  it('does not render user management inside the business workbench', async () => {
    listProjects.mockResolvedValue({ data: { data: [] } })
    listTasks.mockResolvedValue({ data: { data: [] } })

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Home role="B" currentUser={{ account: 'root', group_code: 'root', can_manage_users: true }} />
      </MemoryRouter>,
    )

    expect(await screen.findByText('项目决策工作台')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: '用户管理' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '添加用户' })).not.toBeInTheDocument()
  })
})
