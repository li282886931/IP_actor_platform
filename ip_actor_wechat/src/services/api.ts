import Taro from '@tarojs/taro'

import { CLIENT_SOURCE, DEFAULT_API_BASE, REQUEST_TIMEOUT_MS, STORAGE_KEYS } from '@/config/runtime'

export interface ApiEnvelope<T> {
  code: number
  data: T
  message: string
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  data?: Record<string, unknown>
}

export const getApiBase = () => Taro.getStorageSync<string>(STORAGE_KEYS.apiBase) || DEFAULT_API_BASE

export const setApiBase = (value: string) => {
  const normalized = value.trim().replace(/\/+$/, '')
  Taro.setStorageSync(STORAGE_KEYS.apiBase, normalized || DEFAULT_API_BASE)
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = Taro.getStorageSync<string>(STORAGE_KEYS.token)
  const tenant = Taro.getStorageSync<{ id?: number }>(STORAGE_KEYS.tenant)

  try {
    const response = await Taro.request<ApiEnvelope<T> | T>({
      url: `${getApiBase()}${path}`,
      method: options.method || 'GET',
      data: options.data,
      timeout: REQUEST_TIMEOUT_MS,
      header: {
        'Content-Type': 'application/json',
        'X-Client-Source': CLIENT_SOURCE,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(tenant?.id ? { 'X-Tenant-Id': String(tenant.id) } : {}),
      },
    })

    if (response.statusCode === 401) {
      throw new Error('AUTH_EXPIRED')
    }
    if (response.statusCode === 403) {
      throw new Error('FORBIDDEN')
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw new Error(`HTTP_${response.statusCode}`)
    }
    const body = response.data
    if (body && typeof body === 'object' && 'code' in body) {
      const envelope = body as ApiEnvelope<T>
      if (envelope.code !== 0) {
        throw new Error(envelope.message || 'BUSINESS_ERROR')
      }
      return envelope.data
    }
    return body as T
  } catch (error) {
    console.error('[API] request failed', { path, method: options.method || 'GET', error })
    throw error
  }
}

