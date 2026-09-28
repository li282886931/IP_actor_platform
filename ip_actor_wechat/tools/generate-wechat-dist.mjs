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
  ['S52', 'Agent', 'agent'],
  ['S67', '我的', 'profile'],
]

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
  pages: screens.map(([id]) => pagePath(id)),
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

const normalizeItems = (values) => {
  if (!Array.isArray(values)) return []
  return values.map((value, index) => ({
    id: String(value.id || 'record-' + index),
    entityId: Number(value.context && (value.context.task_id || value.context.project_id) || 0),
    title: String(value.title || ''),
    description: String(value.description || ''),
    status: String(value.status || ''),
    value: value.value == null ? '' : String(value.value),
    details: String(value.details || '')
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
      if (screenId !== 'S55') return
      const taskId = Number(event.currentTarget.dataset.id || 0)
      if (!taskId) return
      wx.setStorageSync(STORAGE_KEYS.taskId, taskId)
      wx.redirectTo({ url: routeFor('S56') })
    },
    goNext() {
      const hasProject = Number(wx.getStorageSync(STORAGE_KEYS.projectId) || 0) > 0
      const target = screenId === 'S74' && !hasProject
        ? 'S10'
        : nextScreen[screenId] || 'S04'
      const url = routeFor(target)
      if (tabs.includes(target)) wx.switchTab({ url })
      else wx.redirectTo({ url })
    }
  })
}

module.exports = { createScreenPage }
`)

const wxml = `<view class="page">
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

const defaultBusinessItemsWxml = `<view wx:for="{{items}}" wx:key="id" class="item" data-id="{{item.entityId}}" bindtap="onBusinessItemTap">
      <view class="item-main">
        <view class="item-title">{{item.title}}</view>
        <view class="item-desc">{{item.description}}</view>
      </view>
      <view class="badge">{{item.status}}</view>
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
    <view wx:if="{{projectSearchOpen}}" class="search-dropdown">
      <view wx:if="{{projectSearchLoading}}" class="search-state">正在搜索数据库...</view>
      <block wx:elif="{{projectSearchSections.length}}">
        <view wx:for="{{projectSearchSections}}" wx:key="key" wx:for-item="section" class="search-group">
          <view class="search-group-label">{{section.label}}</view>
          <view
            wx:for="{{section.items}}"
            wx:key="id"
            wx:for-item="suggestion"
            class="search-suggestion"
            data-kind="{{suggestion.kind}}"
            data-title="{{suggestion.title}}"
            data-artist-name="{{suggestion.artistName}}"
            data-source-id="{{suggestion.sourceId}}"
            bindtap="onProjectSearchSelect"
          >
            <view class="search-suggestion-main">
              <view class="search-suggestion-title">{{suggestion.title}}</view>
              <view class="search-suggestion-description">{{suggestion.description}}</view>
            </view>
            <view class="search-suggestion-action">选择</view>
          </view>
        </view>
      </block>
      <view wx:else class="search-state">未找到匹配的艺人或历史项目</view>
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
      .replace('__PROJECT_SEARCH__', id === 'S13' ? projectSearchWxml : '')
      .replace('__BUSINESS_ITEMS__', id === 'S56' ? taskBusinessItemsWxml : defaultBusinessItemsWxml)
      .replace('__PAGE_ACTIONS__', id === 'S56' ? taskActionsWxml : defaultActionsWxml),
  )
  writeFileSync(resolve(pageDir, 'index.wxss'), `${wxss}${id === 'S13' ? projectSearchWxss : ''}${id === 'S56' ? taskWxss : ''}`)
  writeFileSync(resolve(pageDir, 'index.js'), `const { createScreenPage } = require('../../common/runtime')

createScreenPage('${id}')
`)
}

console.log(`Generated WeChat devtools dist with ${screens.length} pages.`)
