import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { test } from 'node:test'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const appConfigPath = resolve(root, 'src/app.config.ts')

const screenIds = Array.from({ length: 84 }, (_, index) => `S${String(index + 1).padStart(2, '0')}`)
const apiPaths = [
  '/auth/web-login',
  '/auth/wechat-login',
  '/user-groups',
  '/users',
  '/tenants',
  '/tenants/switch',
  '/projects',
  '/finance/calculate',
  '/finance/breakeven',
  '/decisions',
  '/tasks',
  '/accept',
  '/facts',
  '/assumptions',
  '/evidences/upload',
  '/evidences',
  '/oss/uploads/initiate',
  '/oss/uploads/',
  '/parse-jobs',
  '/document-parse-jobs/',
  '/confirm-projects',
  '/gates',
  '/risks',
  '/agent/chat',
  '/cases/search',
  '/external-data/jobs',
  '/analysis-jobs',
  '/reports/',
  '/feasibility-report',
  '/analytics/dashboard',
  '/ticketing/summary',
  '/artists',
  '/ai/generate',
  '/shows',
  '/ping',
]

test('registers all 84 blueprint screens with complete page files', () => {
  const config = readFileSync(appConfigPath, 'utf8')

  for (const screenId of screenIds) {
    const slug = screenId.toLowerCase()
    const pageDir = resolve(root, `src/pages/${slug}`)
    assert.equal(existsSync(resolve(pageDir, 'index.tsx')), true, `${screenId} is missing index.tsx`)
    assert.equal(existsSync(resolve(pageDir, 'index.module.scss')), true, `${screenId} is missing index.module.scss`)
    assert.equal(existsSync(resolve(pageDir, 'index.config.ts')), true, `${screenId} is missing index.config.ts`)
    assert.match(config, new RegExp(`pages/${slug}/index`), `${screenId} is not registered`)
  }
})

