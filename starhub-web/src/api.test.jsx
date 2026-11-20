import { afterEach, expect, it, vi } from 'vitest'
import API, { agentChat, listAgentSources, generateAI, generateAIStream, getInvestorWorkspace, getArtistWorkspace, getAdminWorkspace, getBusinessWorkspace, getBrandWorkspace, getGovernmentWorkspace, getAudienceWorkspace, mockOrder, createUser, updateUser } from './api'
import { createProject, createProjectVersion, calculateFinance, calculateShow } from './api'
import { generateAIImage, getAIImage } from './api'
import {
  activateDataSourceRegistration,
  createCustomConnectorDefinition,
  disableDataSourceRegistration,
  listConnectorDefinitions,
  registerDataSource,
  testDataSourceRegistration,
  updateDataSourceRegistration,
} from './api'

it('authenticates image generation and URL refresh with a 300 second generation timeout', async () => {
  localStorage.setItem('starhub-token', 'image-session')
  localStorage.setItem('starhub-tenant', JSON.stringify({ id: 7 }))
  const post = vi.spyOn(API, 'post').mockResolvedValue({})
  const get = vi.spyOn(API, 'get').mockResolvedValue({})
  await generateAIImage({ prompt: '舞台' })
  await getAIImage(3)
  expect(post).toHaveBeenCalledWith('/ai/generate/image', { prompt: '舞台' }, {
    timeout: 300000, headers: { Authorization: 'Bearer image-session', 'X-Tenant-Id': '7' },
  })
  expect(get).toHaveBeenCalledWith('/ai/images/3', {
    headers: { Authorization: 'Bearer image-session', 'X-Tenant-Id': '7' },
  })
})

afterEach(() => {
  localStorage.clear()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

it('rejects an upstream SSE error instead of returning partial content as a completed generation', async () => {
  const onFinal = vi.fn()
  const onDelta = vi.fn()
  const body = new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(
        'data: {"event":"delta","content":"部分文案"}\n\n' +
        'data: {"event":"error","message":"硅基流动生成失败，请重试"}\n\n',
      ))
      controller.close()
    },
  })
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, body }))
  await expect(generateAIStream({ type: 'poster' }, { onFinal, onDelta })).rejects.toThrow('硅基流动生成失败')
  expect(onDelta).toHaveBeenCalledWith('部分文案')
  expect(onFinal).not.toHaveBeenCalled()
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

it('uses the current account and tenant for project and finance writes, including account switches', async () => {
  const post = vi.spyOn(API, 'post').mockResolvedValue({})
  for (const [token, tenantId] of [['host-session', 4], ['second-host', 8]]) {
    localStorage.setItem('starhub-token', token)
    localStorage.setItem('starhub-tenant', JSON.stringify({ id: tenantId }))
    const writes = [
      [() => createProject({ name: '项目' }), '/projects'],
      [() => createProjectVersion(2, { name: '修订' }), '/projects/2/versions'],
      [() => calculateFinance({ project_id: 2 }), '/finance/calculate'],
      [() => calculateShow({ project_id: 2 }), '/finance/show-calculation'],
    ]
    for (const [write, path] of writes) {
      await write()
      expect(post.mock.lastCall[0]).toBe(path)
      expect(post.mock.lastCall[2]?.headers).toEqual({
        Authorization: `Bearer ${token}`, 'X-Tenant-Id': String(tenantId),
      })
    }
  }
})

it('uses authenticated connector registry endpoints and preserves filter params', async () => {
  localStorage.setItem('starhub-token', 'connector-session')
  localStorage.setItem('starhub-tenant', JSON.stringify({ id: 12 }))
  const get = vi.spyOn(API, 'get').mockResolvedValue({})
  const post = vi.spyOn(API, 'post').mockResolvedValue({})
  const patch = vi.spyOn(API, 'patch').mockResolvedValue({})
  const headers = { Authorization: 'Bearer connector-session', 'X-Tenant-Id': '12' }

  await listConnectorDefinitions({ source_kind: 'api' })
  await createCustomConnectorDefinition({ key: 'custom_read' })
  await registerDataSource({ definition_key: 'amap' })
  await updateDataSourceRegistration(9, { credential_ref: 'AMAP_PROD' })
  await testDataSourceRegistration(9)
  await activateDataSourceRegistration(9)
  await disableDataSourceRegistration(9)

  expect(get).toHaveBeenCalledWith('/connector-definitions', {
    params: { source_kind: 'api' },
    headers,
  })
  expect(post).toHaveBeenNthCalledWith(1, '/connector-definitions/custom', { key: 'custom_read' }, { headers })
  expect(post).toHaveBeenNthCalledWith(2, '/data-sources/register', { definition_key: 'amap' }, { headers })
  expect(patch).toHaveBeenCalledWith('/data-sources/9', { credential_ref: 'AMAP_PROD' }, { headers })
  expect(post).toHaveBeenNthCalledWith(3, '/data-sources/9/test', {}, { headers })
  expect(post).toHaveBeenNthCalledWith(4, '/data-sources/9/activate', {}, { headers })
  expect(post).toHaveBeenNthCalledWith(5, '/data-sources/9/disable', {}, { headers })
})
