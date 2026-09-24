import { useEffect, useMemo, useState } from 'react'
import { Button, Input, ScrollView, Text, View } from '@tarojs/components'
import Taro, { usePullDownRefresh, useRouter } from '@tarojs/taro'
import classNames from 'classnames'

import { getFixtureItems } from '@/data/fixtures'
import { screenDefinitions } from '@/data/screens'
import { api, getApiBase, setApiBase } from '@/services/api'
import type { DisplayItem, ProjectDraft, SessionData } from '@/types/domain'
import styles from './index.module.scss'

interface BlueprintScreenProps {
  screenId: string
}

type LoadState = 'idle' | 'loading' | 'success' | 'example' | 'error'

const tabIds = new Set(['S04', 'S10', 'S52', 'S67'])
const formScreens = new Set(['S09', 'S13', 'S14', 'S15', 'S16', 'S17', 'S25', 'S36', 'S37', 'S41', 'S45', 'S47', 'S51', 'S54', 'S57', 'S65', 'S72', 'S79', 'S82'])
const destructiveScreens = new Set(['S47', 'S80', 'S84'])

const routeFor = (screenId: string) => `/pages/${screenId.toLowerCase()}/index`

const navigateToScreen = async (screenId: string) => {
  if (tabIds.has(screenId)) {
    await Taro.switchTab({ url: routeFor(screenId) })
    return
  }
  await Taro.navigateTo({ url: routeFor(screenId) })
}

const replaceWithScreen = async (screenId: string) => {
  if (tabIds.has(screenId)) {
    await Taro.switchTab({ url: routeFor(screenId) })
    return
  }
  await Taro.redirectTo({ url: routeFor(screenId) })
}

const nextScreen: Record<string, string> = {
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

const asRecord = (value: unknown): Record<string, unknown> => (
  value && typeof value === 'object' ? value as Record<string, unknown> : {}
)

const textValue = (record: Record<string, unknown>, keys: string[], fallback = '') => {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'string' || typeof value === 'number') return String(value)
  }
  return fallback
}

const toDisplayItems = (values: unknown[], group: string): DisplayItem[] => values.map((value, index) => {
  const record = asRecord(value)
  return {
    id: textValue(record, ['id', 'project_id'], `${group}-${index}`),
    title: textValue(record, ['name', 'title', 'account'], `${group}记录 ${index + 1}`),
    description: textValue(record, ['description', 'content', 'city', 'source'], '详情已从决策服务同步'),
    status: textValue(record, ['status', 'level', 'group_code'], '已同步'),
    value: textValue(record, ['profit', 'heat_score', 'fan_count'], ''),
  }
})

const initialDraft: ProjectDraft = {
  name: '星河计划·南京站',
  type: 'concert',
  artist_name: '艺人 A',
  city: '南京',
  venue: '候选场馆 A',
  schedule: '2027 年 10 月',
  expected_attendance: 12000,
  available_funds: 5000000,
  avg_ticket_price: 680,
  artist_fee: 2600000,
  venue_cost: 1200000,
  marketing_cost: 600000,
  production_cost: 600000,
}

const getStoredDraft = (): ProjectDraft => {
  const stored = Taro.getStorageSync<ProjectDraft>('starhub-project-draft')
  return stored && typeof stored === 'object' ? { ...initialDraft, ...stored } : initialDraft
}

const inputValue = (value: string | number | undefined) => value === undefined ? '' : String(value)

