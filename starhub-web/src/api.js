import axios from 'axios'

const API = axios.create({ baseURL: 'http://localhost:8000' })

export const searchArtist = (q) => API.get(`/artists?q=${encodeURIComponent(q)}`)
export const generateAI = (data) => API.post('/ai/generate', data)
export const listShows = (city) => API.get(`/shows?city=${encodeURIComponent(city || '')}`)
export const getShow = (id) => API.get(`/shows/${id}`)
export const mockOrder = (id, data) => API.post(`/shows/${id}/order`, data)
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
export const createDecision = (data) => API.post('/decisions', data)
export const listTasks = (projectId) => API.get(`/tasks${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''}`)
export const createTask = (data) => API.post('/tasks', data)

export default API