const query = (params: Record<string, string | number | undefined>) => {
  const entries = Object.entries(params).filter(([, value]) => value !== undefined && value !== '')
  return entries.length
    ? `?${entries.map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`).join('&')}`
    : ''
}

export const api = {
  webLogin: (data: Record<string, unknown>) => request<Record<string, unknown>>('/auth/web-login', { method: 'POST', data }),
  wechatLogin: (data: Record<string, unknown>) => request<Record<string, unknown>>('/auth/wechat-login', { method: 'POST', data }),
  listUserGroups: () => request<unknown[]>('/user-groups'),
  listUsers: () => request<unknown[]>('/users'),
  createUser: (data: Record<string, unknown>) => request<Record<string, unknown>>('/users', { method: 'POST', data }),
  updateUser: (id: number, data: Record<string, unknown>) => request<Record<string, unknown>>(`/users/${id}`, { method: 'PATCH', data }),
  deleteUser: (id: number) => request<Record<string, unknown>>(`/users/${id}`, { method: 'DELETE' }),
  listTenants: () => request<unknown[]>('/tenants'),
  switchTenant: (tenantId: number) => request<Record<string, unknown>>(`/tenants/switch${query({ tenant_id: tenantId })}`, { method: 'POST' }),
  listProjects: () => request<unknown[]>('/projects'),
  createProject: (data: Record<string, unknown>) => request<Record<string, unknown>>('/projects', { method: 'POST', data }),
  getProject: (id: number) => request<Record<string, unknown>>(`/projects/${id}`),
  listProjectVersions: (id: number) => request<unknown[]>(`/projects/${id}/versions`),
  createProjectVersion: (id: number, data: Record<string, unknown>) => request<Record<string, unknown>>(`/projects/${id}/versions`, { method: 'POST', data }),
  calculateFinance: (data: Record<string, unknown>) => request<Record<string, unknown>>('/finance/calculate', { method: 'POST', data }),
  calculateBreakeven: (data: Record<string, unknown>) => request<Record<string, unknown>>('/finance/breakeven', { method: 'POST', data }),
  createDecision: (data: Record<string, unknown>) => request<Record<string, unknown>>('/decisions', { method: 'POST', data }),
  listTasks: (projectId?: number) => request<unknown[]>(`/tasks${query({ project_id: projectId })}`),
  createTask: (data: Record<string, unknown>) => request<Record<string, unknown>>('/tasks', { method: 'POST', data }),
  submitTask: (id: number, data: Record<string, unknown>) => request<Record<string, unknown>>(`/tasks/${id}/submit`, { method: 'POST', data }),
  listFacts: (projectId?: number) => request<unknown[]>(`/facts${query({ project_id: projectId })}`),
  createFact: (data: Record<string, unknown>) => request<Record<string, unknown>>('/facts', { method: 'POST', data }),
  verifyFact: (id: number, data: Record<string, unknown>) => request<Record<string, unknown>>(`/facts/${id}/verify`, { method: 'POST', data }),
  listAssumptions: (projectId?: number) => request<unknown[]>(`/assumptions${query({ project_id: projectId })}`),
  createAssumption: (data: Record<string, unknown>) => request<Record<string, unknown>>('/assumptions', { method: 'POST', data }),
  createEvidence: (data: Record<string, unknown>) => request<Record<string, unknown>>('/evidences/upload', { method: 'POST', data }),
  listEvidences: (projectId?: number, factId?: number) => request<unknown[]>(`/evidences${query({ project_id: projectId, fact_id: factId })}`),
  initiateOSSUpload: (data: Record<string, unknown>) => request<Record<string, unknown>>('/oss/uploads/initiate', { method: 'POST', data }),
  completeOSSUpload: (id: number, data: Record<string, unknown>) => request<Record<string, unknown>>(`/oss/uploads/${id}/complete`, { method: 'POST', data }),
  createDocumentParseJob: (evidenceId: number, data: Record<string, unknown>) => request<Record<string, unknown>>(`/evidences/${evidenceId}/parse-jobs`, { method: 'POST', data }),
  runDocumentParseJob: (id: number) => request<Record<string, unknown>>(`/document-parse-jobs/${id}/run`, { method: 'POST' }),
  confirmDocumentParseJobProjects: (id: number) => request<Record<string, unknown>>(`/document-parse-jobs/${id}/confirm-projects`, { method: 'POST' }),
  listGates: (projectId?: number) => request<unknown[]>(`/gates${query({ project_id: projectId })}`),
  createGate: (data: Record<string, unknown>) => request<Record<string, unknown>>('/gates', { method: 'POST', data }),
  listRisks: (projectId?: number) => request<unknown[]>(`/risks${query({ project_id: projectId })}`),
  createRisk: (data: Record<string, unknown>) => request<Record<string, unknown>>('/risks', { method: 'POST', data }),
  agentChat: (data: Record<string, unknown>) => request<Record<string, unknown>>('/agent/chat', { method: 'POST', data }),
  searchCases: (keyword: string) => request<unknown[]>(`/cases/search${query({ q: keyword })}`),
  createExternalDataJob: (data: Record<string, unknown>) => request<Record<string, unknown>>('/external-data/jobs', { method: 'POST', data }),
  listExternalDataJobs: (projectId?: number) => request<unknown[]>(`/external-data/jobs${query({ project_id: projectId })}`),
  getExternalDataJob: (id: number) => request<Record<string, unknown>>(`/external-data/jobs/${id}`),
  runExternalDataJob: (id: number) => request<Record<string, unknown>>(`/external-data/jobs/${id}/run`, { method: 'POST' }),
  createProjectAnalysisJob: (projectId: number, data: Record<string, unknown>) => request<Record<string, unknown>>(`/projects/${projectId}/analysis-jobs`, { method: 'POST', data }),
  getProjectAnalysisJob: (projectId: number, id: number) => request<Record<string, unknown>>(`/projects/${projectId}/analysis-jobs/${id}`),
  shareReport: (projectId: number, data: Record<string, unknown>) => request<Record<string, unknown>>(`/reports/${projectId}/share`, { method: 'POST', data }),
  generateFeasibilityReport: (projectId: number, data: Record<string, unknown>) => request<Record<string, unknown>>(`/projects/${projectId}/feasibility-report`, { method: 'POST', data }),
  getDashboardAnalytics: () => request<Record<string, unknown>>('/analytics/dashboard'),
  getTicketingSummary: () => request<Record<string, unknown>>('/ticketing/summary'),
  listArtists: (keyword = '') => request<unknown[]>(`/artists${query({ q: keyword })}`),
  getArtist: (id: number) => request<Record<string, unknown>>(`/artists/${id}`),
  generateAI: (data: Record<string, unknown>) => request<Record<string, unknown>>('/ai/generate', { method: 'POST', data }),
  listShows: (city = '') => request<unknown[]>(`/shows${query({ city })}`),
  getShow: (id: number) => request<Record<string, unknown>>(`/shows/${id}`),
  createShowOrder: (id: number, data: Record<string, unknown>) => request<Record<string, unknown>>(`/shows/${id}/order`, { method: 'POST', data }),
  ping: () => request<Record<string, unknown>>('/ping'),
}
