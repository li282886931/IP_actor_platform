import { mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { routeFor, screens } from './blueprint-manifest.mjs'

const root = resolve(import.meta.dirname, '..')
const dist = resolve(root, 'dist')

const runtimeConfig = {
  DEFAULT_API_BASE: 'http://127.0.0.1:8000',
  REQUEST_TIMEOUT_MS: 300000,
  CLIENT_SOURCE: 'mp',
  STORAGE_KEYS: {
    apiBase: 'starhub-api-base',
    token: 'starhub-token',
    tenant: 'starhub-tenant',
    user: 'starhub-user',
    projectDraft: 'starhub-project-draft',
    projectId: 'starhub-project-id',
    versionId: 'starhub-version-id',
    taskId: 'starhub-task-id',
    artistId: 'starhub-artist-id',
  },
}

const tabItems = [
  ['S04', '发现', 'discover'],
  ['S10', '项目', 'project'],
  ['S52', '工作', 'agent'],
  ['S67', '我的', 'profile'],
]
const tabScreenIds = new Set(tabItems.map(([screenId]) => screenId))

const nextScreen = {
  S01: 'S02', S02: 'S03', S03: 'S04', S04: 'S13', S05: 'S11', S06: 'S07',
  S07: 'S13', S08: 'S13', S09: 'S06', S10: 'S13', S11: 'S34', S12: 'S49',
  S13: 'S14', S14: 'S15', S15: 'S16', S16: 'S17', S17: 'S74', S18: 'S16',
  S24: 'S25', S25: 'S29', S26: 'S25', S27: 'S25',
  S28: 'S29', S29: 'S34', S30: 'S29', S31: 'S34', S32: 'S34', S33: 'S55',
  S34: 'S45', S35: 'S37', S36: 'S12', S37: 'S40', S38: 'S37', S39: 'S42',
  S40: 'S41', S41: 'S42', S42: 'S39', S43: 'S44', S44: 'S55', S45: 'S46',
  S46: 'S47', S47: 'S48', S48: 'S52', S49: 'S47', S50: 'S51', S51: 'S50',
  S52: 'S53', S53: 'S55', S54: 'S55', S55: 'S56', S56: 'S57', S57: 'S55',
  S58: 'S55', S59: 'S49', S60: 'S52', S61: 'S62', S62: 'S63', S63: 'S11',
  S64: 'S65', S65: 'S66', S66: 'S10', S67: 'S68', S68: 'S72', S69: 'S55',
  S70: 'S83', S71: 'S67', S72: 'S68', S73: 'S13', S74: 'S11', S75: 'S10',
  S76: 'S37', S77: 'S67', S78: 'S49', S79: 'S25', S80: 'S10', S81: 'S01',
  S82: 'S70', S83: 'S70', S84: 'S67',
}

const pagePath = (screenId) => routeFor(screenId).slice(1)
const serializableScreens = Object.fromEntries(screens.map((item) => [
  item[0],
  {
    id: item[0],
    title: item[1],
    subtitle: item[2],
    group: item[3],
    primaryAction: item[4],
    highlight: '',
  },
]))

rmSync(dist, { recursive: true, force: true })
mkdirSync(dist, { recursive: true })
mkdirSync(resolve(dist, 'common'), { recursive: true })
mkdirSync(resolve(dist, 'assets/tabbar'), { recursive: true })

writeFileSync(resolve(dist, 'app.json'), `${JSON.stringify({
  pages: [...screens.map(([id]) => pagePath(id)), 'pages/entity-detail/index'],
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#ffffff',
    navigationBarTitleText: '锐音场',
    navigationBarTextStyle: 'black',
  },
  tabBar: {
    color: '#86909c',
    selectedColor: '#2864dc',
    backgroundColor: '#ffffff',
    borderStyle: 'white',
    list: tabItems.map(([id, text, icon]) => ({
      pagePath: pagePath(id),
      text,
      iconPath: `assets/tabbar/${icon}.png`,
      selectedIconPath: `assets/tabbar/${icon}-selected.png`,
    })),
  },
  sitemapLocation: 'sitemap.json',
}, null, 2)}\n`)

writeFileSync(resolve(dist, 'app.js'), `App({
  globalData: {
    apiBase: ${JSON.stringify(runtimeConfig.DEFAULT_API_BASE)}
  }
})
`)

writeFileSync(resolve(dist, 'sitemap.json'), `${JSON.stringify({ rules: [{ action: 'allow', page: '*' }] }, null, 2)}\n`)

writeFileSync(resolve(dist, 'app.wxss'), `page {
  min-height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif;
  font-size: 28rpx;
  color: #1d2129;
  background: #f5f7fb;
}
view, text, button, input, scroll-view {
  box-sizing: border-box;
}
button::after {
  border: 0;
}
`)

writeFileSync(resolve(dist, 'common/screens.js'), `const screens = ${JSON.stringify(serializableScreens, null, 2)}
const nextScreen = ${JSON.stringify(nextScreen, null, 2)}
const tabs = ${JSON.stringify(tabItems.map(([id]) => id), null, 2)}

module.exports = { screens, nextScreen, tabs }
`)

writeFileSync(resolve(dist, 'common/config.js'), `module.exports = ${JSON.stringify(runtimeConfig, null, 2)}
`)

writeFileSync(resolve(dist, 'common/runtime.js'), `const { screens, nextScreen, tabs } = require('./screens')
const { DEFAULT_API_BASE, REQUEST_TIMEOUT_MS, CLIENT_SOURCE, STORAGE_KEYS } = require('./config')

const apiBase = () => wx.getStorageSync(STORAGE_KEYS.apiBase) || DEFAULT_API_BASE
const routeFor = (screenId) => '/pages/' + screenId.toLowerCase() + '/index'
const statusLabels = {
  active: '进行中',
  archived: '已归档',
  available: '可用',
  blocked: '已阻塞',
  calculated: '已测算',
  closed: '已关闭',
  completed: '已完成',
  confirmed: '已确认',
  disabled: '已停用',
  draft: '草稿',
  enabled: '已启用',
  failed: '失败',
  in_progress: '进行中',
  on_sale: '售票中',
  open: '待处理',
  pending: '待处理',
  pending_confirmation: '待确认',
  queued: '排队中',
  read: '已读',
  revoked: '已撤回',
  running: '处理中',
  settled: '已结算',
  submitted: '待验收',
  unread: '未读',
  unverified: '待核验',
  verified: '已核验'
}
const statusLabel = (status) => statusLabels[status] || status

const normalizeItems = (values) => {
  if (!Array.isArray(values)) return []
  return values.map((value, index) => ({
    id: String(value.id || 'record-' + index),
    entityId: Number(value.context && (value.context.task_id || value.context.project_id) || 0),
    title: String(value.title || ''),
    description: String(value.description || ''),
    status: statusLabel(String(value.status || '')),
    value: value.value == null ? '' : String(value.value),
    details: String(value.details || ''),
    detailRef: value.detail_ref || null
  }))
}

const request = (path, method = 'GET', data) => new Promise((resolve, reject) => {
  const token = wx.getStorageSync(STORAGE_KEYS.token)
  const tenant = wx.getStorageSync(STORAGE_KEYS.tenant) || {}
  const header = {
    'Content-Type': 'application/json',
    'X-Client-Source': CLIENT_SOURCE
  }
  if (token) header.Authorization = 'Bearer ' + token
  if (tenant.id) header['X-Tenant-Id'] = String(tenant.id)
  wx.request({
    url: apiBase() + path,
    method,
    data,
    timeout: REQUEST_TIMEOUT_MS,
    header,
    success: (response) => {
      if (response.statusCode < 200 || response.statusCode >= 300) {
        const detail = response.data && typeof response.data === 'object' && 'detail' in response.data ? String(response.data.detail) : ''
        reject(new Error(detail || ('HTTP_' + response.statusCode)))
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
  const initialTaskId = Number(wx.getStorageSync(STORAGE_KEYS.taskId) || 0)
  return Page({
    data: {
      screen,
      items: [],
      loadState: 'idle',
      message: '',
      keyword: '',
      placeholder: screenId === 'S82' ? DEFAULT_API_BASE : screenId === 'S13' ? '输入艺人、IP 或项目名称' : '输入关键词或补充信息',
      apiBase: apiBase(),
      candidateGroups: [],
      candidateSearchGroups: [],
      candidateSearchOpen: false,
      candidateSearchLoading: false,
      showHome: screenId !== 'S01' && !tabs.includes(screenId),
      selectedTaskIds: screenId === 'S56' && initialTaskId ? [initialTaskId] : [],
      expandedTaskIds: screenId === 'S56' && initialTaskId ? [initialTaskId] : [],
      isForm: ['S09','S13','S14','S15','S16','S17','S25','S36','S37','S41','S45','S47','S51','S54','S57','S65','S72','S79','S82'].includes(screenId)
    },
    onLoad() {
      this.fetchRemote()
    },
    onPullDownRefresh() {
      this.fetchRemote().finally(() => wx.stopPullDownRefresh())
    },
    onInput(event) {
      const keyword = event.detail.value
      this.setData({ keyword })
      if (['S13', 'S14', 'S15', 'S16'].includes(screenId)) this.onCandidateSearchInput(keyword)
    },
    applyCandidate(candidate) {
      const patch = candidate && candidate.patch
      if (!patch || typeof patch !== 'object') return
      const draft = wx.getStorageSync(STORAGE_KEYS.projectDraft) || {}
      wx.setStorageSync(STORAGE_KEYS.projectDraft, Object.assign({}, draft, patch))
      this.setData({ keyword: candidate.label || this.data.keyword, candidateSearchOpen: false })
    },
    onCandidateTap(event) {
      const groupIndex = Number(event.currentTarget.dataset.groupIndex)
      const itemIndex = Number(event.currentTarget.dataset.itemIndex)
      const group = this.data.candidateGroups[groupIndex]
      const candidate = group && group.items && group.items[itemIndex]
      this.applyCandidate(candidate)
    },
    onCandidateSearchTap(event) {
      const groupIndex = Number(event.currentTarget.dataset.groupIndex)
      const itemIndex = Number(event.currentTarget.dataset.itemIndex)
      const group = this.data.candidateSearchGroups[groupIndex]
      const candidate = group && group.items && group.items[itemIndex]
      this.applyCandidate(candidate)
    },
    candidateFromSearchItem(item) {
      const value = item && item.value || {}
      if (item.entity_type === 'artist') {
        return {
          key: 'artist-' + item.entity_id,
          label: item.label,
          description: item.description || '',
          patch: { artist_id: Number(item.entity_id), artist_name: item.label }
        }
      }
      if (item.entity_type === 'project') {
        return {
          key: 'project-' + item.entity_id,
          label: item.label,
          description: item.description || '',
          patch: Object.assign({}, value, { source_project_id: Number(item.entity_id) })
        }
      }
      if (item.entity_type === 'venue') {
        return {
          key: 'venue-' + item.entity_id,
          label: item.label,
          description: item.description || '',
          patch: {
            venue_id: Number(item.entity_id),
            venue: item.label,
            city: value.city || '',
            venue_capacity: Number(value.capacity) || undefined
          }
        }
      }
      return {
        key: 'city-' + item.label,
        label: item.label,
        description: item.description || '',
        patch: { city: item.label }
      }
    },
    onCandidateSearchInput(keyword) {
      clearTimeout(this.candidateSearchTimer)
      const normalized = String(keyword || '').trim()
      if (!normalized) {
        this.setData({
          candidateSearchGroups: [],
          candidateSearchOpen: false,
          candidateSearchLoading: false
        })
        return
      }
      const localGroups = (this.data.candidateGroups || []).map((group) => Object.assign({}, group, {
        items: (group.items || []).filter((item) => (
          String(item.label || '').toLowerCase().includes(normalized.toLowerCase())
          || String(item.description || '').toLowerCase().includes(normalized.toLowerCase())
        ))
      })).filter((group) => group.items.length)
      if (['S15', 'S16'].includes(screenId)) {
        this.setData({
          candidateSearchGroups: localGroups,
          candidateSearchOpen: true,
          candidateSearchLoading: false
        })
        return
      }
      const allowedTypes = screenId === 'S13' ? ['artist', 'project'] : ['city', 'venue']
      this.setData({ candidateSearchOpen: true, candidateSearchLoading: true })
      this.candidateSearchTimer = setTimeout(() => {
        request('/miniapp/search' + query({ q: normalized })).then((result) => {
          const groups = (result.groups || [])
            .filter((group) => allowedTypes.includes(group.entity_type))
            .map((group) => ({
              key: group.entity_type,
              label: group.label,
              items: (group.items || []).map((item) => this.candidateFromSearchItem(item))
            }))
            .filter((group) => group.items.length)
          this.setData({
            candidateSearchGroups: groups,
            candidateSearchLoading: false
          })
        }).catch((error) => {
          console.error('[CandidateSearch] fuzzy search failed', normalized, error)
          this.setData({ candidateSearchGroups: [], candidateSearchLoading: false })
        })
      }, 300)
    },
    fetchRemote() {
      this.setData({ items: [], loadState: 'loading', message: '' })
      const projectId = Number(wx.getStorageSync(STORAGE_KEYS.projectId) || 0)
      const versionId = Number(wx.getStorageSync(STORAGE_KEYS.versionId) || 0)
      const taskId = Number(wx.getStorageSync(STORAGE_KEYS.taskId) || 0)
      const artistId = Number(wx.getStorageSync(STORAGE_KEYS.artistId) || 0)
      const context = {
        project_id: projectId || undefined,
        version_id: versionId || undefined,
        task_id: taskId || undefined,
        artist_id: artistId || undefined,
        keyword: String(this.data.keyword || '').trim() || undefined
      }
      return request('/miniapp/screens/' + screenId + query(context)).then((data) => {
        let items = normalizeItems(data && data.items)
        if (screenId === 'S52') {
          const cachedProjectId = Number(wx.getStorageSync(STORAGE_KEYS.projectId) || 0)
          const defaultProjectId = Number(data && data.options && data.options.default_project_id || 0)
          if (!cachedProjectId && defaultProjectId) {
            wx.setStorageSync(STORAGE_KEYS.projectId, defaultProjectId)
          }
        }
        if (['S55', 'S56', 'S57', 'S58'].includes(screenId) && items.length) {
          const storedTaskId = Number(wx.getStorageSync(STORAGE_KEYS.taskId) || 0)
          const selectedTask = items.find((task) => task.entityId === storedTaskId) || items[0]
          if (selectedTask.entityId) wx.setStorageSync(STORAGE_KEYS.taskId, selectedTask.entityId)
          if (screenId === 'S56') {
            const selectedTaskIds = this.data.selectedTaskIds
            const expandedTaskIds = this.data.expandedTaskIds
            items = items.map((item) => Object.assign({}, item, {
              selected: selectedTaskIds.includes(item.entityId),
              expanded: expandedTaskIds.includes(item.entityId)
            }))
          }
        }
        const emptyState = data && data.empty_state
        this.setData({
          screen: Object.assign({}, screen, data.summary || {}),
          items,
          candidateGroups: data && data.options && Array.isArray(data.options.candidate_groups)
            ? data.options.candidate_groups
            : [],
          loadState: items.length ? 'success' : 'empty',
          message: !items.length && emptyState ? String(emptyState.title || emptyState.description || '') : ''
        })
      }).catch((error) => {
        console.error('[MiniApp] load failed', screenId, error)
        this.setData({ loadState: 'error', items: [], message: '页面数据加载失败，请重试。' })
      })
    },
    onGetPhoneNumber(event) {
      if (screenId !== 'S01') return
      if (!event.detail || !event.detail.code) {
        this.setData({ loadState: 'error', message: '未完成手机号授权，暂不能登录。' })
        return
      }
      this.setData({ loadState: 'loading', message: '' })
      wx.login({
        success: (loginResult) => {
          request('/auth/wechat-login', 'POST', { code: loginResult.code || 'local-devtools', phone_code: event.detail.code, name: '小程序用户' }).then((session) => {
            wx.setStorageSync(STORAGE_KEYS.token, session.token)
            wx.setStorageSync(STORAGE_KEYS.user, session.user)
            wx.setStorageSync(STORAGE_KEYS.tenant, session.current_tenant)
            this.goNext()
          }).catch((error) => {
            console.error('[MiniApp] phone login failed', error)
            const detail = String(error && error.message || '')
            this.setData({ loadState: 'error', message: detail.includes('Phone number is not linked to any account') ? '手机号未绑定，请联系管理员分配账号。' : '登录失败，请确认后端服务可用。' })
          })
        },
        fail: (error) => {
          console.error('[MiniApp] wx.login failed', error)
          this.setData({ loadState: 'error', message: '登录失败，请确认微信登录状态。' })
        }
      })
    },
    onPrimaryTap() {
      if (screenId === 'S01') {
        this.setData({ loadState: 'error', message: '请使用手机号授权登录。' })
        return
      }
      if (screenId === 'S17') {
        const draft = wx.getStorageSync(STORAGE_KEYS.projectDraft) || {}
        if (!draft.name) {
          this.setData({ loadState: 'error', message: '项目名称缺失，请返回第一步补充。' })
          return Promise.resolve()
        }
        this.setData({ loadState: 'loading', message: '' })
        return request('/projects', 'POST', draft).then((project) => {
          const projectId = Number(project.id || 0)
          if (!projectId) throw new Error('PROJECT_ID_MISSING')
          wx.setStorageSync(STORAGE_KEYS.projectId, projectId)
          if (project.current_version_id) {
            wx.setStorageSync(STORAGE_KEYS.versionId, Number(project.current_version_id))
          }
          wx.removeStorageSync(STORAGE_KEYS.projectDraft)
          this.setData({ loadState: 'success' })
          this.goNext()
        }).catch((error) => {
          console.error('[S17] create project failed', error)
          this.setData({ loadState: 'error', message: '项目创建失败，输入已保留，请重试。' })
        })
      }
      if (screenId === 'S82') {
        const value = this.data.keyword && this.data.keyword.trim()
        if (value) wx.setStorageSync(STORAGE_KEYS.apiBase, value.replace(/\\/+$/, ''))
        this.fetchRemote()
        return
      }
      this.goNext()
    },
    syncTaskItemState() {
      const selectedTaskIds = this.data.selectedTaskIds
      const expandedTaskIds = this.data.expandedTaskIds
      this.setData({
        items: this.data.items.map((item) => Object.assign({}, item, {
          selected: selectedTaskIds.includes(Number(item.id)),
          expanded: expandedTaskIds.includes(Number(item.id))
        }))
      })
    },
    onTaskCheck(event) {
      if (screenId !== 'S56') return
      const taskId = Number(event.currentTarget.dataset.id || 0)
      if (!taskId) return
      const selectedTaskIds = this.data.selectedTaskIds.includes(taskId)
        ? this.data.selectedTaskIds.filter((id) => id !== taskId)
        : this.data.selectedTaskIds.concat(taskId)
      this.setData({ selectedTaskIds }, () => this.syncTaskItemState())
    },
    onTaskToggleDetail(event) {
      if (screenId !== 'S56') return
      const taskId = Number(event.currentTarget.dataset.id || 0)
      if (!taskId) return
      const expandedTaskIds = this.data.expandedTaskIds.includes(taskId)
        ? this.data.expandedTaskIds.filter((id) => id !== taskId)
        : this.data.expandedTaskIds.concat(taskId)
      this.setData({ expandedTaskIds }, () => this.syncTaskItemState())
    },
    onBatchTaskAction(event) {
      if (screenId !== 'S56') return
      const action = event.currentTarget.dataset.action
      if (!this.data.selectedTaskIds.length) {
        this.setData({ loadState: 'error', message: '请至少勾选一项任务。' })
        return
      }
      if (action === 'reject') {
        wx.showModal({
          title: '拒绝接单',
          editable: true,
          placeholderText: '请输入拒绝原因',
          confirmText: '确认拒绝',
          success: (result) => {
            if (!result.confirm) return
            const reason = String(result.content || '').trim()
            if (!reason) {
              this.setData({ loadState: 'error', message: '拒绝接单时必须填写原因。' })
              return
            }
            this.executeBatchTaskAction(action, reason)
          }
        })
        return
      }
      this.executeBatchTaskAction(action, '')
    },
    executeBatchTaskAction(action, reason) {
      const taskIds = this.data.selectedTaskIds.slice()
      this.setData({ loadState: 'loading', message: '' })
      return request('/tasks/actions/batch', 'POST', {
        task_ids: taskIds,
        action,
        reason
      }).then(() => {
        this.setData({ selectedTaskIds: [] })
        return this.fetchRemote()
      }).then(() => {
        const message = action === 'accept'
          ? '已接受 ' + taskIds.length + ' 项任务。'
          : '已拒绝 ' + taskIds.length + ' 项任务，任务已恢复待分配。'
        this.setData({ loadState: 'success', message })
      }).catch((error) => {
        console.error('[S56] batch task action failed', action, error)
        this.setData({
          loadState: 'error',
          message: action === 'accept' ? '接受任务失败，请刷新后重试。' : '拒绝任务失败，请刷新后重试。'
        })
      })
    },
    onBusinessItemTap(event) {
      const entityType = String(event.currentTarget.dataset.entityType || '')
      const entityId = Number(event.currentTarget.dataset.entityId || 0)
      if (!entityType || !entityId) return
      if (entityType === 'task') wx.setStorageSync(STORAGE_KEYS.taskId, entityId)
      wx.navigateTo({
        url: '/pages/entity-detail/index?entityType=' + encodeURIComponent(entityType) + '&entityId=' + entityId
      })
    },
    onHomeTap() {
      const token = String(wx.getStorageSync(STORAGE_KEYS.token) || '')
      if (token) {
        wx.switchTab({ url: routeFor('S04') })
        return
      }
      wx.redirectTo({ url: routeFor('S01') })
    },
    goNext() {
      const hasProject = Number(wx.getStorageSync(STORAGE_KEYS.projectId) || 0) > 0
      const target = ['S52', 'S74'].includes(screenId) && !hasProject
        ? 'S10'
        : nextScreen[screenId] || 'S04'
      const url = routeFor(target)
      if (tabs.includes(target)) wx.switchTab({ url })
      else wx.redirectTo({ url })
    }
  })
}

const createEntityDetailPage = () => Page({
  data: {
    entityType: '',
    entityId: 0,
    detail: null,
    loadState: 'loading',
    message: ''
  },
  onLoad(options) {
    this.setData({
      entityType: String(options.entityType || ''),
      entityId: Number(options.entityId || 0)
    })
    return this.fetchDetail()
  },
  fetchDetail() {
    if (!this.data.entityType || !this.data.entityId) {
      this.setData({ loadState: 'error', message: '详情参数不完整' })
      return Promise.resolve()
    }
    this.setData({ loadState: 'loading', message: '' })
    return request(
      '/miniapp/entities/' + encodeURIComponent(this.data.entityType) + '/' + this.data.entityId
    ).then((detail) => {
      this.setData({
        detail: Object.assign({}, detail, { status: statusLabel(String(detail.status || '')) }),
        loadState: 'success'
      })
    }).catch((error) => {
      console.error('[EntityDetail] load failed', error)
      const message = String(error && error.message || '')
      this.setData({
        detail: null,
        loadState: 'error',
        message: message === 'HTTP_403' || message === 'HTTP_404'
          ? '详情不存在或无权查看'
          : '详情加载失败，请重试'
      })
    })
  },
  onRetry() {
    return this.fetchDetail()
  },
  onBack() {
    wx.navigateBack()
  },
  onRelatedTap(event) {
    const entityType = String(event.currentTarget.dataset.entityType || '')
    const entityId = Number(event.currentTarget.dataset.entityId || 0)
    if (!entityType || !entityId) return
    wx.navigateTo({
      url: '/pages/entity-detail/index?entityType=' + encodeURIComponent(entityType) + '&entityId=' + entityId
    })
  }
})

module.exports = { createScreenPage, createEntityDetailPage }
`)

const wxml = `<view class="page">__HOME_BUTTON__
  <view class="hero">
    <view class="eyebrow">{{screen.group}} · {{screen.id}}</view>
    <view class="title">{{screen.title}}</view>
    <view class="subtitle">{{screen.subtitle}}</view>
    <view class="highlight">{{screen.highlight}}</view>
  </view>

  <view wx:if="{{isForm}}" class="panel">
    <view class="panel-title">输入与联调</view>
    <input class="input" value="{{keyword}}" bindinput="onInput" placeholder="{{placeholder}}" />__PROJECT_SEARCH__
  </view>

  <view class="panel">
    <view class="panel-head">
      <view class="panel-title">业务记录</view>
      <view class="state {{loadState}}">{{loadState}}</view>
    </view>
    __BUSINESS_ITEMS__
  </view>

  <view class="message" wx:if="{{message}}">{{message}}</view>
  __PAGE_ACTIONS__
</view>
`

const defaultBusinessItemsWxml = `<view
      wx:for="{{items}}"
      wx:key="id"
      class="item"
      data-entity-type="{{item.detailRef.entity_type}}"
      data-entity-id="{{item.detailRef.entity_id}}"
      bindtap="onBusinessItemTap"
    >
      <view class="item-main">
        <view class="item-title">{{item.title}}</view>
        <view class="item-desc">{{item.description}}</view>
      </view>
      <view class="badge">{{item.status}}</view>
      <view wx:if="{{item.detailRef}}" class="detail-chevron">›</view>
    </view>`

const taskBusinessItemsWxml = `<view class="task-selection">已选择 {{selectedTaskIds.length}} 项任务</view>
    <view wx:for="{{items}}" wx:key="id" class="item task-item">
      <view
        class="task-checkbox {{item.selected ? 'selected' : ''}}"
        data-id="{{item.entityId}}"
        catchtap="onTaskCheck"
      >{{item.selected ? '✓' : ''}}</view>
      <view class="item-main" data-id="{{item.entityId}}" bindtap="onTaskToggleDetail">
        <view class="item-title">{{item.title}}</view>
        <view class="item-desc {{item.expanded ? 'expanded' : ''}}">{{item.description}}</view>
        <view wx:if="{{item.expanded}}" class="task-details">{{item.details || '暂无更多任务信息'}}</view>
      </view>
      <view class="badge">{{item.status}}</view>
      <view
        wx:if="{{item.detailRef}}"
        class="detail-chevron"
        data-entity-type="{{item.detailRef.entity_type}}"
        data-entity-id="{{item.detailRef.entity_id}}"
        catchtap="onBusinessItemTap"
      >›</view>
    </view>`

const defaultActionsWxml = `<block wx:if="{{screen.id === 'S01'}}">
    <button class="primary" open-type="getPhoneNumber" bindgetphonenumber="onGetPhoneNumber">{{screen.primaryAction}}</button>
  </block>
  <block wx:else>
    <button class="primary" bindtap="onPrimaryTap">{{screen.primaryAction}}</button>
  </block>`

const taskActionsWxml = `<view class="task-actions">
    <button
      class="primary"
      data-action="accept"
      disabled="{{loadState === 'loading' || !selectedTaskIds.length}}"
      bindtap="onBatchTaskAction"
    >接受选中</button>
    <button
      class="reject"
      data-action="reject"
      disabled="{{loadState === 'loading' || !selectedTaskIds.length}}"
      bindtap="onBatchTaskAction"
    >拒绝接单</button>
  </view>`

const projectSearchWxml = `
    <view wx:if="{{candidateGroups.length}}" class="candidate-groups">
      <view wx:for="{{candidateGroups}}" wx:key="key" wx:for-item="group" wx:for-index="groupIndex" class="candidate-group">
        <view class="candidate-group-label">{{group.label}}</view>
        <view class="candidate-list">
          <view
            wx:for="{{group.items}}"
            wx:key="key"
            wx:for-item="candidate"
            wx:for-index="itemIndex"
            class="candidate-item"
            data-group-index="{{groupIndex}}"
            data-item-index="{{itemIndex}}"
            bindtap="onCandidateTap"
          >
            <view class="candidate-main">
              <view class="candidate-title">{{candidate.label}}</view>
              <view wx:if="{{candidate.description}}" class="candidate-description">{{candidate.description}}</view>
            </view>
            <view class="candidate-action">选择</view>
          </view>
        </view>
      </view>
    </view>
    <view wx:if="{{candidateSearchOpen}}" class="search-dropdown">
      <view wx:if="{{candidateSearchLoading}}" class="search-state">正在搜索数据库...</view>
      <block wx:elif="{{candidateSearchGroups.length}}">
        <view wx:for="{{candidateSearchGroups}}" wx:key="key" wx:for-item="group" wx:for-index="groupIndex" class="search-group">
          <view class="search-group-label">{{group.label}}</view>
          <view
            wx:for="{{group.items}}"
            wx:key="key"
            wx:for-item="candidate"
            wx:for-index="itemIndex"
            class="search-suggestion"
            data-group-index="{{groupIndex}}"
            data-item-index="{{itemIndex}}"
            bindtap="onCandidateSearchTap"
          >
            <view class="search-suggestion-main">
              <view class="search-suggestion-title">{{candidate.label}}</view>
              <view class="search-suggestion-description">{{candidate.description}}</view>
            </view>
            <view class="search-suggestion-action">选择</view>
          </view>
        </view>
      </block>
      <view wx:else class="search-state">未找到匹配数据</view>
    </view>`

const wxss = `.page {
  min-height: 100vh;
  padding: 32rpx;
  background: linear-gradient(180deg, #eef4ff 0%, #f7f8fb 42%, #f7f8fb 100%);
}
.hero {
  padding: 40rpx 32rpx;
  border-radius: 24rpx;
  background: #fff;
  box-shadow: 0 10rpx 30rpx rgba(20, 38, 76, .08);
}
.eyebrow {
  color: #2864dc;
  font-size: 24rpx;
  font-weight: 600;
}
.title {
  margin-top: 16rpx;
  color: #101828;
  font-size: 44rpx;
  font-weight: 700;
  line-height: 1.2;
}
.subtitle {
  margin-top: 16rpx;
  color: #4e5969;
  font-size: 28rpx;
  line-height: 1.55;
}
.highlight {
  display: inline-flex;
  margin-top: 24rpx;
  padding: 10rpx 18rpx;
  border-radius: 999rpx;
  color: #0f3f91;
  background: #e8f1ff;
  font-size: 24rpx;
}
.panel {
  margin-top: 24rpx;
  padding: 28rpx;
  border-radius: 20rpx;
  background: #fff;
  box-shadow: 0 8rpx 24rpx rgba(20, 38, 76, .06);
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.panel-title {
  color: #1d2129;
  font-size: 30rpx;
  font-weight: 700;
}
.state {
  padding: 8rpx 14rpx;
  border-radius: 999rpx;
  color: #4e5969;
  background: #f2f3f5;
  font-size: 22rpx;
}
.state.success {
  color: #16763b;
  background: #e8ffea;
}
.state.example {
  color: #9a5b00;
  background: #fff3df;
}
.input {
  margin-top: 20rpx;
  height: 80rpx;
  padding: 0 24rpx;
  border-radius: 16rpx;
  background: #f5f7fb;
  color: #1d2129;
}
.item {
  display: flex;
  gap: 20rpx;
  justify-content: space-between;
  margin-top: 20rpx;
  padding: 24rpx 0;
  border-top: 1rpx solid #eef0f5;
}
.item-main {
  min-width: 0;
}
.item-title {
  color: #1d2129;
  font-size: 28rpx;
  font-weight: 600;
}
.item-desc {
  margin-top: 8rpx;
  color: #667085;
  font-size: 24rpx;
  line-height: 1.5;
}
.badge {
  flex: 0 0 auto;
  align-self: flex-start;
  max-width: 180rpx;
  padding: 8rpx 14rpx;
  border-radius: 999rpx;
  color: #2864dc;
  background: #edf4ff;
  font-size: 22rpx;
}
.detail-chevron {
  flex: 0 0 auto;
  color: #8893a7;
  font-size: 40rpx;
  line-height: 1;
}
.message {
  margin-top: 24rpx;
  padding: 20rpx 24rpx;
  border-radius: 16rpx;
  color: #7a4a00;
  background: #fff7e6;
  font-size: 24rpx;
}
.primary {
  margin-top: 32rpx;
  width: 100%;
  height: 92rpx;
  border-radius: 999rpx;
  color: #fff;
  background: linear-gradient(135deg, #2864dc 0%, #0e42a8 100%);
  font-size: 30rpx;
  font-weight: 700;
}
`

const homeWxss = `.home-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 88rpx;
  height: 64rpx;
  padding: 0 16rpx;
  margin: 24rpx 0 0 32rpx;
  color: #2864dc;
  font-size: 24rpx;
  font-weight: 600;
  line-height: 64rpx;
  background: #e8f0ff;
  border: 1rpx solid #d3e1ff;
  border-radius: 32rpx;
}
`

const projectSearchWxss = `.search-dropdown {
  max-height: 560rpx;
  margin-top: 12rpx;
  padding: 8rpx 20rpx;
  overflow-y: auto;
  border: 1rpx solid #dce2ec;
  border-radius: 12rpx;
  background: #fff;
  box-shadow: 0 8rpx 32rpx rgba(0, 0, 0, .15);
}
.candidate-groups {
  margin-top: 24rpx;
}
.candidate-group + .candidate-group {
  margin-top: 24rpx;
}
.candidate-group-label {
  margin-bottom: 12rpx;
  color: #566176;
  font-size: 24rpx;
  font-weight: 600;
}
.candidate-list {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1rpx solid #e5eaf2;
  border-radius: 12rpx;
}
.candidate-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  min-height: 88rpx;
  padding: 16rpx 20rpx;
  background: #fff;
}
.candidate-item + .candidate-item {
  border-top: 1rpx solid #edf0f5;
}
.candidate-item:active {
  background: #eef2f7;
}
.candidate-main {
  min-width: 0;
  flex: 1;
}
.candidate-title,
.candidate-description {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.candidate-title {
  color: #172033;
  font-size: 28rpx;
  font-weight: 600;
}
.candidate-description {
  margin-top: 6rpx;
  color: #667085;
  font-size: 22rpx;
}
.candidate-action {
  flex: none;
  color: #2864dc;
  font-size: 24rpx;
  font-weight: 600;
}
.search-group {
  padding: 16rpx 0 8rpx;
}
.search-group + .search-group {
  border-top: 1rpx solid #edf0f5;
}
.search-group-label {
  padding: 0 8rpx 8rpx;
  color: #8893a7;
  font-size: 22rpx;
  font-weight: 600;
}
.search-suggestion {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  min-height: 88rpx;
  padding: 12rpx 8rpx;
  border-radius: 8rpx;
}
.search-suggestion:active {
  background: #eef2f7;
}
.search-suggestion-main {
  min-width: 0;
  flex: 1;
}
.search-suggestion-title,
.search-suggestion-description {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.search-suggestion-title {
  color: #172033;
  font-size: 28rpx;
  font-weight: 600;
}
.search-suggestion-description {
  margin-top: 6rpx;
  color: #566176;
  font-size: 22rpx;
}
.search-suggestion-action {
  flex: none;
  color: #2864dc;
  font-size: 24rpx;
  font-weight: 600;
}
.search-state {
  padding: 28rpx 8rpx;
  color: #8893a7;
  font-size: 24rpx;
  text-align: center;
}
`

const taskWxss = `.task-selection {
  padding: 20rpx 0 4rpx;
  color: #667085;
  font-size: 24rpx;
}
.task-item {
  align-items: flex-start;
}
.task-checkbox {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 38rpx;
  width: 38rpx;
  height: 38rpx;
  margin-top: 2rpx;
  color: #fff;
  font-size: 22rpx;
  font-weight: 700;
  border: 2rpx solid #dce2ec;
  border-radius: 6rpx;
}
.task-checkbox.selected {
  background: #2864dc;
  border-color: #2864dc;
}
.item-desc.expanded {
  overflow: visible;
  white-space: normal;
}
.task-details {
  padding: 16rpx;
  margin-top: 14rpx;
  color: #566176;
  font-size: 22rpx;
  line-height: 1.6;
  background: #eef2f7;
  border-left: 4rpx solid #2864dc;
  border-radius: 6rpx;
}
.task-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16rpx;
  margin-top: 32rpx;
}
.task-actions .primary,
.task-actions .reject {
  width: 100%;
  min-width: 0;
  margin-top: 0;
}
.reject {
  height: 92rpx;
  border: 1rpx solid #e6a5a0;
  border-radius: 999rpx;
  color: #a72424;
  background: #fff;
  font-size: 30rpx;
  font-weight: 700;
}
`

const entityDetailWxml = `<scroll-view class="detail-page" scroll-y>
  <view class="detail-topbar">
    <button class="detail-back" bindtap="onBack">‹</button>
    <view class="detail-page-title">业务详情</view>
    <view class="detail-spacer"></view>
  </view>

  <view wx:if="{{loadState === 'loading'}}" class="detail-state">
    <view class="detail-loading-bar"></view>
    <view class="detail-state-title">正在加载详情</view>
  </view>

  <view wx:elif="{{loadState === 'error'}}" class="detail-state">
    <view class="detail-state-title">{{message}}</view>
    <view class="detail-state-desc">返回上一页或重新读取最新数据。</view>
    <view class="detail-state-actions">
      <button class="detail-secondary" bindtap="onBack">返回</button>
      <button class="detail-primary" bindtap="onRetry">重新加载</button>
    </view>
  </view>

  <block wx:elif="{{detail}}">
    <image wx:if="{{detail.media_url}}" class="detail-media" src="{{detail.media_url}}" mode="aspectFill" lazy-load />
    <view class="detail-hero">
      <view class="detail-type">{{detail.entity_type}}</view>
      <view class="detail-title">{{detail.title}}</view>
      <view wx:if="{{detail.subtitle}}" class="detail-subtitle">{{detail.subtitle}}</view>
      <view wx:if="{{detail.status}}" class="detail-status">{{detail.status}}</view>
    </view>

    <view wx:if="{{detail.fields.length}}" class="detail-section">
      <view class="detail-section-title">关键信息</view>
      <view class="detail-fields">
        <view wx:for="{{detail.fields}}" wx:key="key" class="detail-field">
          <view class="detail-label">{{item.label}}</view>
          <view class="detail-value">{{item.value}}</view>
        </view>
      </view>
    </view>

    <view wx:for="{{detail.sections}}" wx:key="key" class="detail-section">
      <view class="detail-section-title">{{item.title}}</view>
      <view class="detail-content">{{item.content}}</view>
    </view>

    <view wx:if="{{detail.related_items.length}}" class="detail-section">
      <view class="detail-section-title">关联记录</view>
      <view
        wx:for="{{detail.related_items}}"
        wx:key="title"
        class="detail-related"
        data-entity-type="{{item.detail_ref.entity_type}}"
        data-entity-id="{{item.detail_ref.entity_id}}"
        bindtap="onRelatedTap"
      >
        <view class="detail-related-main">
          <view class="detail-related-title">{{item.title}}</view>
          <view wx:if="{{item.subtitle}}" class="detail-related-subtitle">{{item.subtitle}}</view>
        </view>
        <view class="detail-related-chevron">›</view>
      </view>
    </view>
  </block>
</scroll-view>`

const entityDetailWxss = `.detail-page {
  min-height: 100vh;
  color: #172033;
  background: #f4f6f9;
}
.detail-topbar {
  display: grid;
  grid-template-columns: 72rpx 1fr 72rpx;
  align-items: center;
  min-height: 96rpx;
  padding: env(safe-area-inset-top) 32rpx 0;
  background: #fff;
  border-bottom: 1rpx solid #edf0f5;
}
.detail-back {
  width: 64rpx;
  height: 64rpx;
  padding: 0;
  margin: 0;
  color: #172033;
  background: transparent;
  font-size: 56rpx;
  line-height: 58rpx;
}
.detail-page-title {
  text-align: center;
  font-size: 28rpx;
  font-weight: 600;
}
.detail-media {
  display: block;
  width: 100%;
  height: 420rpx;
  background: #e9edf4;
}
.detail-hero,
.detail-section,
.detail-state {
  width: calc(100% - 64rpx);
  margin: 0 auto;
  box-sizing: border-box;
}
.detail-hero {
  padding: 40rpx 0 32rpx;
  border-bottom: 1rpx solid #dce2ec;
}
.detail-type {
  color: #2864dc;
  font-size: 22rpx;
  font-weight: 700;
  text-transform: uppercase;
}
.detail-title {
  margin-top: 12rpx;
  font-size: 42rpx;
  font-weight: 700;
  line-height: 1.3;
}
.detail-subtitle {
  margin-top: 14rpx;
  color: #566176;
  font-size: 28rpx;
  line-height: 1.5;
}
.detail-status {
  display: inline-flex;
  align-items: center;
  min-height: 48rpx;
  padding: 0 18rpx;
  margin-top: 24rpx;
  color: #1748a7;
  background: #e8f0ff;
  border-radius: 999rpx;
  font-size: 22rpx;
  font-weight: 600;
}
.detail-section {
  padding: 32rpx 0;
  border-bottom: 1rpx solid #dce2ec;
}
.detail-section-title {
  margin-bottom: 24rpx;
  font-size: 32rpx;
  font-weight: 700;
}
.detail-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24rpx 32rpx;
}
.detail-label {
  color: #8893a7;
  font-size: 22rpx;
}
.detail-value {
  margin-top: 8rpx;
  color: #172033;
  font-size: 28rpx;
  font-weight: 500;
  line-height: 1.5;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.detail-content {
  color: #566176;
  font-size: 28rpx;
  line-height: 1.8;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.detail-related {
  display: flex;
  align-items: center;
  min-height: 112rpx;
  border-top: 1rpx solid #edf0f5;
}
.detail-related-main {
  min-width: 0;
  flex: 1;
}
.detail-related-title {
  font-size: 28rpx;
  font-weight: 600;
}
.detail-related-subtitle {
  margin-top: 6rpx;
  color: #8893a7;
  font-size: 24rpx;
}
.detail-related-chevron {
  color: #8893a7;
  font-size: 44rpx;
}
.detail-state {
  padding: 96rpx 0;
  text-align: center;
}
.detail-loading-bar {
  width: 96rpx;
  height: 8rpx;
  margin: 0 auto 32rpx;
  background: #2864dc;
  border-radius: 999rpx;
}
.detail-state-title {
  font-size: 32rpx;
  font-weight: 700;
}
.detail-state-desc {
  margin-top: 16rpx;
  color: #566176;
  font-size: 24rpx;
}
.detail-state-actions {
  display: flex;
  gap: 16rpx;
  justify-content: center;
  margin-top: 32rpx;
}
.detail-primary,
.detail-secondary {
  min-width: 180rpx;
  height: 80rpx;
  padding: 0 28rpx;
  margin: 0;
  border-radius: 999rpx;
  font-size: 24rpx;
  font-weight: 600;
}
.detail-primary {
  color: #fff;
  background: #2864dc;
}
.detail-secondary {
  color: #2864dc;
  background: #e8f0ff;
}
`

const transparentPng = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=',
  'base64',
)
for (const [, , icon] of tabItems) {
  writeFileSync(resolve(dist, `assets/tabbar/${icon}.png`), transparentPng)
  writeFileSync(resolve(dist, `assets/tabbar/${icon}-selected.png`), transparentPng)
}

