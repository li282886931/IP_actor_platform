import { mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { routeFor, screens } from './blueprint-manifest.mjs'

const root = resolve(import.meta.dirname, '..')
const dist = resolve(root, 'dist')

const tabItems = [
  ['S04', '发现', 'discover'],
  ['S10', '项目', 'project'],
  ['S52', 'Agent', 'agent'],
  ['S67', '我的', 'profile'],
]

const nextScreen = {
  S01: 'S02', S02: 'S03', S03: 'S04', S04: 'S13', S05: 'S11', S06: 'S07',
  S07: 'S13', S08: 'S13', S09: 'S06', S10: 'S13', S11: 'S34', S12: 'S49',
  S17: 'S74', S18: 'S16', S24: 'S25', S25: 'S29', S26: 'S25', S27: 'S25',
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

const fixtures = {
  认证: [
    ['可信身份', '登录后签发统一令牌，跨端身份保持一致', '安全'],
    ['客户隔离', '项目、资料和 Agent 按当前客户空间隔离', '最小权限'],
    ['人工确认', '政策、场地、授权与资金责任由负责人确认', '硬门禁'],
  ],
  发现: [
    ['华东万人场案例 A', '南京 · 12,000 席 · 已核验结算', '盈利'],
    ['城市剧场项目', '通过缩小规模降低资金风险', '可迁移'],
    ['十月档期机会', '同量级项目存在可比案例，档期仍需核验', '待证据'],
  ],
  项目: [
    ['星河计划·南京站', '艺人 A · 南京 · 2027 年 10 月', '调整后推进'],
    ['星河计划·杭州站', '档期与场馆报价待补充', '缺资料'],
    ['冬季剧场项目', '组合待选 · 2027 年 12 月', '草稿'],
  ],
  财务: [
    ['保守情景', '65% 上座率 · 利润缓冲较薄', '压力边界'],
    ['中性情景', '80% 上座率 · 当前判断口径', '条件推进'],
    ['乐观情景', '95% 上座率 · 不作为销售承诺', '上行空间'],
  ],
  依据: [
    ['可用资金 500 万', '资金确认单 · 已由负责人核验', '已核验'],
    ['可售规模 12,000 人', '项目输入 · 待场馆正式确认', '待确认'],
    ['场馆容量冲突', '项目输入 12,000 与资料 10,500', '需处理'],
  ],
  风险: [
    ['峰值资金缺口未落实', '中性情景缺口 94.61 万', '高风险'],
    ['艺人授权范围未核验', '影响履约、版权与正式签约', '高风险'],
    ['保守利润缓冲很薄', '65% 上座率利润仅 12.86 万', '中风险'],
  ],
  门禁: [
    ['政策与大型活动审批', '负责人已核验示意文件', '已确认'],
    ['场地承载、消防与安保', '容量冲突仍待消解', '待确认'],
    ['资金拨付与合同责任', '资金缺口和亏损承担待确认', '待确认'],
  ],
  Agent: [
    ['确认新增资金安排', '财务负责人 · 今天 18:00', '优先'],
    ['补充艺人授权文件', '商务负责人 · 明天 12:00', '待证据'],
    ['核对场馆报价口径', '地方执行 · 明天 18:00', '进行中'],
  ],
  任务: [
    ['确认资金安排', '今天 18:00 · 财务 · 未认领', '高优先'],
    ['补充艺人授权范围', '明天 12:00 · 商务', '进行中'],
    ['核对场馆售票区域', '明天 18:00 · 地方执行', '待处理'],
  ],
  我的: [
    ['团队与项目权限', '管理成员角色和项目可见范围', '可管理'],
    ['Agent 授权设置', '内部任务、提醒与对外行为', '最小权限'],
    ['数据授权与隐私', '连接、文件、可见范围与撤回', '可管理'],
  ],
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
    highlight: item[5],
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
    apiBase: 'http://127.0.0.1:8000'
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
const fixtures = ${JSON.stringify(fixtures, null, 2)}
const nextScreen = ${JSON.stringify(nextScreen, null, 2)}
const tabs = ${JSON.stringify(tabItems.map(([id]) => id), null, 2)}

module.exports = { screens, fixtures, nextScreen, tabs }
`)

writeFileSync(resolve(dist, 'common/runtime.js'), `const { screens, fixtures, nextScreen, tabs } = require('./screens')

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
        if (value) wx.setStorageSync('starhub-api-base', value.replace(/\\/+$/, ''))
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
    <input class="input" value="{{keyword}}" bindinput="onInput" placeholder="{{placeholder}}" />
  </view>

  <view class="panel">
    <view class="panel-head">
      <view class="panel-title">业务记录</view>
      <view class="state {{loadState}}">{{loadState}}</view>
    </view>
    <view wx:for="{{items}}" wx:key="id" class="item">
      <view class="item-main">
        <view class="item-title">{{item.title}}</view>
        <view class="item-desc">{{item.description}}</view>
      </view>
      <view class="badge">{{item.status}}</view>
    </view>
  </view>

  <view class="message" wx:if="{{message}}">{{message}}</view>
  <button class="primary" bindtap="onPrimaryTap">{{screen.primaryAction}}</button>
</view>
`

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
  writeFileSync(resolve(pageDir, 'index.wxml'), wxml)
  writeFileSync(resolve(pageDir, 'index.wxss'), wxss)
  writeFileSync(resolve(pageDir, 'index.js'), `const { createScreenPage } = require('../../common/runtime')

createScreenPage('${id}')
`)
}

console.log(`Generated WeChat devtools dist with ${screens.length} pages.`)
