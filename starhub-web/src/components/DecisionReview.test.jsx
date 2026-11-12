import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import DecisionReview from './DecisionReview'

afterEach(cleanup)

it('switches role priorities and separates verified sourced facts from evidence', () => {
  render(<DecisionReview facts={[
    { id: 1, status: 'verified', source: '场馆邮件' },
    { id: 2, status: 'pending', source: '会议整理' },
    { id: 3, status: 'verified', source: '' },
  ]} evidences={[{ id: 1 }]} risks={[{ status: 'open' }]} gates={[{ status: 'pending' }]} />)
  expect(screen.getByText('有来源且已核验事实：1 / 3 条')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: '政府' }))
  expect(screen.getByText('当地可用场馆、审批与安全条件')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: '查看风险与关卡' })).toHaveAttribute('href', '#project-risks')
  fireEvent.click(screen.getByRole('button', { name: '品牌' }))
  expect(screen.getByText('传播体量、数据来源与统计周期')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: '资方' }))
  expect(screen.getByText('资金监管、合同保障与分期付款节点')).toBeInTheDocument()
  expect(screen.queryByText('资金安全')).not.toBeInTheDocument()
})
