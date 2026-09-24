const { screens, fixtures, nextScreen, tabs } = require('./screens')

const apiBase = () => wx.getStorageSync('starhub-api-base') || 'http://127.0.0.1:8000'
const routeFor = (screenId) => '/pages/' + screenId.toLowerCase() + '/index'
const fixtureItems = (group) => (fixtures[group] || fixtures['项目']).map((item, index) => ({
  id: group + '-' + index,
  title: item[0],
  description: item[1],
  status: item[2]
}))

const normalizeItems = (values, group) => {
  if (!Array.isArray(values) || values.length === 0) return fixtureItems(group)
  return values.map((value, index) => ({
    id: String(value.id || value.project_id || group + '-' + index),
    title: String(value.name || value.title || value.account || group + '记录 ' + (index + 1)),
    description: String(value.description || value.content || value.city || value.source || '详情已从决策服务同步'),
    status: String(value.status || value.level || value.group_code || '已同步'),
    value: value.profit || value.heat_score || value.fan_count || ''
  }))
}

const request = (path, method = 'GET', data) => new Promise((resolve, reject) => {
  const token = wx.getStorageSync('starhub-token')
  const tenant = wx.getStorageSync('starhub-tenant') || {}
  const header = {
    'Content-Type': 'application/json',
    'X-Client-Source': 'mp'
  }
  if (token) header.Authorization = 'Bearer ' + token
  if (tenant.id) header['X-Tenant-Id'] = String(tenant.id)
  wx.request({
    url: apiBase() + path,
    method,
    data,
    timeout: 300000,
    header,
    success: (response) => {
      if (response.statusCode < 200 || response.statusCode >= 300) {
        reject(new Error('HTTP_' + response.statusCode))
        return
      }
      const body = response.data
      if (body && typeof body === 'object' && 'code' in body) {
        if (body.code !== 0) reject(new Error(body.message || 'BUSINESS_ERROR'))
        else resolve(body.data)
      } else {
        resolve(body)
      }
    },
    fail: reject
  })
})

const query = (params) => {
  const entries = Object.keys(params).filter((key) => params[key] !== undefined && params[key] !== '')
  return entries.length ? '?' + entries.map((key) => encodeURIComponent(key) + '=' + encodeURIComponent(String(params[key]))).join('&') : ''
}

const createScreenPage = (screenId) => {
  const screen = screens[screenId]
  return Page({
    data: {
      screen,
      items: fixtureItems(screen.group),
      loadState: 'idle',
      message: '',
      keyword: '',
      placeholder: screenId === 'S82' ? 'http://127.0.0.1:8000' : '输入关键词或补充信息',
      apiBase: apiBase(),
      isForm: ['S09','S13','S14','S15','S16','S17','S25','S36','S37','S41','S45','S47','S51','S54','S57','S65','S72','S79','S82'].includes(screenId)
    },
    onLoad() {
      this.fetchRemote()
    },
    onPullDownRefresh() {
      this.fetchRemote().finally(() => wx.stopPullDownRefresh())
    },
    onInput(event) {
      this.setData({ keyword: event.detail.value })
    },
    fetchRemote() {
      this.setData({ loadState: 'loading', message: '' })
      const projectId = Number(wx.getStorageSync('starhub-project-id') || 1)
      const taskId = Number(wx.getStorageSync('starhub-task-id') || 1)
      let promise
      switch (screenId) {
        case 'S02': promise = request('/tenants'); break
        case 'S04': promise = request('/shows'); break
        case 'S06':
        case 'S09': promise = request('/cases/search' + query({ q: this.data.keyword })); break
        case 'S10': promise = request('/projects'); break
        case 'S11': promise = request('/projects/' + projectId).then((project) => [project]); break
        case 'S12':
        case 'S49': promise = request('/projects/' + projectId + '/versions'); break
        case 'S19': promise = request('/artists' + query({ q: this.data.keyword })); break
        case 'S36': promise = request('/assumptions' + query({ project_id: projectId })); break
        case 'S37': promise = request('/facts' + query({ project_id: projectId })); break
        case 'S38':
        case 'S41':
        case 'S42': promise = request('/evidences' + query({ project_id: projectId })); break
        case 'S43':
        case 'S44': promise = request('/risks' + query({ project_id: projectId })); break
        case 'S45':
        case 'S46': promise = request('/gates' + query({ project_id: projectId })); break
        case 'S52':
        case 'S53':
        case 'S55':
        case 'S56':
        case 'S57':
        case 'S58': promise = request('/tasks' + query({ project_id: projectId })); break
        case 'S82': promise = request('/ping').then(() => []); break
        default: promise = Promise.resolve([])
      }
      return promise.then((values) => {
        const items = Array.isArray(values) && values.length ? normalizeItems(values, screen.group) : fixtureItems(screen.group)
        this.setData({ items, loadState: 'success', message: screenId === 'S82' ? '决策服务连接正常' : '' })
      }).catch((error) => {
        console.error('[MiniApp] load failed', screenId, error)
        this.setData({ loadState: 'example', items: fixtureItems(screen.group), message: '决策服务暂不可用，当前展示已标注的产品示例数据。' })
      })
    },
    onPrimaryTap() {
      if (screenId === 'S01') {
        request('/auth/wechat-login', 'POST', { code: 'local-devtools', name: '小程序用户', group_code: 'B' }).then((session) => {
          wx.setStorageSync('starhub-token', session.token)
          wx.setStorageSync('starhub-user', session.user)
          wx.setStorageSync('starhub-tenant', session.current_tenant)
          this.goNext()
        }).catch((error) => {
          console.error('[MiniApp] login failed', error)
          this.setData({ message: '登录失败，请确认后端服务可用。' })
        })
        return
      }
      if (screenId === 'S82') {
        const value = this.data.keyword && this.data.keyword.trim()
        if (value) wx.setStorageSync('starhub-api-base', value.replace(/\/+$/, ''))
        this.fetchRemote()
        return
      }
      this.goNext()
    },
    goNext() {
      const target = nextScreen[screenId] || 'S04'
      const url = routeFor(target)
      if (tabs.includes(target)) wx.switchTab({ url })
      else wx.redirectTo({ url })
    }
  })
}

module.exports = { createScreenPage }
