import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { BrowserRouter } from 'react-router-dom'

import App from '../App'
import {
  agentChat,
  createAssumption,
  createEvidence,
  createFact,
  createGate,
  createRisk,
  createProject,
  createUser,
  deleteUser,
  generateAI,
  getProject,
  getShow,
  listAssumptions,
  listEvidences,
  listFacts,
  listGates,
  listProjectVersions,
  listProjects,
  listRisks,
  listShows,
  listTasks,
  listUsers,
  mockOrder,
  searchArtist,
  searchCases,
  shareReport,
  submitTask,
  updateUser,
  verifyFact,
  webLogin,
} from '../api'

vi.mock('../api', () => ({
  agentChat: vi.fn(),
  createAssumption: vi.fn(),
  createEvidence: vi.fn(),
  createFact: vi.fn(),
  createGate: vi.fn(),
  createProject: vi.fn(),
  createRisk: vi.fn(),
  createUser: vi.fn(),
  deleteUser: vi.fn(),
  generateAI: vi.fn(),
  getProject: vi.fn(),
  getShow: vi.fn(),
  listAssumptions: vi.fn(),
  listEvidences: vi.fn(),
  listFacts: vi.fn(),
  listGates: vi.fn(),
  listProjectVersions: vi.fn(),
  listProjects: vi.fn(),
  listRisks: vi.fn(),
  listShows: vi.fn(),
  listTasks: vi.fn(),
  listUsers: vi.fn(),
  mockOrder: vi.fn(),
  searchArtist: vi.fn(),
  searchCases: vi.fn(),
  shareReport: vi.fn(),
  submitTask: vi.fn(),
  updateUser: vi.fn(),
  verifyFact: vi.fn(),
  webLogin: vi.fn(),
}))

function renderProjectDetail() {
  window.history.pushState({}, '', '/projects/1')
  return render(
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <App />
    </BrowserRouter>,
  )
}

