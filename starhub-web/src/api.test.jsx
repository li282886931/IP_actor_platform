import { afterEach, expect, it, vi } from 'vitest'
import API, { agentChat, listAgentSources, generateAI, generateAIStream, getInvestorWorkspace, getArtistWorkspace, getAdminWorkspace, getBusinessWorkspace, getBrandWorkspace, getGovernmentWorkspace, getAudienceWorkspace, mockOrder, createUser, updateUser } from './api'

afterEach(() => {
  localStorage.clear()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

it('authenticates role workspaces and admin artist binding requests using the current session', async () => {
  localStorage.setItem('starhub-token', 'signed-session')
  localStorage.setItem('starhub-tenant', JSON.stringify({ id: 5 }))
  const get = vi.spyOn(API, 'get').mockResolvedValue({})
  const post = vi.spyOn(API, 'post').mockResolvedValue({})
  const patch = vi.spyOn(API, 'patch').mockResolvedValue({})
  await getInvestorWorkspace()
  await getArtistWorkspace()
  await getAdminWorkspace()
  await getBusinessWorkspace()
  await getBrandWorkspace()
  await getGovernmentWorkspace()
  await getAudienceWorkspace()
  await createUser({ group_code: 'Artist', artist_id: 1 })
  await updateUser(9, { artist_id: null })
  const expected = { Authorization: 'Bearer signed-session', 'X-Tenant-Id': '5' }
  get.mock.calls.forEach(call => expect(call[1].headers).toEqual(expected))
  expect(post.mock.calls[0][2].headers).toEqual(expected)
  expect(patch.mock.calls[0][2].headers).toEqual(expected)
  await mockOrder(1, { name: '甲', phone: '13800000000' })
  expect(post.mock.calls[1][2].headers).toEqual(expected)
  localStorage.setItem('starhub-token', 'second-session')
  await mockOrder(1, { name: '乙', phone: '13800000000' })
  expect(post.mock.calls[2][2].headers.Authorization).toBe('Bearer second-session')
})

it('sends the current login and space with both generation endpoints', async () => {
  localStorage.setItem('starhub-token', 'user-a-token')
  localStorage.setItem('starhub-tenant', JSON.stringify({ id: 7 }))
  const post = vi.spyOn(API, 'post').mockResolvedValue({})
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true, body: { getReader: () => ({ read: async () => ({ done: true }) }) },
  })
  vi.stubGlobal('fetch', fetchMock)
  await generateAI({ type: 'poster' })
  await generateAIStream({ type: 'poster' })
  const expected = { Authorization: 'Bearer user-a-token', 'X-Tenant-Id': '7' }
  expect(post.mock.calls[0][2].headers).toEqual(expected)
  expect(fetchMock.mock.calls[0][1].headers).toMatchObject(expected)
  localStorage.setItem('starhub-token', 'user-b-token')
  await generateAIStream({ type: 'poster' })
  expect(fetchMock.mock.calls[1][1].headers.Authorization).toBe('Bearer user-b-token')
})

it('authenticates live analysis tool discovery and execution', async () => {
  localStorage.setItem('starhub-token', 'analysis-session')
  localStorage.setItem('starhub-tenant', JSON.stringify({ id: 4 }))
  const get = vi.spyOn(API, 'get').mockResolvedValue({})
  const post = vi.spyOn(API, 'post').mockResolvedValue({})
  await listAgentSources(2)
  await agentChat({ project_id: 2, message: '读取', reads: [{ source_id: 1 }] })
  expect(get.mock.calls[0][1].headers.Authorization).toBe('Bearer analysis-session')
  expect(post.mock.calls[0][2].headers['X-Tenant-Id']).toBe('4')
})