test('maps all 84 screens to explicit context and write actions', () => {
  const mapPath = resolve(root, 'src/data/screenDataMap.ts')
  assert.equal(existsSync(mapPath), true, 'src/data/screenDataMap.ts is missing')
  const source = readFileSync(mapPath, 'utf8')
  const mappedIds = [...source.matchAll(/^\s{2}(S\d{2}):\s*\{/gm)].map((match) => match[1])

  assert.deepEqual(mappedIds.sort(), [...screenIds].sort())
  for (const screenId of screenIds) {
    assert.match(
      source,
      new RegExp(`${screenId}: \\{ requiredContext: \\[.*?\\], writeActions: \\[.*?\\] \\}`),
      `${screenId} must explicitly declare requiredContext and writeActions`,
    )
  }
  assert.doesNotMatch(source, /default\s*:/)
  assert.doesNotMatch(source, /(?:amount|count|highlight|items|profit|status|subtitle|title)\s*:/)
})

test('keeps frontend and backend screen id registries aligned', () => {
  const frontendSource = readFileSync(resolve(root, 'src/data/screenDataMap.ts'), 'utf8')
  const backendSource = readFileSync(resolve(root, '../app/miniapp_screens.py'), 'utf8')
  const frontendIds = [...frontendSource.matchAll(/^\s{2}(S\d{2}):\s*\{/gm)].map((match) => match[1]).sort()
  const backendIds = [...backendSource.matchAll(/_registration\('?(S\d{2})'?,/g)].map((match) => match[1]).sort()

  assert.deepEqual(frontendIds, backendIds)
})

test('keeps the documented API matrix aligned with all screen registries', () => {
  const frontendSource = readFileSync(resolve(root, 'src/data/screenDataMap.ts'), 'utf8')
  const backendSource = readFileSync(resolve(root, '../app/miniapp_screens.py'), 'utf8')
  const matrixSource = readFileSync(resolve(root, '../docs/miniapp-screen-api-matrix.md'), 'utf8')
  const frontendIds = [...frontendSource.matchAll(/^\s{2}(S\d{2}):\s*\{/gm)].map((match) => match[1]).sort()
  const backendIds = [...backendSource.matchAll(/_registration\('?(S\d{2})'?,/g)].map((match) => match[1]).sort()
  const matrixIds = [...matrixSource.matchAll(/^\|\s*(S\d{2})\s*\|/gm)].map((match) => match[1]).sort()

  assert.deepEqual(matrixIds, frontendIds)
  assert.deepEqual(matrixIds, backendIds)
})

test('configures the four primary tabs from the blueprint', () => {
  const config = readFileSync(appConfigPath, 'utf8')

  for (const pagePath of ['pages/s04/index', 'pages/s10/index', 'pages/s52/index', 'pages/s67/index']) {
    assert.match(config, new RegExp(pagePath), `${pagePath} is missing from tabBar`)
  }
})

test('maps every existing FastAPI capability in the mini program API service', () => {
  const apiPath = resolve(root, 'src/services/api.ts')
  assert.equal(existsSync(apiPath), true, 'src/services/api.ts is missing')
  const apiSource = readFileSync(apiPath, 'utf8')

  for (const path of apiPaths) {
    assert.match(apiSource, new RegExp(path.replaceAll('/', '\\/')), `${path} is not mapped`)
  }
})

test('keeps mini program runtime config in a dedicated config file', () => {
  const runtimeConfigPath = resolve(root, 'src/config/runtime.ts')
  const apiPath = resolve(root, 'src/services/api.ts')
  const blueprintPath = resolve(root, 'src/components/BlueprintScreen/index.tsx')
  assert.equal(existsSync(runtimeConfigPath), true, 'src/config/runtime.ts is missing')

  const runtimeConfig = readFileSync(runtimeConfigPath, 'utf8')
  const apiSource = readFileSync(apiPath, 'utf8')
  const blueprintSource = readFileSync(blueprintPath, 'utf8')

  assert.match(runtimeConfig, /DEFAULT_API_BASE/)
  assert.match(runtimeConfig, /REQUEST_TIMEOUT_MS/)
  assert.match(runtimeConfig, /STORAGE_KEYS/)
  assert.match(apiSource, /@\/config\/runtime/)
  assert.doesNotMatch(apiSource, /const DEFAULT_API_BASE/)
  assert.doesNotMatch(apiSource, /timeout:\s*120000/)
  assert.match(blueprintSource, /@\/config\/runtime/)
  assert.doesNotMatch(blueprintSource, /['"]starhub-[^'"]+['"]/)
})

test('keeps the existing AppID and points WeChat to the Taro build output', () => {
  const projectConfig = JSON.parse(readFileSync(resolve(root, 'project.config.json'), 'utf8'))

  assert.equal(projectConfig.appid, 'wx31ef37c8a392752b')
  assert.equal(projectConfig.miniprogramRoot, 'dist/')
})

test('disables request domain checking for local FastAPI integration', () => {
  const projectConfig = JSON.parse(readFileSync(resolve(root, 'project.config.json'), 'utf8'))
  const privateConfig = JSON.parse(readFileSync(resolve(root, 'project.private.config.json'), 'utf8'))

  assert.equal(projectConfig.setting.urlCheck, false)
  assert.equal(privateConfig.setting.urlCheck, false)
})

test('provides a WeChat devtools dist app and all declared page entries', () => {
  const appJsonPath = resolve(root, 'dist/app.json')
  assert.equal(existsSync(appJsonPath), true, 'dist/app.json is missing')

  const appJson = JSON.parse(readFileSync(appJsonPath, 'utf8'))
  assert.equal(appJson.pages.length, 84)

  for (const pagePath of appJson.pages) {
    const pageDir = resolve(root, 'dist', pagePath)
    assert.equal(existsSync(`${pageDir}.json`), true, `${pagePath}.json is missing`)
    assert.equal(existsSync(`${pageDir}.wxml`), true, `${pagePath}.wxml is missing`)
    assert.equal(existsSync(`${pageDir}.wxss`), true, `${pagePath}.wxss is missing`)
    assert.equal(existsSync(`${pageDir}.js`), true, `${pagePath}.js is missing`)
  }
})

test('stores the tenant and refreshed token returned by tenant switching', () => {
  const source = readFileSync(resolve(root, 'src/components/BlueprintScreen/index.tsx'), 'utf8')

  assert.match(source, /switched\.current_tenant/)
  assert.match(source, /switched\.token/)
})

test('uses redirect navigation for sequential flows to avoid the WeChat page stack limit', () => {
  const source = readFileSync(resolve(root, 'src/components/BlueprintScreen/index.tsx'), 'utf8')

  assert.match(source, /Taro\.redirectTo/)
  assert.match(source, /replaceWithScreen\(target\)/)
})

test('keeps the five-step project creation flow moving forward', () => {
  const source = readFileSync(resolve(root, 'src/components/BlueprintScreen/index.tsx'), 'utf8')
  const generator = readFileSync(resolve(root, 'tools/generate-wechat-dist.mjs'), 'utf8')

  for (const [from, to] of [['S13', 'S14'], ['S14', 'S15'], ['S15', 'S16'], ['S16', 'S17']]) {
    const mapping = new RegExp(`${from}: ['"]${to}['"]`)
    assert.match(source, mapping, `${from} should continue to ${to} in Taro source`)
    assert.match(generator, mapping, `${from} should continue to ${to} in generated WeChat runtime`)
  }
})

test('creates the project and stores returned ids before leaving S17', async () => {
  const runtimePath = resolve(root, 'dist/common/runtime.js')
  const draft = {
    name: '真实项目',
    type: 'concert',
    artist_name: '真实艺人',
    city: '南京',
  }
  const storage = new Map([['starhub-project-draft', draft]])
  const requests = []
  const navigations = []
  let page
  globalThis.wx = {
    getStorageSync: (key) => storage.get(key),
    setStorageSync: (key, value) => storage.set(key, value),
    removeStorageSync: (key) => storage.delete(key),
    request: (options) => {
      requests.push(options)
      options.success({
        statusCode: 200,
        data: {
          code: 0,
          data: { id: 42, current_version_id: 7 },
          message: 'ok',
        },
      })
    },
    redirectTo: ({ url }) => navigations.push(url),
    switchTab: ({ url }) => navigations.push(url),
  }
  globalThis.Page = (definition) => {
    page = {
      ...definition,
      data: { ...definition.data },
      setData(next, callback) {
        this.data = { ...this.data, ...next }
        callback?.()
      },
    }
  }

  const require = createRequire(import.meta.url)
  delete require.cache[runtimePath]
  try {
    require(runtimePath).createScreenPage('S17')
    await page.onPrimaryTap()

    const createRequest = requests.find((request) => request.url.endsWith('/projects'))
    assert.equal(createRequest.method, 'POST')
    assert.deepEqual(createRequest.data, draft)
    assert.equal(storage.get('starhub-project-id'), 42)
    assert.equal(storage.get('starhub-version-id'), 7)
    assert.equal(storage.has('starhub-project-draft'), false)
    assert.deepEqual(navigations, ['/pages/s74/index'])
  } finally {
    delete globalThis.wx
    delete globalThis.Page
    delete require.cache[runtimePath]
  }
})

test('returns from S74 to the project list when no project id exists', () => {
  const runtimePath = resolve(root, 'dist/common/runtime.js')
  const navigations = []
  let page
  globalThis.wx = {
    getStorageSync: () => undefined,
    switchTab: ({ url }) => navigations.push({ method: 'switchTab', url }),
    redirectTo: ({ url }) => navigations.push({ method: 'redirectTo', url }),
  }
  globalThis.Page = (definition) => {
    page = {
      ...definition,
      data: { ...definition.data },
      setData(next) {
        this.data = { ...this.data, ...next }
      },
    }
  }

  const require = createRequire(import.meta.url)
  delete require.cache[runtimePath]
  try {
    require(runtimePath).createScreenPage('S74')
    page.onPrimaryTap()

    assert.deepEqual(navigations, [
      { method: 'switchTab', url: '/pages/s10/index' },
    ])
  } finally {
    delete globalThis.wx
    delete globalThis.Page
    delete require.cache[runtimePath]
  }
})

test('stores the S52 default project before opening the generated agent plan', async () => {
  const runtimePath = resolve(root, 'dist/common/runtime.js')
  const storage = new Map()
  const navigations = []
  let page
  globalThis.wx = {
    getStorageSync: (key) => storage.get(key),
    setStorageSync: (key, value) => storage.set(key, value),
    request: (options) => options.success({
      statusCode: 200,
      data: {
        code: 0,
        data: {
          screen_id: 'S52',
          summary: { title: '今日工作' },
          items: [],
          options: {
            default_project_id: 42,
            available_projects: [{ id: 42, name: '真实项目', status: 'active' }],
          },
          context: {},
          empty_state: null,
        },
        message: 'ok',
      },
    }),
    stopPullDownRefresh: () => {},
    redirectTo: ({ url }) => navigations.push(url),
    switchTab: ({ url }) => navigations.push(url),
  }
  globalThis.Page = (definition) => {
    page = {
      ...definition,
      data: { ...definition.data },
      setData(next, callback) {
        this.data = { ...this.data, ...next }
        callback?.()
      },
    }
  }

  const require = createRequire(import.meta.url)
  delete require.cache[runtimePath]
  try {
    require(runtimePath).createScreenPage('S52')
    await page.fetchRemote()
    page.onPrimaryTap()

    assert.equal(storage.get('starhub-project-id'), 42)
    assert.deepEqual(navigations, ['/pages/s53/index'])
  } finally {
    delete globalThis.wx
    delete globalThis.Page
    delete require.cache[runtimePath]
  }
})

test('returns generated S52 to the project list when no project exists', async () => {
  const runtimePath = resolve(root, 'dist/common/runtime.js')
  const navigations = []
  let page
  globalThis.wx = {
    getStorageSync: () => undefined,
    request: (options) => options.success({
      statusCode: 200,
      data: {
        code: 0,
        data: {
          screen_id: 'S52',
          summary: { title: '今日工作' },
          items: [],
          options: { default_project_id: null, available_projects: [] },
          context: {},
          empty_state: null,
        },
        message: 'ok',
      },
    }),
    stopPullDownRefresh: () => {},
    redirectTo: ({ url }) => navigations.push({ method: 'redirectTo', url }),
    switchTab: ({ url }) => navigations.push({ method: 'switchTab', url }),
  }
  globalThis.Page = (definition) => {
    page = {
      ...definition,
      data: { ...definition.data },
      setData(next, callback) {
        this.data = { ...this.data, ...next }
        callback?.()
      },
    }
  }

  const require = createRequire(import.meta.url)
  delete require.cache[runtimePath]
  try {
    require(runtimePath).createScreenPage('S52')
    await page.fetchRemote()
    page.onPrimaryTap()

    assert.deepEqual(navigations, [
      { method: 'switchTab', url: '/pages/s10/index' },
    ])
  } finally {
    delete globalThis.wx
    delete globalThis.Page
    delete require.cache[runtimePath]
  }
})

test('supports partial batch acceptance and rejection from the task detail screen', () => {
  const source = readFileSync(resolve(root, 'src/components/BlueprintScreen/index.tsx'), 'utf8')
  const styles = readFileSync(resolve(root, 'src/components/BlueprintScreen/index.module.scss'), 'utf8')
  const apiSource = readFileSync(resolve(root, 'src/services/api.ts'), 'utf8')
  const generator = readFileSync(resolve(root, 'tools/generate-wechat-dist.mjs'), 'utf8')

  assert.match(apiSource, /batchTaskAction/)
  assert.match(apiSource, /tasks\/actions\/batch/)
  assert.match(source, /selectedTaskIds/)
  assert.match(source, /expandedTaskIds/)
  assert.match(source, /toggleTaskSelection/)
  assert.match(source, /toggleTaskDetails/)
  assert.match(source, /runBatchTaskAction\(['"]accept['"]\)/)
  assert.match(source, /runBatchTaskAction\(['"]reject['"]\)/)
  assert.match(source, /await api\.batchTaskAction/)
  assert.match(styles, /\.taskCheckbox/)
  assert.match(styles, /\.taskDetails/)
  assert.match(styles, /\.taskActions/)

  assert.match(generator, /selectedTaskIds/)
  assert.match(generator, /expandedTaskIds/)
  assert.match(generator, /onTaskCheck/)
  assert.match(generator, /onTaskToggleDetail/)
  assert.match(generator, /onBatchTaskAction/)
  assert.match(generator, /\/tasks\/actions\/batch/)
  assert.match(generator, /data-id="{{item\.entityId}}"/)
})

test('generates an interactive S56 batch task screen and sends selected task ids', async () => {
  const runtimePath = resolve(root, 'dist/common/runtime.js')
  const s56Wxml = readFileSync(resolve(root, 'dist/pages/s56/index.wxml'), 'utf8')
  const s56Wxss = readFileSync(resolve(root, 'dist/pages/s56/index.wxss'), 'utf8')

  assert.match(s56Wxml, /catchtap="onTaskCheck"/)
  assert.match(s56Wxml, /bindtap="onTaskToggleDetail"/)
  assert.match(s56Wxml, /data-action="accept"/)
  assert.match(s56Wxml, /data-action="reject"/)
  assert.match(s56Wxss, /\.task-checkbox/)
  assert.match(s56Wxss, /\.task-actions/)

  const requests = []
  const storage = new Map([['starhub-task-id', 1]])
  let page
  globalThis.wx = {
    getStorageSync: (key) => storage.get(key),
    setStorageSync: (key, value) => storage.set(key, value),
    request: (options) => {
      requests.push(options)
      const data = options.url.includes('/miniapp/screens/S56')
        ? {
            screen_id: 'S56',
            summary: { title: '批量处理任务' },
            items: [
              { id: 'task-1', title: '任务一', description: '详情一', status: 'pending', context: { task_id: 1 } },
              { id: 'task-2', title: '任务二', description: '详情二', status: 'pending', context: { task_id: 2 } },
            ],
            options: {},
            context: {},
            empty_state: null,
          }
        : { action: 'accept', updated_count: 2, tasks: [] }
      options.success({ statusCode: 200, data: { code: 0, data, message: 'ok' } })
    },
    stopPullDownRefresh: () => {},
  }
  globalThis.Page = (definition) => {
    page = {
      ...definition,
      data: { ...definition.data },
      setData(next, callback) {
        this.data = { ...this.data, ...next }
        callback?.()
      },
    }
  }

  const require = createRequire(import.meta.url)
  delete require.cache[runtimePath]
  try {
    require(runtimePath).createScreenPage('S56')
    await page.fetchRemote()
    page.onTaskCheck({ currentTarget: { dataset: { id: 2 } } })
    await page.executeBatchTaskAction('accept', '')

    const batchRequest = requests.find((request) => request.url.endsWith('/tasks/actions/batch'))
    assert.deepEqual(batchRequest.data.task_ids, [1, 2])
    assert.equal(batchRequest.data.action, 'accept')
    assert.deepEqual(page.data.selectedTaskIds, [])
    assert.match(page.data.message, /已接受 2 项任务/)
  } finally {
    delete globalThis.wx
    delete globalThis.Page
    delete require.cache[runtimePath]
  }
})

test('persists the initial project version after project creation', () => {
  const source = readFileSync(resolve(root, 'src/components/BlueprintScreen/index.tsx'), 'utf8')

  assert.match(source, /current_version_id/)
  assert.match(source, /STORAGE_KEYS\.versionId/)
})

test('starts evidence parsing and project analysis from the blueprint runtime', () => {
  const source = readFileSync(resolve(root, 'src/components/BlueprintScreen/index.tsx'), 'utf8')

  assert.match(source, /api\.createDocumentParseJob/)
  assert.match(source, /api\.runDocumentParseJob/)
  assert.match(source, /api\.createProjectAnalysisJob/)
})

test('uses WeChat phone authorization for mini program login', () => {
  const source = readFileSync(resolve(root, 'src/components/BlueprintScreen/index.tsx'), 'utf8')

  assert.match(source, /openType=['"]getPhoneNumber['"]/)
  assert.match(source, /onGetPhoneNumber=/)
  assert.match(source, /phone_code/)
  assert.match(source, /HTTP_503/)
  assert.doesNotMatch(source, /wechatLogin\(\{ code, name: '微信用户', group_code: 'B' \}\)/)
})

test('provides debounced artist and project fuzzy search on project creation step one', () => {
  const source = readFileSync(resolve(root, 'src/components/BlueprintScreen/index.tsx'), 'utf8')
  const searchSource = readFileSync(resolve(root, 'src/components/SearchSelect/index.tsx'), 'utf8')
  const searchStyles = readFileSync(resolve(root, 'src/components/SearchSelect/index.module.scss'), 'utf8')
  const generator = readFileSync(resolve(root, 'tools/generate-wechat-dist.mjs'), 'utf8')

  assert.match(source, /@\/components\/SearchSelect/)
  assert.match(source, /<SearchSelect/)
  assert.match(source, /projectSearchKeyword/)
  assert.match(source, /api\.searchMiniappEntities\(keyword\)/)
  assert.doesNotMatch(source, /Promise\.all\(\[api\.listArtists\(keyword\), api\.searchCases\(keyword\)\]\)/)
  assert.match(source, /selectProjectSearchSuggestion/)
  assert.match(source, /artist_id: Number\(suggestion\.entityId\)/)
  assert.match(source, /source_project_id: Number\(suggestion\.entityId\)/)
  assert.match(source, /venue_id: Number\(suggestion\.entityId\)/)
  assert.match(searchSource, /setTimeout\([^]*300\)/)
  assert.match(searchSource, /onSelect\(option\)/)
  assert.match(searchStyles, /\.dropdown/)
  assert.match(searchStyles, /\.option/)

  assert.match(generator, /projectSearchSections/)
  assert.match(generator, /request\('\/miniapp\/search'/)
  assert.doesNotMatch(generator, /request\('\/artists'[^]*request\('\/cases\/search'/)
  assert.match(generator, /onProjectSearchInput/)
  assert.match(generator, /onProjectSearchSelect/)
  assert.match(generator, /search-dropdown/)
})

test('removes fixture fallbacks and default entity ids from all mini program runtimes', () => {
  const source = readFileSync(resolve(root, 'src/components/BlueprintScreen/index.tsx'), 'utf8')
  const generator = readFileSync(resolve(root, 'tools/generate-wechat-dist.mjs'), 'utf8')
  const runtime = readFileSync(resolve(root, 'dist/common/runtime.js'), 'utf8')

  assert.equal(existsSync(resolve(root, 'src/data/fixtures.ts')), false)
  for (const content of [source, generator, runtime]) {
    assert.doesNotMatch(content, /getFixtureItems|fixtureItems|loadState:\s*['"]example['"]/)
    assert.doesNotMatch(content, /projectId\)\s*\|\|\s*1|taskId\)\s*\|\|\s*1/)
    assert.doesNotMatch(content, /产品示例数据|示例利润|\/projects\/1/)
  }
  assert.doesNotMatch(source, /screenData\?\.summary\.highlight\s*\|\|\s*screen\.highlight/)
  assert.match(generator, /screen:\s*Object\.assign\(\{\},\s*screen,\s*data\.summary/)
})

test('generated runtime loads every screen from the unified aggregation endpoint', async () => {
  const runtimePath = resolve(root, 'dist/common/runtime.js')
  const storage = new Map([
    ['starhub-token', 'dev-token-1-1'],
    ['starhub-tenant', { id: 1 }],
    ['starhub-project-id', 42],
    ['starhub-version-id', 7],
  ])
  const requests = []
  let page
  globalThis.wx = {
    getStorageSync: (key) => storage.get(key),
    setStorageSync: (key, value) => storage.set(key, value),
    request: (options) => {
      requests.push(options)
      options.success({
        statusCode: 200,
        data: {
          code: 0,
          data: {
            screen_id: 'S11',
            summary: { title: '真实项目', subtitle: null, highlight: 'draft' },
            items: [],
            options: {},
            context: { project_id: 42, version_id: 7 },
            empty_state: { title: '暂无业务记录', description: '等待真实数据' },
          },
          message: 'ok',
        },
      })
    },
    stopPullDownRefresh: () => {},
  }
  globalThis.Page = (definition) => {
    page = {
      ...definition,
      data: { ...definition.data },
      setData(next, callback) {
        this.data = { ...this.data, ...next }
        callback?.()
      },
    }
  }

  const require = createRequire(import.meta.url)
  delete require.cache[runtimePath]
  try {
    require(runtimePath).createScreenPage('S11')
    await page.fetchRemote()

    assert.match(requests[0].url, /\/miniapp\/screens\/S11\?/)
    assert.match(requests[0].url, /project_id=42/)
    assert.equal(page.data.items.length, 0)
    assert.equal(page.data.loadState, 'empty')
    assert.equal(page.data.message, '暂无业务记录')
  } finally {
    delete globalThis.wx
    delete globalThis.Page
    delete require.cache[runtimePath]
  }
})

test('generated runtime keeps an empty list and retry state after request failure', async () => {
  const runtimePath = resolve(root, 'dist/common/runtime.js')
  let page
  globalThis.wx = {
    getStorageSync: () => undefined,
    request: (options) => options.fail(new Error('offline')),
    stopPullDownRefresh: () => {},
  }
  globalThis.Page = (definition) => {
    page = {
      ...definition,
      data: { ...definition.data },
      setData(next, callback) {
        this.data = { ...this.data, ...next }
        callback?.()
      },
    }
  }

  const require = createRequire(import.meta.url)
  delete require.cache[runtimePath]
  try {
    require(runtimePath).createScreenPage('S04')
    await page.fetchRemote()

    assert.deepEqual(page.data.items, [])
    assert.equal(page.data.loadState, 'error')
    assert.match(page.data.message, /重试/)
  } finally {
    delete globalThis.wx
    delete globalThis.Page
    delete require.cache[runtimePath]
  }
})
