import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import AdminWorkspace from './AdminWorkspace'
import BusinessWorkspace from './BusinessWorkspace'
import BrandWorkspace from './BrandWorkspace'
import GovernmentWorkspace from './GovernmentWorkspace'
import AudienceWorkspace from './AudienceWorkspace'
import InvestorWorkspace from './InvestorWorkspace'
import ArtistWorkspace from './ArtistWorkspace'
import { getAdminWorkspace, getBrandWorkspace, getAudienceWorkspace } from '../api'

const payload = { projects: [
  { id: 1, name: '上海现场', city: '上海', artist_name: '甲', evidence: { total: 1, pending: 1 }, risks: [], gates: [], facts: [] },
  { id: 2, name: '北京现场', city: '北京', artist_name: '乙', evidence: { total: 0, pending: 0 }, risks: [], gates: [], facts: [] },
], personal: { tasks: [{ id: 1, title: '我的核验', status: 'pending' }], notifications: [{ id: 1, title: '我的消息', status: 'unread' }] },
  summary: { users: 0, projects: 2, sources: 0, quality_issues: 0 }, sources: [], jobs: [], venues: [],
  shows: [{ id: 1, title: '上海演出', city: '上海', artist_name: '甲' }, { id: 2, title: '北京演出', city: '北京', artist_name: '乙' }],
  reservations: [{ id: 3, show: { id: 1, title: '我的预约现场', city: '上海' } }],
}
vi.mock('../api', () => ({
  getAdminWorkspace: vi.fn(async () => ({ data: { data: payload } })),
  getBusinessWorkspace: vi.fn(async () => ({ data: { data: payload } })),
  getBrandWorkspace: vi.fn(async () => ({ data: { data: payload } })),
  getGovernmentWorkspace: vi.fn(async () => ({ data: { data: payload } })),
  getAudienceWorkspace: vi.fn(async () => ({ data: { data: payload } })),
  getInvestorWorkspace: vi.fn(async () => ({ data: { data: payload } })),
  getArtistWorkspace: vi.fn(async () => ({ data: { data: payload } })),
}))
afterEach(() => { cleanup(); vi.clearAllMocks() })
const mount = element => render(<MemoryRouter>{element}</MemoryRouter>)

it.each([
  [AdminWorkspace, '平台管理工作台'], [BusinessWorkspace, '主办方经营工作台'],
  [BrandWorkspace, '品牌合作工作台'], [GovernmentWorkspace, '城市文旅工作台'], [AudienceWorkspace, '我的现场'],
  [InvestorWorkspace, '投资评估概览'], [ArtistWorkspace, '我的演出工作台'],
])('renders a distinct homepage with personal inbox', async (Component, title) => {
  mount(<Component />)
  expect(await screen.findByRole('heading', { name: title })).toBeInTheDocument()
  expect(screen.getByText('我的核验')).toBeInTheDocument()
  expect(screen.getByText('我的消息')).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: '工作流程' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: '待我处理 · 1' })).toBeInTheDocument()
  const tasks = screen.getByRole('heading', { name: '我的待办与消息' }).closest('section')
  expect(tasks.previousElementSibling).toHaveClass('page-lead')
})

it('filters government projects by city and distinguishes impact from attendance', async () => {
  mount(<GovernmentWorkspace mode="impact" />)
  await screen.findByText('上海现场')
  await userEvent.selectOptions(screen.getByLabelText('选择城市'), '上海')
  expect(screen.queryByText('北京现场')).not.toBeInTheDocument()
  expect(screen.getByText(/消费金额.*待接入/)).toBeInTheDocument()
})

it('changes brand evidence requirements without inventing ROI', async () => {
  mount(<BrandWorkspace mode="evidence" />)
  await screen.findByText('上海现场')
  await userEvent.selectOptions(screen.getByLabelText('合作目标'), 'conversion')
  expect(screen.getByText(/转化归因.*核销/)).toBeInTheDocument()
  expect(screen.queryByText('3.8')).not.toBeInTheDocument()
})

it('searches audience discovery and lists only owned reservations', async () => {
  const view = mount(<AudienceWorkspace mode="discover" />)
  await screen.findByText('上海演出')
  await userEvent.type(screen.getByLabelText('搜索演出、艺人或城市'), '北京')
  expect(screen.queryByText('上海演出')).not.toBeInTheDocument()
  expect(screen.getByText('北京演出')).toBeInTheDocument()
  view.unmount()
  mount(<AudienceWorkspace mode="reservations" />)
  expect(await screen.findByText('我的预约现场')).toBeInTheDocument()
  expect(screen.getByText(/预约登记.*购票/)).toBeInTheDocument()
})

it('retries failed workspace requests', async () => {
  getBrandWorkspace.mockRejectedValueOnce(new Error('offline'))
  mount(<BrandWorkspace />)
  await screen.findByText('工作台数据暂时不可用')
  await userEvent.click(screen.getByRole('button', { name: '重试' }))
  expect(await screen.findByRole('heading', { name: '品牌合作工作台' })).toBeInTheDocument()
})
it('shows cancelled reservation status on the existing audience page', async () => {
  getAudienceWorkspace.mockResolvedValueOnce({ data: { data: { ...payload, reservations: [{ id: 3, status: 'cancelled', show: { id: 1, title: '取消后的现场' } }] } } })
  mount(<AudienceWorkspace mode="reservations" />)
  expect(await screen.findByText('取消后的现场')).toBeInTheDocument()
  expect(screen.getByText('已取消登记')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: '管理登记与查看历史' })).toHaveAttribute('href', '/collaboration')
})

it('keeps the admin overview compact when many collection jobs exist', async () => {
  getAdminWorkspace.mockResolvedValueOnce({ data: { data: { ...payload, jobs: Array.from({ length: 30 }, (_, i) => ({
    id: i, purpose: `任务${i}`, status: 'queued',
  })) } } })
  mount(<AdminWorkspace />)
  const recent = (await screen.findByRole('heading', { name: '近期采集任务' })).closest('section')
  expect(recent).toHaveTextContent('任务0')
  expect(screen.getByText('任务4')).toBeInTheDocument()
  expect(screen.queryByText('任务5')).not.toBeInTheDocument()
  expect(screen.getByText('共 30 项 · 展示最近 5 项')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: '查看接入详情' })).toHaveAttribute('href', '/admin/data')
})
