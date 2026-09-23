import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import Home from './Home'
import { calculateFinance, createDecision, createProject, listProjects, listShows, listTasks } from '../api'

vi.mock('../api', () => ({
  calculateFinance: vi.fn(),
  createDecision: vi.fn(),
  createProject: vi.fn(),
  listProjects: vi.fn(),
  listShows: vi.fn(),
  listTasks: vi.fn(),
}))

describe('Home', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('shows a visible error when show data cannot be loaded', async () => {
    listShows.mockRejectedValue(new Error('offline'))

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Home role="C" />
      </MemoryRouter>,
    )

    expect(await screen.findByText('演出数据暂时不可用')).toBeInTheDocument()
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
    expect(screen.getByText('确认场地安全资料')).toBeInTheDocument()
    expect(listProjects).toHaveBeenCalled()
    expect(listTasks).toHaveBeenCalled()
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
          project_id: 1,
          version_id: 2,
          decision_type: 'advance',
          project_status: 'pending_confirmation',
        },
      },
    })

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Home role="B" />
      </MemoryRouter>,
    )

    expect(await screen.findByText('北京大型演唱会测算')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '计算盈亏' }))

    await waitFor(() => {
      expect(calculateFinance).toHaveBeenCalledWith(expect.objectContaining({ project_id: 1 }))
    })
    expect(await screen.findByText('中性利润 ¥10,040,000')).toBeInTheDocument()
    expect(screen.getByText('保本人数 33,236')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '提交推进决策' }))

    await waitFor(() => {
      expect(createDecision).toHaveBeenCalledWith({
        project_id: 1,
        version_id: 2,
        decision_type: 'advance',
        conditions: '完成政策审批、场地安全、艺人授权与资金合同确认后推进。',
      })
    })
    expect(await screen.findByText('已提交推进决策')).toBeInTheDocument()
  })
})
