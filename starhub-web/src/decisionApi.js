import API from './api'

function headers() {
  const token = localStorage.getItem('starhub-token')
  let tenant
  try { tenant = JSON.parse(localStorage.getItem('starhub-tenant') || 'null') } catch { tenant = null }
  return { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(tenant?.id ? { 'X-Tenant-Id': String(tenant.id) } : {}) }
}
export const getDecisionWorkspace = () => API.get('/decision/workspace', { headers: headers() })
export const decisionMutation = (path, body, requestKey) => {
  const payload = { ...body, request_key: requestKey }
  const config = { headers: headers() }
  if (path.startsWith('actuals/')) return API.put(`/projects/${path.split('/')[1]}/actuals`, payload, config)
  if (path.startsWith('report/')) return API.post(`/projects/${path.split('/')[1]}/report`, payload, config)
  if (path.startsWith('calibrate/')) return API.post(`/reports/${path.split('/')[1]}/calibrate`, payload, config)
  if (path === 'cities') return API.post('/cities', payload, config)
  return API.post(`/decision/${path}`, payload, config)
}
export const replayDecisionReport = id => API.get(`/decision/reports/${id}/replay`, { headers: headers() })
export const calculateDecisionScenarios = (id, body) => API.post(`/decision/projects/${id}/scenarios`, body, { headers: headers() })