describe('ProjectDetail', () => {
  beforeEach(() => {
    localStorage.setItem('starhub-login', 'true')
    localStorage.setItem('starhub-role', 'B')
    localStorage.setItem('starhub-user', JSON.stringify({ account: 'root', role: 'B', group_code: 'root', can_manage_users: true }))
    createProject.mockResolvedValue({ data: { data: {} } })
    createUser.mockResolvedValue({ data: { data: {} } })
    deleteUser.mockResolvedValue({ data: { data: {} } })
    generateAI.mockResolvedValue({ data: { data: { result: '' } } })
    getShow.mockResolvedValue({ data: { data: {} } })
    listProjects.mockResolvedValue({ data: { data: [] } })
    listShows.mockResolvedValue({ data: { data: [] } })
    listUsers.mockResolvedValue({ data: { data: [] } })
    mockOrder.mockResolvedValue({ data: { data: {} } })
    searchArtist.mockResolvedValue({ data: { data: [] } })
    updateUser.mockResolvedValue({ data: { data: {} } })
    webLogin.mockResolvedValue({ data: { data: {} } })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('loads project decision materials and supports the main web completion actions', async () => {
    const user = userEvent.setup()
    getProject.mockResolvedValue({
      data: {
        data: {
          id: 1,
          name: '北京大型演唱会测算',
          artist_name: '周杰伦',
          city: '北京',
          venue: '国家体育场',
          status: 'calculated',
          current_version_id: 2,
          current_version: {
            id: 2,
            version_no: 2,
            status: 'calculated',
            finance_result: {
              total_cost: 22600000,
              breakeven_attendance: 33236,
              scenarios: {
                neutral: { revenue: 32640000, profit: 10040000 },
              },
            },
          },
        },
      },
    })
    listProjectVersions.mockResolvedValue({
      data: { data: [{ id: 1, version_no: 1, status: 'draft' }, { id: 2, version_no: 2, status: 'calculated' }] },
    })
    listFacts.mockResolvedValue({
      data: { data: [{ id: 7, title: '艺人档期已确认', content: '经纪团队邮件确认', source: '邮件', status: 'pending' }] },
    })
    listEvidences.mockResolvedValue({
      data: { data: [{ id: 9, name: '场馆报价单', file_url: 'https://example.com/quote.pdf', evidence_type: 'document', source: '场馆' }] },
    })
    listAssumptions.mockResolvedValue({
      data: { data: [{ id: 3, title: '上座率假设', content: '中性预计 85%', confidence: 80, status: 'active' }] },
    })
    listGates.mockResolvedValue({
      data: { data: [{ id: 4, name: '安全审批', status: 'pending', required_evidence: '审批回执', owner_group: 'G' }] },
    })
    listRisks.mockResolvedValue({
      data: { data: [{ id: 5, title: '天气影响入场', level: 'medium', mitigation: '加开接驳', status: 'open' }] },
    })
    listTasks.mockResolvedValue({
      data: { data: [{ id: 6, title: '补充安保方案', description: '提交给场地方', status: 'pending', due_date: '2026-08-01' }] },
    })
    createFact.mockResolvedValue({ data: { data: { id: 8, title: '票务通道确认', content: '已完成压测', source: '票务系统', status: 'pending' } } })
    verifyFact.mockResolvedValue({ data: { data: { id: 7, title: '艺人档期已确认', content: '经纪团队邮件确认', source: '邮件', status: 'verified' } } })
    createEvidence.mockResolvedValue({ data: { data: { id: 10, name: '批复文件', file_url: 'https://example.com/approval.pdf', evidence_type: 'document', source: '文旅局' } } })
    createAssumption.mockResolvedValue({ data: { data: { id: 11, title: '二开票假设', content: '追加 5000 张', confidence: 65, status: 'active' } } })
    createGate.mockResolvedValue({ data: { data: { id: 12, name: '消防验收', status: 'pending', required_evidence: '验收文件', owner_group: 'G' } } })
    createRisk.mockResolvedValue({ data: { data: { id: 13, title: '交通拥堵', level: 'high', mitigation: '错峰入场', status: 'open' } } })
    submitTask.mockResolvedValue({ data: { data: { id: 6, title: '补充安保方案', status: 'submitted', result: '已提交材料' } } })
    agentChat.mockResolvedValue({ data: { data: { answer: '建议先完成安全审批并锁定交通方案。' } } })
    searchCases.mockResolvedValue({ data: { data: [{ project_id: 2, name: '上海体育场项目', artist_name: '五月天', city: '上海', venue: '上海体育场', status: 'calculated' }] } })
    shareReport.mockResolvedValue({ data: { data: { share_url: '/shared/reports/abc123', token: 'abc123', expires_in_days: 7 } } })

    renderProjectDetail()

    expect(await screen.findByRole('heading', { name: '北京大型演唱会测算' })).toBeInTheDocument()
    expect(screen.getByText('中性利润 ¥10,040,000')).toBeInTheDocument()
    expect(screen.getByText('艺人档期已确认')).toBeInTheDocument()
    expect(screen.getByText('场馆报价单')).toBeInTheDocument()
    expect(screen.getByText('安全审批')).toBeInTheDocument()
    expect(screen.getByText('天气影响入场')).toBeInTheDocument()

    await user.type(screen.getByLabelText('事实标题'), '票务通道确认')
    await user.type(screen.getByLabelText('事实内容'), '已完成压测')
    await user.type(screen.getByLabelText('事实来源'), '票务系统')
    await user.click(screen.getByRole('button', { name: '添加事实' }))
    expect(await screen.findByText('票务通道确认')).toBeInTheDocument()
    expect(createFact).toHaveBeenCalledWith({ project_id: 1, title: '票务通道确认', content: '已完成压测', source: '票务系统' })

    await user.click(screen.getAllByRole('button', { name: '核验通过' }).at(-1))
    await waitFor(() => expect(verifyFact).toHaveBeenCalledWith(7, { status: 'verified', comment: 'Web 端核验通过' }))

    await user.type(screen.getByLabelText('证据名称'), '批复文件')
    await user.type(screen.getByLabelText('证据链接'), 'https://example.com/approval.pdf')
    await user.click(screen.getByRole('button', { name: '上传证据' }))
    expect(await screen.findByText('批复文件')).toBeInTheDocument()

    await user.type(screen.getByLabelText('假设标题'), '二开票假设')
    await user.type(screen.getByLabelText('假设说明'), '追加 5000 张')
    await user.click(screen.getByRole('button', { name: '添加假设' }))
    expect(await screen.findByText('二开票假设')).toBeInTheDocument()

    await user.type(screen.getByLabelText('关卡名称'), '消防验收')
    await user.type(screen.getByLabelText('所需证据'), '验收文件')
    await user.click(screen.getByRole('button', { name: '添加关卡' }))
    expect(await screen.findByText('消防验收')).toBeInTheDocument()

    await user.type(screen.getByLabelText('风险标题'), '交通拥堵')
    await user.type(screen.getByLabelText('缓释方案'), '错峰入场')
    await user.click(screen.getByRole('button', { name: '添加风险' }))
    expect(await screen.findByText('交通拥堵')).toBeInTheDocument()

    await user.type(screen.getByLabelText('任务提交结果'), '已提交材料')
    await user.click(screen.getByRole('button', { name: '提交任务' }))
    await waitFor(() => expect(submitTask).toHaveBeenCalledWith(6, { result: '已提交材料', evidence_ids: [] }))
    expect(await screen.findByText('已提交材料')).toBeInTheDocument()

    await user.type(screen.getByLabelText('向智能体提问'), '下一步先处理什么')
    await user.click(screen.getByRole('button', { name: '询问智能体' }))
    expect(await screen.findByText('建议先完成安全审批并锁定交通方案。')).toBeInTheDocument()

    await user.type(screen.getByLabelText('案例搜索'), '上海')
    await user.click(screen.getByRole('button', { name: '搜索案例' }))
    expect(await screen.findByText('上海体育场项目')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '生成分享链接' }))
    expect(await screen.findByText('/shared/reports/abc123')).toBeInTheDocument()
  })
})
