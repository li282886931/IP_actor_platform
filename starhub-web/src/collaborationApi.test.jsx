import { beforeEach, expect, it, vi } from 'vitest'
const client = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))
vi.mock('axios', () => ({ default: { create: () => client } }))
import { collaborationMutation, getCollaboration, getCollaborationHistory } from './collaborationApi'
beforeEach(() => { localStorage.clear(); vi.clearAllMocks() })
it('sends the active account and space on reads writes and history requests', () => {
  localStorage.setItem('starhub-token', 'account-token')
  localStorage.setItem('starhub-tenant', JSON.stringify({ id: 8 }))
  const options = { headers: { Authorization: 'Bearer account-token', 'X-Tenant-Id': '8' } }
  getCollaboration()
  expect(client.get).toHaveBeenCalledWith('/collaboration', options)
  collaborationMutation('personal', { type: 'focus' }, 'retry-key')
  expect(client.post).toHaveBeenCalledWith('/collaboration/personal', { type: 'focus', request_key: 'retry-key' }, options)
  getCollaborationHistory('items/3')
  expect(client.get).toHaveBeenCalledWith('/collaboration/items/3/history', options)
})
it('does not reuse an earlier account after switching login', () => {
  localStorage.setItem('starhub-token', 'first')
  getCollaboration()
  localStorage.setItem('starhub-token', 'second')
  localStorage.setItem('starhub-tenant', '{invalid')
  getCollaboration()
  expect(client.get).toHaveBeenLastCalledWith('/collaboration', { headers: { Authorization: 'Bearer second' } })
})
