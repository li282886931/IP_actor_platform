import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, it, expect, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import InvestorWorkspace from './InvestorWorkspace'
import ArtistWorkspace from './ArtistWorkspace'
import { getInvestorWorkspace, getArtistWorkspace } from '../api'

vi.mock('../api', () => ({ getInvestorWorkspace: vi.fn(), getArtistWorkspace: vi.fn() }))
afterEach(() => { cleanup(); vi.clearAllMocks() })
const renderPage = (element) => render(<MemoryRouter>{element}</MemoryRouter>)

it('shows saved finance including zero and filters projects without simulated returns', async () => {
  const user = userEvent.setup()
  getInvestorWorkspace.mockResolvedValue({ data: { data: { projects: [
    { id: 1, name: '北京音乐会', city: '北京', version: { version_no: 2, finance_result: {
      status: 'calculated', funding_gap: 0, roi: 0, net_profit: 0,
    } }, risks: [{ id: 1, title: '合同待核验', status: 'open' }], gates: [] },
    { id: 2, name: '上海巡演', city: '上海', version: null, risks: [], gates: [] },
  ] } } })
  renderPage(<InvestorWorkspace mode="projects" />)
  expect(await screen.findByText('北京音乐会')).toBeInTheDocument()
  await user.click(screen.getByText('北京音乐会'))
  expect(screen.getByText('0.00%')).toBeInTheDocument()
  expect(screen.getByText('合同待核验')).toBeInTheDocument()
  expect(screen.getByText('测算待补齐')).toBeInTheDocument()
  await user.type(screen.getByLabelText('搜索项目或城市'), '上海')
  expect(screen.queryByText('北京音乐会')).not.toBeInTheDocument()
})

it('retries an API error and renders an honest empty state', async () => {
  getInvestorWorkspace.mockRejectedValueOnce(new Error('offline')).mockResolvedValue({ data: { data: { projects: [] } } })
  renderPage(<InvestorWorkspace />)
  await userEvent.click(await screen.findByRole('button', { name: '重试' }))
  expect(await screen.findByText('当前空间暂无项目')).toBeInTheDocument()
})

it('explains missing artist binding and does not invent opportunities', async () => {
  getArtistWorkspace.mockResolvedValue({ data: { data: { artist: null, projects: [] } } })
  renderPage(<ArtistWorkspace />)
  expect(await screen.findByText('尚未关联艺人资料')).toBeInTheDocument()
  expect(screen.getByText(/请联系管理员/)).toBeInTheDocument()
})

it('renders bound artist profile with labeled structured values and real opportunities', async () => {
  getArtistWorkspace.mockResolvedValue({ data: { data: {
    artist: { id: 9, name: '艺人甲', tags: '流行', fan_count: '1200', profile: { audience: { city: '北京' } } },
    projects: [{ id: 1, name: '关联演出', city: '北京', venue: '音乐厅', schedule: '待定', status: 'draft' }],
  } } })
  const { container } = renderPage(<ArtistWorkspace mode="profile" />)
  expect(await screen.findByText('艺人甲')).toBeInTheDocument()
  expect(screen.getByText(/1,200/)).toBeInTheDocument()
  expect(container.textContent).not.toContain('[object Object]')
  cleanup()
  renderPage(<ArtistWorkspace mode="opportunities" />)
  expect(await screen.findByText('关联演出')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: '报名' })).not.toBeInTheDocument()
})
