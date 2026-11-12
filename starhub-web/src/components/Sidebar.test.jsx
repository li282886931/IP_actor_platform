import { cleanup, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it } from 'vitest'
import Sidebar from './Sidebar'

afterEach(cleanup)
it.each([
  ['Admin', ['创建角色账号']],
  ['B', ['经营工作台', '项目运营', '执行待办', '艺人智策', 'AI 宣发']],
  ['Brand', ['品牌工作台', '合作候选', '效果与证据', '受众洞察', 'AI 品宣']],
  ['G', ['城市工作台', '城市项目', '审批与安全', '文旅成效', '城市宣发']],
  ['C', ['我的现场', '演出发现', '我的预约', '艺人查询']],
  ['Investor', ['资方工作台', '项目评估', '资金与风险', '市场与艺人']],
  ['Artist', ['艺人工作台', '我的资料', '演出机会', 'AI 宣发']],
])('provides independent desktop and mobile navigation for %s', (role, labels) => {
  render(<MemoryRouter><Sidebar role={role} /></MemoryRouter>)
  const navigation = within(screen.getByRole('navigation', { name: '主导航' }))
  labels.forEach(label => expect(navigation.getByRole('link', { name: label })).toBeInTheDocument())
  if (role === 'Admin') {
    expect(navigation.getAllByRole('link')).toHaveLength(1)
    expect(navigation.getByRole('link')).toHaveAttribute('href', '/users')
    const mobile = within(screen.getByRole('navigation', { name: '移动端主导航' }))
    expect(mobile.getAllByRole('link')).toHaveLength(1)
    expect(mobile.getByRole('link', { name: '创建账号' })).toHaveAttribute('href', '/users')
    return
  }
  if (role !== 'Admin') expect(navigation.queryByText('用户管理')).not.toBeInTheDocument()
  expect(navigation.getByRole('link', { name: '个人关注' })).toHaveAttribute('href', '/preferences')
  expect(navigation.getAllByRole('link').some(link => link.getAttribute('href') === '/collaboration')).toBe(true)
  const mobile = within(screen.getByRole('navigation', { name: '移动端主导航' }))
  expect(mobile.getAllByRole('link')).toHaveLength(labels.length + 2)
  expect(mobile.getByRole('link', { name: '协作' })).toHaveAttribute('href', '/collaboration')
})
