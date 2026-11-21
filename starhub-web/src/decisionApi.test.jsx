import { afterEach, expect, it, vi } from 'vitest'
import API from './api'
import { calculateDecisionScenarios, decisionMutation, getDecisionWorkspace } from './decisionApi'
vi.mock('./api', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn() } }))
afterEach(() => { vi.clearAllMocks(); localStorage.clear() })
it('sends login and tenant context with each decision request', () => {
  localStorage.setItem('starhub-token', 'test-token')
  localStorage.setItem('starhub-tenant', JSON.stringify({ id: 7 }))
  getDecisionWorkspace()
  calculateDecisionScenarios(3, { prices: [100] })
  const config = { headers: { Authorization: 'Bearer test-token', 'X-Tenant-Id': '7' } }
  expect(API.get).toHaveBeenCalledWith('/decision/workspace', config)
  expect(API.post).toHaveBeenCalledWith('/decision/projects/3/scenarios', { prices: [100] }, config)
})
it('routes mutations correctly and retains the supplied idempotency key', () => {
  decisionMutation('actuals/3', { actual_cost: 100 }, 'once')
  expect(API.put).toHaveBeenCalledWith('/projects/3/actuals', { actual_cost: 100, request_key: 'once' }, expect.any(Object))
  decisionMutation('calibrate/4', { attribution: '偏差' }, 'calibration')
  expect(API.post).toHaveBeenCalledWith('/reports/4/calibrate', { attribution: '偏差', request_key: 'calibration' }, expect.any(Object))
})
