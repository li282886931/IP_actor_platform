import axios from 'axios'

const client = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000' })
const headers = () => {
  let tenant
  try { tenant = JSON.parse(localStorage.getItem('starhub-tenant') || 'null') } catch { tenant = null }
  const token = localStorage.getItem('starhub-token')
  return { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(tenant?.id ? { 'X-Tenant-Id': String(tenant.id) } : {}) }
}
export const getCollaboration = () => client.get('/collaboration', { headers: headers() })
export const collaborationMutation = (path, body, requestKey) => client.post(`/collaboration/${path}`, { ...body, request_key: requestKey }, { headers: headers() })
export const getCollaborationHistory = (path) => client.get(`/collaboration/${path}/history`, { headers: headers() })
