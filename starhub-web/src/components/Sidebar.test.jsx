import { cleanup, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it } from 'vitest'
import Sidebar from './Sidebar'

afterEach(cleanup)
it.each([
  ['Investor', ['资方工作台', '项目评估', '资金与风险', '市场与艺人']],
  ['Artist', ['艺人工作台', '我的资料', '演出机会', 'AI 宣发']],
])('provides independent desktop and mobile navigation for %s', (role, labels) => {
  render(<MemoryRouter><Sidebar role={role} /></MemoryRouter>)
  const navigation = within(screen.getByRole('navigation', { name: '主导航' }))
  labels.forEach(label => expect(navigation.getByRole('link', { name: label })).toBeInTheDocument())
  expect(navigation.queryByText('用户管理')).not.toBeInTheDocument()
  expect(within(screen.getByRole('navigation', { name: '移动端主导航' })).getAllByRole('link')).toHaveLength(4)
})