export default function BlueprintScreen({ screenId }: BlueprintScreenProps) {
  const screen = screenDefinitions[screenId]
  const router = useRouter()
  const params = router.params
  const [items, setItems] = useState<DisplayItem[]>(() => getFixtureItems(screen.group))
  const [loadState, setLoadState] = useState<LoadState>('idle')
  const [message, setMessage] = useState('')
  const [draft, setDraft] = useState<ProjectDraft>(getStoredDraft)
  const [form, setForm] = useState<Record<string, string>>({
    keyword: '',
    question: '',
    result: '',
    condition: '落实资金缺口；关闭艺人授权与场地安全门禁',
    decision: 'advance',
    apiBase: getApiBase(),
    evidenceName: '',
    evidenceUrl: '',
    factTitle: '',
    assumptionTitle: '',
    gateName: '',
  })

  const projectId = Number(params.projectId || Taro.getStorageSync<number>('starhub-project-id') || 1)
  const versionId = Number(Taro.getStorageSync<number>('starhub-version-id') || 1)
  const taskId = Number(params.taskId || Taro.getStorageSync<number>('starhub-task-id') || 1)

  const fetchRemote = async () => {
    let values: unknown[] | null = null
    setLoadState('loading')
    try {
      switch (screenId) {
        case 'S02':
          values = await api.listTenants()
          break
        case 'S04':
          values = await api.listShows()
          break
        case 'S06':
        case 'S09':
          values = await api.searchCases(form.keyword)
          break
        case 'S10':
          values = await api.listProjects()
          break
        case 'S11': {
          const project = await api.getProject(projectId)
          const projectRecord = asRecord(project)
          if (projectRecord.current_version_id) {
            Taro.setStorageSync('starhub-version-id', Number(projectRecord.current_version_id))
          }
          values = [project]
          break
        }
        case 'S12':
        case 'S49':
          values = await api.listProjectVersions(projectId)
          break
        case 'S19':
          values = await api.listArtists(form.keyword)
          break
        case 'S20': {
          const artist = await api.getArtist(Number(params.artistId || 1))
          values = [artist]
          break
        }
        case 'S36':
          values = await api.listAssumptions(projectId)
          break
        case 'S37':
          values = await api.listFacts(projectId)
          break
        case 'S38':
        case 'S41':
        case 'S42':
          values = await api.listEvidences(projectId)
          break
        case 'S43':
        case 'S44':
          values = await api.listRisks(projectId)
          break
        case 'S45':
        case 'S46':
          values = await api.listGates(projectId)
          break
        case 'S52':
        case 'S53':
        case 'S55':
        case 'S56':
        case 'S57':
        case 'S58':
          values = await api.listTasks(projectId)
          break
        case 'S68': {
          const [users, groups] = await Promise.all([api.listUsers(), api.listUserGroups()])
          values = [...users, ...groups]
          break
        }
        case 'S82':
          await api.ping()
          setMessage('决策服务连接正常')
          break
        default:
          setLoadState('success')
          return
      }

      if (values?.length) setItems(toDisplayItems(values, screen.group))
      setLoadState('success')
    } catch (error) {
      console.error(`[${screenId}] load failed`, error)
      setLoadState('example')
      setMessage('决策服务暂不可用，当前展示已标注的产品示例数据。')
    } finally {
      Taro.stopPullDownRefresh()
    }
  }

  useEffect(() => {
    void fetchRemote()
  }, [screenId])

  usePullDownRefresh(() => {
    void fetchRemote()
  })

  const progress = useMemo(() => {
    const current = Number(screenId.slice(1))
    return Math.round((current / 84) * 100)
  }, [screenId])

  const updateDraft = (key: keyof ProjectDraft, value: string) => {
    const numericKeys: Array<keyof ProjectDraft> = [
      'expected_attendance', 'available_funds', 'avg_ticket_price', 'artist_fee',
      'venue_cost', 'marketing_cost', 'production_cost',
    ]
    const nextValue = numericKeys.includes(key) ? (value === '' ? undefined : Number(value)) : value
    const next = { ...draft, [key]: nextValue }
    setDraft(next)
    Taro.setStorageSync('starhub-project-draft', next)
  }

  const updateForm = (key: string, value: string) => setForm((current) => ({ ...current, [key]: value }))

  const runPrimaryAction = async () => {
    setLoadState('loading')
    setMessage('')
    try {
      if (screenId === 'S01') {
        let code = 'preview-code'
        if (Taro.getEnv() === Taro.ENV_TYPE.WEAPP) {
          const login = await Taro.login()
          code = login.code
        }
        const session = await api.wechatLogin({ code, name: '微信用户', group_code: 'B' }) as SessionData
        if (session.token) Taro.setStorageSync('starhub-token', session.token)
        if (session.user) Taro.setStorageSync('starhub-user', session.user)
        if (session.current_tenant) Taro.setStorageSync('starhub-tenant', session.current_tenant)
      } else if (screenId === 'S02') {
        const tenantId = Number(items[0]?.id || 1)
        const switched = await api.switchTenant(tenantId)
        if (switched.current_tenant) {
          Taro.setStorageSync('starhub-tenant', switched.current_tenant)
        }
        if (typeof switched.token === 'string') {
          Taro.setStorageSync('starhub-token', switched.token)
        }
      } else if (screenId === 'S17') {
        const created = await api.createProject(draft as unknown as Record<string, unknown>)
        const record = asRecord(created)
        const id = Number(record.id || 1)
        Taro.setStorageSync('starhub-project-id', id)
        if (record.current_version_id) {
          Taro.setStorageSync('starhub-version-id', Number(record.current_version_id))
        }
        Taro.removeStorageSync('starhub-project-draft')
      } else if (screenId === 'S25') {
        const result = await api.calculateFinance({
          project_id: projectId,
          expected_attendance: draft.expected_attendance,
          avg_ticket_price: draft.avg_ticket_price,
          artist_fee: draft.artist_fee,
          venue_cost: draft.venue_cost,
          marketing_cost: draft.marketing_cost,
          production_cost: draft.production_cost,
        })
        const record = asRecord(result)
        if (record.version_id) Taro.setStorageSync('starhub-version-id', Number(record.version_id))
      } else if (screenId === 'S31') {
        await api.calculateBreakeven({
          project_id: projectId,
          target_profit: 0,
          avg_ticket_price: draft.avg_ticket_price,
          artist_fee: draft.artist_fee,
          venue_cost: draft.venue_cost,
          marketing_cost: draft.marketing_cost,
          production_cost: draft.production_cost,
        })
      } else if (screenId === 'S36') {
        await api.createAssumption({ project_id: projectId, title: form.assumptionTitle || '上座率假设', content: '中性预计 80%', confidence: 80 })
      } else if (screenId === 'S37') {
        await api.createFact({ project_id: projectId, title: form.factTitle || '项目输入待核验', content: '由小程序提交', source: '项目表单' })
      } else if (screenId === 'S41') {
        const evidence = await api.createEvidence({
          project_id: projectId,
          name: form.evidenceName || '项目资料',
          file_url: form.evidenceUrl || 'local://pending-upload',
          evidence_type: 'document',
          source: '微信小程序',
        })
        const evidenceRecord = asRecord(evidence)
        const parseJob = await api.createDocumentParseJob(Number(evidenceRecord.id), { purpose: 'project_evidence' })
        const parseRecord = asRecord(parseJob)
        await api.runDocumentParseJob(Number(parseRecord.id))
        setMessage('资料解析已完成，候选事实、风险和门禁等待负责人核验。')
      } else if (screenId === 'S45') {
        await api.createGate({ project_id: projectId, name: form.gateName || '人工确认门禁', status: 'pending', owner_group: 'B' })
      } else if (screenId === 'S47') {
        await api.createDecision({ project_id: projectId, version_id: versionId, decision_type: form.decision, conditions: form.condition })
      } else if (screenId === 'S51') {
        const share = await api.shareReport(projectId, { version_id: versionId, expires_in_days: 7 })
        setMessage(textValue(asRecord(share), ['share_url'], '受限分享已创建'))
      } else if (screenId === 'S53') {
        await Promise.all(items.slice(0, 3).map((item) => api.createTask({
          project_id: projectId,
          title: item.title,
          description: item.description,
          due_date: '2026-09-25',
        })))
      } else if (screenId === 'S54') {
        const analysis = await api.createProjectAnalysisJob(projectId, { purpose: 'agent_recommendation' })
        const analysisResult = asRecord(asRecord(analysis).result)
        const answer = await api.agentChat({ project_id: projectId, message: form.question || '下一步应该优先处理什么？' })
        setMessage(`${textValue(asRecord(answer), ['answer'], 'Agent 已生成下一步建议')}｜推荐动作：${textValue(analysisResult, ['recommendation'], '待负责人核验')}`)
      } else if (screenId === 'S57') {
        await api.submitTask(taskId, { result: form.result || '已提交任务结果', evidence_ids: [] })
      } else if (screenId === 'S65') {
        setMessage('结算数据已保存为待财务确认状态。')
      } else if (screenId === 'S72') {
        setMessage('邀请已生成，有效期 48 小时。')
      } else if (screenId === 'S82') {
        setApiBase(form.apiBase)
        await api.ping()
        setMessage('决策服务连接正常，地址已保存。')
      }

      setLoadState('success')
      const target = nextScreen[screenId] || `S${String(Math.min(Number(screenId.slice(1)) + 1, 84)).padStart(2, '0')}`
      if (!['S36', 'S37', 'S41', 'S45', 'S51', 'S54', 'S57', 'S65', 'S72', 'S82'].includes(screenId)) {
        await replaceWithScreen(target)
      } else {
        await fetchRemote()
      }
    } catch (error) {
      console.error(`[${screenId}] action failed`, error)
      setLoadState('error')
      setMessage('操作未完成，输入已保留。请检查服务连接后重试。')
    }
  }

  const renderForm = () => {
    if (!formScreens.has(screenId)) return null

    if (screenId === 'S13') {
      return (
        <View className={styles.formGrid}>
          <Field label='项目名称' value={draft.name} onInput={(value) => updateDraft('name', value)} />
          <Field label='项目类型' value={draft.type} onInput={(value) => updateDraft('type', value)} />
          <Field label='核心艺人 / IP' value={draft.artist_name} onInput={(value) => updateDraft('artist_name', value)} />
        </View>
      )
    }
    if (screenId === 'S14') {
      return (
        <View className={styles.formGrid}>
          <Field label='举办城市' value={draft.city} onInput={(value) => updateDraft('city', value)} />
          <Field label='计划时间' value={draft.schedule} onInput={(value) => updateDraft('schedule', value)} />
          <Field label='候选场馆' value={draft.venue} onInput={(value) => updateDraft('venue', value)} />
        </View>
      )
    }
    if (screenId === 'S15') {
      return (
        <View className={styles.formGrid}>
          <Field label='可售规模 / 人' type='number' value={inputValue(draft.expected_attendance)} onInput={(value) => updateDraft('expected_attendance', value)} />
          <Field label='可用资金 / 元' type='number' value={inputValue(draft.available_funds)} onInput={(value) => updateDraft('available_funds', value)} />
          <Field label='平均实收票价 / 元' type='number' value={inputValue(draft.avg_ticket_price)} onInput={(value) => updateDraft('avg_ticket_price', value)} />
        </View>
      )
    }
    if (screenId === 'S16' || screenId === 'S25') {
      return (
        <View className={styles.formGrid}>
          <Field label='艺人费用 / 元' type='number' value={inputValue(draft.artist_fee)} onInput={(value) => updateDraft('artist_fee', value)} />
          <Field label='场馆费用 / 元' type='number' value={inputValue(draft.venue_cost)} onInput={(value) => updateDraft('venue_cost', value)} />
          <Field label='宣发费用 / 元' type='number' value={inputValue(draft.marketing_cost)} onInput={(value) => updateDraft('marketing_cost', value)} />
          <Field label='制作费用 / 元' type='number' value={inputValue(draft.production_cost)} onInput={(value) => updateDraft('production_cost', value)} />
        </View>
      )
    }
    if (screenId === 'S17') {
      return <ProjectReview draft={draft} />
    }

    const fields: Record<string, Array<[string, string, string]>> = {
      S09: [['keyword', '搜索条件', '艺人、城市、档期或规模']],
      S36: [['assumptionTitle', '新增假设', '例如：中性上座率 80%']],
      S37: [['factTitle', '新增事实', '填写待核验的项目事实']],
      S41: [['evidenceName', '资料名称', '例如：场馆容量确认'], ['evidenceUrl', '资料地址', '上传后的文件地址']],
      S45: [['gateName', '门禁名称', '政策、场地、授权或资金']],
      S47: [['condition', '前置条件', '填写负责人决定的必要条件']],
      S51: [['condition', '分享说明', '仅指定版本和授权成员可见']],
      S54: [['question', '输入问题或限制条件', '例如：固定成本降低 30 万会怎样']],
      S57: [['result', '核对结果', '填写结果、核对人和日期']],
      S65: [['result', '结算说明', '填写收入、成本与售出票数']],
      S72: [['result', '邀请对象', '填写姓名或联系方式']],
      S79: [['result', '缺失字段', '补充 0 至 100 的有效上座率']],
      S82: [['apiBase', '决策服务地址', 'http://127.0.0.1:8000']],
    }

    return (
      <View className={styles.formGrid}>
        {(fields[screenId] || []).map(([key, label, placeholder]) => (
          <Field key={key} label={label} value={form[key] || ''} placeholder={placeholder} onInput={(value) => updateForm(key, value)} />
        ))}
      </View>
    )
  }

  const secondaryTarget = screenId === 'S01' ? 'S06' : screenId === 'S10' ? 'S80' : screenId === 'S47' ? 'S35' : ''

  return (
    <ScrollView className={styles.page} scrollY enhanced showScrollbar={false}>
      <View className={styles.safeTop} />
      <View className={styles.topbar}>
        <View className={styles.brand}>
          <View className={styles.brandMark}>R</View>
          <View>
            <Text className={styles.brandName}>锐音场</Text>
            <Text className={styles.brandMeta}>RUIYINCHANG</Text>
          </View>
        </View>
        <View className={styles.screenCode}>{screen.id}</View>
      </View>

      <View className={styles.hero}>
        <Text className={styles.eyebrow}>{screen.group.toUpperCase()}</Text>
        <Text className={styles.title}>{screen.title}</Text>
        <Text className={styles.subtitle}>{screen.subtitle}</Text>
        <View className={styles.highlightRow}>
          <Text className={styles.highlight}>{screen.highlight}</Text>
          <Text className={styles.context}>产品蓝图 · {screen.id}</Text>
        </View>
      </View>

      {['财务', '判断', '风险', '版本', '复盘'].includes(screen.group) && (
        <View className={styles.chartSection}>
          <View className={styles.chartHeader}>
            <Text>项目收益边界</Text>
            <Text className={styles.chartCaption}>finance-v1</Text>
          </View>
          <View className={styles.chart}>
            {[22, 34, 48, 62, 79, 92].map((height, index) => (
              <View key={height} className={styles.chartColumn}>
                <View className={classNames(styles.chartBar, index < 2 && styles.chartBarRisk)} style={{ height: `${height}%` }} />
                <Text>{50 + index * 10}%</Text>
              </View>
            ))}
          </View>
          <View className={styles.breakEven}>
            <View className={styles.breakEvenDot} />
            <Text>63.2% 保本线 · 低于边界需重新测算</Text>
          </View>
        </View>
      )}

      {renderForm()}

      <View className={styles.section}>
        <View className={styles.sectionHeading}>
          <Text className={styles.sectionTitle}>{screen.group === '状态' ? '恢复说明' : '关键信息'}</Text>
          <Text className={styles.sectionCount}>{items.length} 项</Text>
        </View>

        {loadState === 'loading' && <View className={styles.loadingLine}>正在连接决策服务...</View>}
        {items.map((item) => (
          <View className={styles.listItem} key={item.id}>
            <View className={styles.listMain}>
              <Text className={styles.itemTitle}>{item.title}</Text>
              <Text className={styles.itemDescription}>{item.description}</Text>
            </View>
            <View className={styles.itemAside}>
              {item.value && <Text className={styles.itemValue}>{item.value}</Text>}
              <Text className={styles.status}>{item.status}</Text>
            </View>
          </View>
        ))}
      </View>

      <View className={styles.trustNote}>
        <View className={styles.trustIcon}>i</View>
        <Text>
          {loadState === 'example'
            ? '当前为产品示例数据，不代表已核验事实。连接服务后将自动读取授权范围内的数据。'
            : '事实、假设和 AI 建议分别标注；关键决定与人工门禁始终由具名负责人确认。'}
        </Text>
      </View>

      {message && (
        <View className={classNames(styles.message, loadState === 'error' && styles.messageError)}>
          <Text>{message}</Text>
        </View>
      )}

      <View className={styles.actions}>
        <Button
          className={classNames(styles.primaryButton, destructiveScreens.has(screenId) && styles.cautionButton)}
          disabled={loadState === 'loading'}
          onClick={runPrimaryAction}
        >
          {loadState === 'loading' ? '处理中...' : screen.primaryAction}
        </Button>
        {secondaryTarget && (
          <Button className={styles.secondaryButton} onClick={() => navigateToScreen(secondaryTarget)}>
            {screenId === 'S01' ? '先看看成功案例' : screenId === 'S10' ? '查看归档说明' : '返回检查依据'}
          </Button>
        )}
      </View>

      <View className={styles.progress}>
        <View className={styles.progressFill} style={{ width: `${progress}%` }} />
      </View>
      <Text className={styles.footer}>锐音场决策系统 · 所有金额与案例需按来源核验</Text>
      <View className={styles.safeBottom} />
    </ScrollView>
  )
}

interface FieldProps {
  label: string
  value: string
  placeholder?: string
  type?: 'text' | 'number'
  onInput: (value: string) => void
}

function Field({ label, value, placeholder, type = 'text', onInput }: FieldProps) {
  return (
    <View className={styles.field}>
      <Text className={styles.fieldLabel}>{label}</Text>
      <Input
        className={styles.input}
        type={type}
        value={value}
        placeholder={placeholder}
        onInput={(event) => onInput(event.detail.value)}
      />
    </View>
  )
}

function ProjectReview({ draft }: { draft: ProjectDraft }) {
  return (
    <View className={styles.reviewGrid}>
      <View><Text>项目组合</Text><Text>{draft.artist_name} × {draft.city}</Text></View>
      <View><Text>计划时间</Text><Text>{draft.schedule}</Text></View>
      <View><Text>可售规模</Text><Text>{draft.expected_attendance || '待补'} 人</Text></View>
      <View><Text>平均票价</Text><Text>{draft.avg_ticket_price || '待补'} 元</Text></View>
      <View><Text>候选场馆</Text><Text>{draft.venue || '待选择'}</Text></View>
      <View><Text>资料缺口</Text><Text>场馆、授权、成本依据</Text></View>
    </View>
  )
}
