import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it } from 'vitest'
import PersonalInbox from './PersonalInbox'
import { canAccessRoute } from '../roleConfig'

afterEach(cleanup)
const mount = props => render(<MemoryRouter><PersonalInbox {...props} /></MemoryRouter>)
const personal = { tasks: [
  { id: 1, title: '确认场地', project_name: '春季演出', status: 'in_progress', assignee_name: '张三', description: '补交场地授权', due_date: '2026-12-01' },
  { id: 2, title: '提交合同', status: 'submitted', result: '已上传合同扫描件' },
  { id: 3, title: '历史任务', status: 'completed' },
  { id: 4, title: '补充消防资料', status: 'rejected', rejection_reason: '缺少有效日期' },
] }

it('shows actionable tasks, current step, owner and details without exposing finished tasks by default', async () => {
  mount({ personal, role: 'B' })
  expect(screen.getByText('确认场地')).toBeInTheDocument()
  expect(screen.getByText(/春季演出.*2026-12-01/)).toBeInTheDocument()
  expect(screen.getByText(/负责人：张三/)).toBeInTheDocument()
  expect(screen.getByText('执行中')).toBeInTheDocument()
  expect(screen.getByText(/下一步：完成执行并提交结果/)).toBeInTheDocument()
  expect(screen.getByText(/缺少有效日期/)).toBeInTheDocument()
  expect(screen.queryByText('历史任务')).not.toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: '待验收 · 1' }))
  expect(screen.getByText('提交合同')).toBeInTheDocument()
  expect(screen.queryByText('确认场地')).not.toBeInTheDocument()
  expect(screen.getByText(/下一处理人：验收负责人待指定/)).toBeInTheDocument()
  await userEvent.click(screen.getByText('展开任务材料'))
  expect(screen.getByText('已上传合同扫描件')).toBeVisible()
  await userEvent.click(screen.getByRole('button', { name: '已结束 · 1' }))
  expect(screen.getByText('历史任务')).toBeInTheDocument()
})

it('does not imply a completed workflow when no personal tasks exist', () => {
  mount({ role: 'Artist', data: {} })
  expect(screen.getByText('暂无分配给您的待办')).toBeInTheDocument()
  expect(screen.getByText('尚未关联艺人资料 · 下一步：联系管理员绑定资料')).toBeInTheDocument()
  expect(screen.queryByText('流程已完成')).not.toBeInTheDocument()
})

it('shows actual gate statuses and owners separately from role workflow guidance', () => {
  mount({ role: 'G', data: { projects: [{ id: 4, name: '核验演出', status: 'pending_confirmation',
    gates: [{ id: 8, name: '场地安全', status: 'pending', owner_group: 'B', required_evidence: '消防材料' },
      { id: 9, name: '资金确认', status: 'passed', owner_group: 'Investor' }],
    risks: [{ status: 'open' }], evidence: { pending: 2 },
  }] } })
  expect(screen.getByRole('heading', { name: '工作流程' })).toBeInTheDocument()
  expect(screen.getByText('待确认推进')).toBeInTheDocument()
  const row = screen.getByText('场地安全').closest('article')
  expect(within(row).getByText(/责任角色：主办方/)).toBeInTheDocument()
  expect(within(row).getByText(/下一步：补齐并核验.*消防材料/)).toBeInTheDocument()
  expect(screen.getByText(/2 份证据待核验.*1 项开放风险/)).toBeInTheDocument()
  expect(screen.getByRole('link', { name: '审批与安全' })).toHaveAttribute('href', '/city/review')
  expect(screen.getByText(/法定审批结果.*待接入/)).toBeInTheDocument()
})

it('keeps unsupported audience stages explicit and links to available reservation pages', () => {
  mount({ role: 'C', data: { reservations: [{ id: 1, show: { title: '我的音乐节' } }] } })
  expect(screen.getByText(/我的音乐节.*已登记/)).toBeInTheDocument()
  expect(screen.getByText(/购票、支付与核销.*待接入/)).toBeInTheDocument()
  expect(screen.getByRole('link', { name: '我的预约' })).toHaveAttribute('href', '/audience/reservations')
})

it('keeps long lists compact and allows opening all tasks', async () => {
  mount({ role: 'Admin', personal: { tasks: Array.from({ length: 8 }, (_, i) => ({ id: i, title: `个人事项${i}`, status: 'pending' })) } })
  expect(screen.queryByText('个人事项7')).not.toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: '展开全部 8 项待办' }))
  expect(screen.getByText('个人事项7')).toBeInTheDocument()
})

it.each(['Admin', 'B', 'Brand', 'G', 'C', 'Investor', 'Artist'])('shows only accessible workflow entrances for %s', role => {
  mount({ role })
  const flow = screen.getByRole('heading', { name: '工作流程' }).closest('section')
  expect(within(flow).getByRole('list')).toBeInTheDocument()
  const links = within(flow).getAllByRole('link')
  expect(links.length).toBeGreaterThan(0)
  for (const link of links) expect(canAccessRoute(role, link.getAttribute('href'))).toBe(true)
})

it('keeps unknown task states visible for confirmation and does not invent a workflow stage', () => {
  mount({ personal: { tasks: [{ id: 1, title: '未知事项', status: 'external_status' }] }, role: 'Brand' })
  expect(screen.getByText('状态待确认')).toBeInTheDocument()
  expect(screen.getByText(/下一步：联系项目负责人确认任务状态/)).toBeInTheDocument()
})
it('shows the actual reviewer and execution entry for a linked collaboration task', () => {
  mount({ role: 'Artist', personal: { tasks: [{ id: 1, title: '履约验收', status: 'submitted', reviewer_name: '项目主办人', next_user_name: '项目主办人', collaboration_item_id: 7 }] } })
  expect(screen.getByText(/下一处理人：项目主办人/)).toBeInTheDocument()
  expect(screen.getByText(/下一步：等待项目主办人验收/)).toBeInTheDocument()
  expect(screen.getByRole('link', { name: '处理事项与查看历史' })).toHaveAttribute('href', '/collaboration')
})

it('does not interpret absent artist gate projections as missing project gates', async () => {
  mount({ role: 'Artist', data: { artist: { name: '甲' }, projects: [{ id: 1, name: '关联演出', schedule: '待定', venue: '音乐厅' }] },
    personal: { tasks: [{ id: 1, title: '艺人任务', status: 'pending', evidence_count: 0 }] } })
  expect(screen.getByText('出演安排待确认')).toBeInTheDocument()
  expect(screen.queryByText('关卡清单待补齐')).not.toBeInTheDocument()
  await userEvent.click(screen.getByText('关联演出'))
  expect(screen.getByText(/音乐厅.*向主办方确认出演安排与流程状态/)).toBeVisible()
  expect(screen.queryByText('0', { exact: true })).not.toBeInTheDocument()
})
