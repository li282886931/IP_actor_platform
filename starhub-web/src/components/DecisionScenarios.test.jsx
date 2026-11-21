import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import DecisionScenarios from './DecisionScenarios'
import { calculateDecisionScenarios } from '../decisionApi'

vi.mock('../decisionApi', () => ({ calculateDecisionScenarios: vi.fn() }))
afterEach(() => { cleanup(); vi.clearAllMocks() })
it('sends explicit assumptions to the backend and shows missing parameters', async () => {
  calculateDecisionScenarios.mockResolvedValue({ data: { data: {
    missing_fields: ['capacity'], scenarios: [], cancellation_loss: null, cost_overrun_ratio: null,
  } } })
  const user = userEvent.setup()
  render(<DecisionScenarios projectId={3} />)
  await user.type(screen.getByLabelText('测算票价（元）'), '100')
  await user.type(screen.getByLabelText('有来源的价格弹性（−10–0）'), '-1')
  await user.click(screen.getByRole('button', { name: '计算敏感性' }))
  expect(calculateDecisionScenarios).toHaveBeenCalledWith(3, { price_elasticity: -1, prices: [100] })
  expect(await screen.findByText('待补齐：单场容量（人）')).toBeInTheDocument()
})