for (const [id, title] of screens) {
  const pageDir = resolve(dist, pagePath(id).replace('/index', ''))
  mkdirSync(pageDir, { recursive: true })
  writeFileSync(resolve(pageDir, 'index.json'), `${JSON.stringify({
    navigationBarTitleText: title,
    enablePullDownRefresh: true,
  }, null, 2)}\n`)
  writeFileSync(
    resolve(pageDir, 'index.wxml'),
    wxml
      .replace('__HOME_BUTTON__', id !== 'S01' && !tabScreenIds.has(id)
        ? '\n  <button class="home-button" bindtap="onHomeTap">主页</button>'
        : '')
      .replace('__PROJECT_SEARCH__', ['S13', 'S14', 'S15', 'S16'].includes(id) ? projectSearchWxml : '')
      .replace('__BUSINESS_ITEMS__', id === 'S56' ? taskBusinessItemsWxml : defaultBusinessItemsWxml)
      .replace('__PAGE_ACTIONS__', id === 'S56' ? taskActionsWxml : defaultActionsWxml),
  )
  writeFileSync(resolve(pageDir, 'index.wxss'), `${wxss}${id !== 'S01' && !tabScreenIds.has(id) ? homeWxss : ''}${['S13', 'S14', 'S15', 'S16'].includes(id) ? projectSearchWxss : ''}${id === 'S56' ? taskWxss : ''}`)
  writeFileSync(resolve(pageDir, 'index.js'), `const { createScreenPage } = require('../../common/runtime')

createScreenPage('${id}')
`)
}

const detailPageDir = resolve(dist, 'pages/entity-detail')
mkdirSync(detailPageDir, { recursive: true })
writeFileSync(resolve(detailPageDir, 'index.json'), `${JSON.stringify({
  navigationBarTitleText: '业务详情',
  navigationStyle: 'custom',
}, null, 2)}\n`)
writeFileSync(resolve(detailPageDir, 'index.wxml'), entityDetailWxml)
writeFileSync(resolve(detailPageDir, 'index.wxss'), entityDetailWxss)
writeFileSync(resolve(detailPageDir, 'index.js'), `const { createEntityDetailPage } = require('../../common/runtime')

createEntityDetailPage()
`)

console.log(`Generated WeChat devtools dist with ${screens.length} blueprint pages and one entity detail page.`)
