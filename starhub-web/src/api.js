import axios from 'axios'

const API = axios.create({ baseURL: 'http://localhost:8000' })

const stripThinkContent = (value = '') => value
  .replace(/<think\b[^>]*>[\s\S]*?<\/think>/gi, '')
  .replace(/^\s*<\/?think>\s*$/gim, '')
  .trim()

const parseSsePayload = (raw) => {
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export const searchArtist = (q) => API.get(`/artists?q=${encodeURIComponent(q)}`)
export const generateAI = (data) => API.post('/ai/generate', data)
export const generateAIStream = async (data, handlers = {}) => {
  const response = await fetch(`${API.defaults.baseURL}/ai/generate/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) throw new Error(`HTTP_${response.status}`)
  if (!response.body) throw new Error('STREAM_UNAVAILABLE')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finalResult = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() || ''
    for (const eventText of events) {
      const dataLine = eventText.split('\n').find((line) => line.startsWith('data:'))
      if (!dataLine) continue
      const event = parseSsePayload(dataLine.replace(/^data:\s*/, ''))
      if (!event) continue
      if (event.event === 'progress') handlers.onProgress?.(event.message || '')
      if (event.event === 'thought') handlers.onThought?.(stripThinkContent(event.content || ''))
      if (event.event === 'delta') handlers.onDelta?.(stripThinkContent(event.content || ''))
      if (event.event === 'final') {
        finalResult = stripThinkContent(event.result || '')
        handlers.onFinal?.(finalResult)
      }
    }
  }

  return finalResult
}
export const listShows = (city) => API.get(`/shows?city=${encodeURIComponent(city || '')}`)
export const getShowRecommendations = (phone) => API.get(`/shows/recommendations?phone=${encodeURIComponent(phone || '')}`)
export const getShow = (id) => API.get(`/shows/${id}`)
export const mockOrder = (id, data) => API.post(`/shows/${id}/order`, data)
export const getDashboardAnalytics = () => API.get('/analytics/dashboard')
export const getTicketingSummary = () => API.get('/ticketing/summary')
export const getAuthCaptcha = () => API.get('/auth/captcha')
export const webLogin = (data) => API.post('/auth/web-login', data)
export const listUsers = () => API.get('/users')
export const createUser = (data) => API.post('/users', data)
export const updateUser = (id, data) => API.patch(`/users/${id}`, data)
export const deleteUser = (id) => API.delete(`/users/${id}`)
export const listUserGroups = () => API.get('/user-groups')
export const listTenants = () => API.get('/tenants')
export const switchTenant = (tenantId) => API.post(`/tenants/switch?tenant_id=${encodeURIComponent(tenantId)}`)
export const listProjects = () => API.get('/projects')
export const createProject = (data) => API.post('/projects', data)
export const getProject = (id) => API.get(`/projects/${id}`)
export const listProjectVersions = (id) => API.get(`/projects/${id}/versions`)
export const createProjectVersion = (id, data) => API.post(`/projects/${id}/versions`, data)
export const calculateFinance = (data) => API.post('/finance/calculate', data)
export const calculateBreakeven = (data) => API.post('/finance/breakeven', data)
export const createDecision = (data) => API.post('/decisions', data)
export const listTasks = (projectId) => API.get(`/tasks${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''}`)
export const createTask = (data) => API.post('/tasks', data)
export const submitTask = (id, data) => API.post(`/tasks/${id}/submit`, data)
export const listFacts = (projectId) => API.get(`/facts${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''}`)
export const createFact = (data) => API.post('/facts', data)
export const verifyFact = (id, data) => API.post(`/facts/${id}/verify`, data)
export const listAssumptions = (projectId) => API.get(`/assumptions${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''}`)
export const createAssumption = (data) => API.post('/assumptions', data)
export const listEvidences = (projectId, factId) => {
  const params = new URLSearchParams()
  if (projectId) params.set('project_id', projectId)
  if (factId) params.set('fact_id', factId)
  const query = params.toString()
  return API.get(`/evidences${query ? `?${query}` : ''}`)
}
export const createEvidence = (data) => API.post('/evidences/upload', data)
export const listGates = (projectId) => API.get(`/gates${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''}`)
export const createGate = (data) => API.post('/gates', data)
export const listRisks = (projectId) => API.get(`/risks${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''}`)
export const createRisk = (data) => API.post('/risks', data)
export const listExternalDataJobs = (projectId) => API.get(`/external-data/jobs${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''}`)
export const createExternalDataJob = (data) => API.post('/external-data/jobs', data)
export const runExternalDataJob = (id) => API.post(`/external-data/jobs/${id}/run`)
export const agentChat = (data) => API.post('/agent/chat', data)
export const searchCases = (q) => API.get(`/cases/search?q=${encodeURIComponent(q || '')}`)
export const shareReport = (projectId, data) => API.post(`/reports/${projectId}/share`, data)
export const generateFeasibilityReport = (projectId, data) => API.post(`/projects/${projectId}/feasibility-report`, data)

export default API
