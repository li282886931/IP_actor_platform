import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { payloadFor, formValues, StructuredValues, useCollaboration } from './collaborationSupport'
import * as api from '../collaborationApi'
vi.mock('../collaborationApi', () => ({ getCollaboration: vi.fn().mockResolvedValue({ data: { data: { items: [] } } }), collaborationMutation: vi.fn() }))
afterEach(() => { cleanup(); vi.clearAllMocks() })
it('preserves zero amounts converts local dates and excludes workflow fields from editing', () => {
  expect(payloadFor('investment', { conditions: '核验', amount: '0' })).toEqual({ conditions: '核验', amount: 0 })
  const payload = payloadFor('invitation', { purpose: '确认', start: '2026-12-01T10:00', end: '2026-12-01T12:00' })
  expect(new Date(payload.end) - new Date(payload.start)).toBe(7200000)
  expect(formValues('rights', { deliverables: '权益', due_date: '2026-12-01', acceptance: '照片', confirmations: [1, 2] })).not.toHaveProperty('confirmations')
  expect(() => payloadFor('task', { evidence_ids: '2,x' })).toThrow('证明材料编号')
})
it('renders nested values safely as Chinese parameter labels', () => {
  render(<StructuredValues value={{ changes: { name: '艺人甲', profile: { introduction: '介绍正文内容' } }, amount: 0 }} />)
  expect(screen.getByText('修改内容')).toBeInTheDocument()
  expect(screen.getByText('艺人甲')).toBeInTheDocument()
  expect(screen.getByText('介绍正文内容')).toBeInTheDocument()
  expect(screen.getByText('金额（元）')).toBeInTheDocument()
  expect(screen.queryByText('[object Object]')).not.toBeInTheDocument()
})
it('reuses the same idempotency key on network failure and allows an explicit retry', async () => {
  api.collaborationMutation.mockRejectedValueOnce(new Error('网络连接断开')).mockResolvedValueOnce({})
  function Example() {
    const { mutate, busy, error } = useCollaboration()
    return <><button disabled={busy} onClick={() => mutate('personal', { type: 'focus', payload: {} })}>提交</button>{error && <p role="alert">{error}</p>}</>
  }
  render(<Example />)
  await userEvent.click(screen.getByRole('button', { name: '提交' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('网络连接断开')
  await userEvent.click(screen.getByRole('button', { name: '提交' }))
  const calls = api.collaborationMutation.mock.calls
  expect(calls[0][2]).toBe(calls[1][2])
})
