import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
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
