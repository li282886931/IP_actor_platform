const { screens, nextScreen, tabs } = require('./screens')
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
      projectSearchSections: [],
      projectSearchOpen: false,
      projectSearchLoading: false,
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
      if (screenId === 'S13') this.onProjectSearchInput(keyword)
    },
    onProjectSearchInput(keyword) {
      clearTimeout(this.projectSearchTimer)
      const normalized = String(keyword || '').trim()
      if (!normalized) {
        this.setData({ projectSearchSections: [], projectSearchOpen: false, projectSearchLoading: false })
        return
      }
      this.setData({ projectSearchOpen: true, projectSearchLoading: true })
      this.projectSearchTimer = setTimeout(() => {
        request('/miniapp/search' + query({ q: normalized })).then((result) => {
          const sections = (result.groups || [])
            .filter((group) => ['artist', 'project'].includes(group.entity_type))
            .map((group) => ({
              key: group.entity_type,
              label: group.label,
              items: (group.items || []).map((item) => ({
                id: item.entity_type + '-' + item.entity_id,
                sourceId: item.entity_id,
                kind: item.entity_type,
                title: item.label,
                description: item.description || '',
                artistName: item.entity_type === 'artist'
                  ? item.label
                  : item.value && item.value.artist_name || ''
              }))
            }))
          this.setData({
            projectSearchSections: sections.filter((section) => section.items.length),
            projectSearchLoading: false
          })
        }).catch((error) => {
          console.error('[S13] fuzzy search failed', normalized, error)
          this.setData({ projectSearchSections: [], projectSearchLoading: false })
        })
      }, 300)
    },
    onProjectSearchSelect(event) {
      const suggestion = event.currentTarget.dataset
      const draft = wx.getStorageSync(STORAGE_KEYS.projectDraft) || {}
      this.setData({ keyword: suggestion.title, projectSearchOpen: false })
      if (suggestion.kind === 'artist') {
        wx.setStorageSync(STORAGE_KEYS.projectDraft, Object.assign({}, draft, {
          artist_id: Number(suggestion.sourceId),
          artist_name: suggestion.artistName
        }))
        return
      }
      request('/projects/' + suggestion.sourceId).then((project) => {
        wx.setStorageSync(STORAGE_KEYS.projectDraft, Object.assign({}, draft, {
          name: project.name,
          type: project.type,
          artist_name: project.artist_name
        }))
      }).catch((error) => {
        console.error('[S13] project detail load failed', suggestion.sourceId, error)
        wx.setStorageSync(STORAGE_KEYS.projectDraft, Object.assign({}, draft, {
          name: suggestion.title,
          artist_name: suggestion.artistName
        }))
      })
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
        if (value) wx.setStorageSync(STORAGE_KEYS.apiBase, value.replace(/\/+$/, ''))
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
