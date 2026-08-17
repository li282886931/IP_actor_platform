import axios from 'axios'

const API = axios.create({ baseURL: 'http://localhost:8000' })

export const searchArtist = (q) => API.get(`/artists?q=${encodeURIComponent(q)}`)
export const generateAI = (data) => API.post('/ai/generate', data)
export const listShows = (city) => API.get(`/shows?city=${encodeURIComponent(city || '')}`)
export const getShow = (id) => API.get(`/shows/${id}`)
export const mockOrder = (id, data) => API.post(`/shows/${id}/order`, data)

export default API
