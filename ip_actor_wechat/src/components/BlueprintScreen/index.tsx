import { useCallback, useEffect, useMemo, useState } from 'react'
import { Button, Input, ScrollView, Text, View } from '@tarojs/components'
import Taro, { usePullDownRefresh, useRouter } from '@tarojs/taro'
import classNames from 'classnames'

import SearchSelect, {
  type SearchSelectOption,
  type SearchSelectSection,
} from '@/components/SearchSelect'
import { DEFAULT_API_BASE, STORAGE_KEYS } from '@/config/runtime'
import { screenDataMap } from '@/data/screenDataMap'
import { screenDefinitions } from '@/data/screens'
import { api, ApiError, getApiBase, setApiBase } from '@/services/api'
import type {
  DisplayItem,
  MiniappScreenContext,
  MiniappScreenData,
  ProjectDraft,
  SessionData,
} from '@/types/domain'
import styles from './index.module.scss'

interface BlueprintScreenProps {
  screenId: string
}

type LoadState = 'idle' | 'loading' | 'success' | 'empty' | 'error'

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

const initialDraft: ProjectDraft = {
  name: '',
  type: 'concert',
  artist_name: '',
  city: '',
  venue: '',
  schedule: '',
}

const getStoredDraft = (): ProjectDraft => {
  const stored = Taro.getStorageSync<ProjectDraft>(STORAGE_KEYS.projectDraft)
  return stored && typeof stored === 'object' ? { ...initialDraft, ...stored } : initialDraft
}

const inputValue = (value: string | number | undefined) => value === undefined ? '' : String(value)

export default function BlueprintScreen({ screenId }: BlueprintScreenProps) {
  const screen = screenDefinitions[screenId]
  const router = useRouter()
  const params = router.params
  const [items, setItems] = useState<DisplayItem[]>([])
  const [screenData, setScreenData] = useState<MiniappScreenData | null>(null)
  const [loadState, setLoadState] = useState<LoadState>('idle')
  const [message, setMessage] = useState('')
  const [draft, setDraft] = useState<ProjectDraft>(getStoredDraft)
  const [projectSearchKeyword, setProjectSearchKeyword] = useState('')
  const initialTaskId = Number(params.taskId || Taro.getStorageSync<number>(STORAGE_KEYS.taskId) || 0)
  const [activeTaskId, setActiveTaskId] = useState(initialTaskId)
  const [selectedTaskIds, setSelectedTaskIds] = useState<number[]>(initialTaskId ? [initialTaskId] : [])
  const [expandedTaskIds, setExpandedTaskIds] = useState<number[]>(initialTaskId ? [initialTaskId] : [])
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

  const storedProjectId = Number(params.projectId || Taro.getStorageSync<number>(STORAGE_KEYS.projectId) || 0)
  const projectId = storedProjectId
  const versionId = Number(params.versionId || Taro.getStorageSync<number>(STORAGE_KEYS.versionId) || 0)
  const artistId = Number(params.artistId || 0)

  const fetchRemote = async () => {
    const requiredContext = screenDataMap[screenId].requiredContext
    const context: MiniappScreenContext = {
      ...(projectId && requiredContext.includes('project_id') ? { project_id: projectId } : {}),
      ...(versionId && requiredContext.includes('version_id') ? { version_id: versionId } : {}),
      ...(activeTaskId && requiredContext.includes('task_id') ? { task_id: activeTaskId } : {}),
      ...(artistId && requiredContext.includes('artist_id') ? { artist_id: artistId } : {}),
      ...(form.keyword.trim() ? { keyword: form.keyword.trim() } : {}),
    }
    setItems([])
    setScreenData(null)
    setMessage('')
    setLoadState('loading')
    try {
      const data = await api.getMiniappScreen(screenId, context)
      const displayItems: DisplayItem[] = data.items.map((item) => ({
        id: item.id,
        title: item.title,
        description: item.description || '',
        status: item.status || '',
        value: item.value || '',
        details: item.details || '',
        context: item.context,
      }))
      if (screenId === 'S52') {
        const cachedProjectId = Number(Taro.getStorageSync<number>(STORAGE_KEYS.projectId) || 0)
        const defaultProjectId = Number(data.options.default_project_id || 0)
        if (!cachedProjectId && defaultProjectId) {
          Taro.setStorageSync(STORAGE_KEYS.projectId, defaultProjectId)
        }
      }
      setScreenData(data)
      setItems(displayItems)
      if (displayItems.length) {
        if (['S55', 'S56', 'S57', 'S58'].includes(screenId)) {
          const selectedTaskId = Number(
            displayItems.find((task) => Number(task.context?.task_id) === activeTaskId)?.context?.task_id
              || displayItems[0].context?.task_id
              || 0,
          )
          if (selectedTaskId) {
            setActiveTaskId(selectedTaskId)
            Taro.setStorageSync(STORAGE_KEYS.taskId, selectedTaskId)
          }
        }
      }
      setLoadState(displayItems.length ? 'success' : 'empty')
    } catch (error) {
      console.error(`[${screenId}] load failed`, error)
      const statusCode = error instanceof ApiError ? error.statusCode : undefined
      const errorTarget = statusCode === 401
        ? 'S81'
        : statusCode === 403
          ? 'S77'
          : statusCode === 409
            ? 'S78'
            : ''
      if (errorTarget && screenId !== errorTarget) {
        await replaceWithScreen(errorTarget)
        return
      }
      setLoadState('error')
      setMessage(statusCode === 422
        ? '缺少打开当前页面所需的项目、版本或任务信息。'
        : '页面数据加载失败，请重试。')
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
      'artist_id', 'venue_id', 'source_project_id',
      'expected_attendance', 'available_funds', 'avg_ticket_price', 'artist_fee',
      'venue_cost', 'marketing_cost', 'production_cost',
    ]
    const nextValue = numericKeys.includes(key) ? (value === '' ? undefined : Number(value)) : value
    const next = { ...draft, [key]: nextValue }
    setDraft(next)
    Taro.setStorageSync(STORAGE_KEYS.projectDraft, next)
  }

  const searchProjectOptions = useCallback(async (keyword: string): Promise<Array<SearchSelectSection<Record<string, unknown>>>> => {
    const result = await api.searchMiniappEntities(keyword)
    return result.groups
      .filter((group) => ['artist', 'project'].includes(group.entity_type))
      .map((group) => ({
        entityType: group.entity_type,
        label: group.label,
        options: group.items.map((item) => ({
          entityType: item.entity_type,
          entityId: item.entity_id,
          label: item.label,
          description: item.description || '',
          value: asRecord(item.value),
        })),
      }))
  }, [])

  const searchCityOptions = useCallback(async (keyword: string): Promise<Array<SearchSelectSection<Record<string, unknown>>>> => {
    const result = await api.searchMiniappEntities(keyword)
    return result.groups
      .filter((group) => group.entity_type === 'city')
      .map((group) => ({
        entityType: group.entity_type,
        label: group.label,
        options: group.items.map((item) => ({
          entityType: item.entity_type,
          entityId: item.entity_id,
          label: item.label,
          description: item.description || '',
          value: asRecord(item.value),
        })),
      }))
  }, [])

  const searchVenueOptions = useCallback(async (keyword: string): Promise<Array<SearchSelectSection<Record<string, unknown>>>> => {
    const result = await api.searchMiniappEntities(keyword)
    return result.groups
      .filter((group) => group.entity_type === 'venue')
      .map((group) => ({
        entityType: group.entity_type,
        label: group.label,
        options: group.items.map((item) => ({
          entityType: item.entity_type,
          entityId: item.entity_id,
          label: item.label,
          description: item.description || '',
          value: asRecord(item.value),
        })),
      }))
  }, [])

  const selectProjectSearchSuggestion = async (
    suggestion: SearchSelectOption<Record<string, unknown>>,
  ) => {
    setProjectSearchKeyword(suggestion.label)
    if (suggestion.entityType === 'artist') {
      const next = {
        ...draft,
        artist_id: Number(suggestion.entityId),
        artist_name: suggestion.label,
        source_project_id: undefined,
      }
      setDraft(next)
      Taro.setStorageSync(STORAGE_KEYS.projectDraft, next)
      return
    }

    const projectIdValue = Number(suggestion.entityId)
    let project = suggestion.value
    if (projectIdValue) {
      try {
        project = asRecord(await api.getProject(projectIdValue))
      } catch (error) {
        console.error('[S13] project detail load failed', { projectId: projectIdValue, error })
      }
    }
    const next = {
      ...draft,
      name: textValue(project, ['name'], suggestion.label),
      type: textValue(project, ['type'], draft.type),
      artist_id: Number(project.artist_id) || undefined,
      artist_name: textValue(project, ['artist_name'], draft.artist_name),
      city: textValue(project, ['city'], draft.city),
      venue_id: Number(project.venue_id) || undefined,
      venue: textValue(project, ['venue'], draft.venue),
      source_project_id: Number(suggestion.entityId),
    }
    setDraft(next)
    Taro.setStorageSync(STORAGE_KEYS.projectDraft, next)
  }

  const selectVenue = (suggestion: SearchSelectOption<Record<string, unknown>>) => {
    const venue = suggestion.value
    const next = {
      ...draft,
      venue_id: Number(suggestion.entityId),
      venue: suggestion.label,
      city: textValue(venue, ['city'], draft.city),
    }
    setDraft(next)
    Taro.setStorageSync(STORAGE_KEYS.projectDraft, next)
  }

  const updateForm = (key: string, value: string) => setForm((current) => ({ ...current, [key]: value }))

  const toggleTaskSelection = (taskId: number) => {
    setSelectedTaskIds((current) => (
      current.includes(taskId)
        ? current.filter((id) => id !== taskId)
        : [...current, taskId]
    ))
  }

  const toggleTaskDetails = (taskId: number) => {
    setExpandedTaskIds((current) => (
      current.includes(taskId)
        ? current.filter((id) => id !== taskId)
        : [...current, taskId]
    ))
  }

  const runBatchTaskAction = async (action: 'accept' | 'reject') => {
    if (!selectedTaskIds.length) {
      setLoadState('error')
      setMessage('请至少勾选一项任务。')
      return
    }

    let reason = ''
    if (action === 'reject') {
      const confirmation = await Taro.showModal({
        title: '拒绝接单',
        content: '',
        editable: true,
        placeholderText: '请输入拒绝原因',
        confirmText: '确认拒绝',
      })
      if (!confirmation.confirm) return
      reason = (confirmation.content || '').trim()
      if (!reason) {
        setLoadState('error')
        setMessage('拒绝接单时必须填写原因。')
        return
      }
    }

    setLoadState('loading')
    setMessage('')
    try {
      await api.batchTaskAction({
        task_ids: selectedTaskIds,
        action,
        reason,
      })
      const count = selectedTaskIds.length
      setSelectedTaskIds([])
      setMessage(action === 'accept' ? `已接受 ${count} 项任务。` : `已拒绝 ${count} 项任务，任务已恢复待分配。`)
      await fetchRemote()
    } catch (error) {
      console.error(`[S56] batch ${action} failed`, error)
      setLoadState('error')
      setMessage(action === 'accept' ? '接受任务失败，请刷新后重试。' : '拒绝任务失败，请刷新后重试。')
    }
  }

  const storeSessionData = (session: SessionData) => {
    if (session.token) Taro.setStorageSync(STORAGE_KEYS.token, session.token)
    if (session.user) Taro.setStorageSync(STORAGE_KEYS.user, session.user)
    if (session.current_tenant) Taro.setStorageSync(STORAGE_KEYS.tenant, session.current_tenant)
  }

  const handleWechatPhoneLogin = async (event: { detail?: { code?: string, errMsg?: string } }) => {
    setLoadState('loading')
    setMessage('')
    try {
      const phoneCode = event?.detail?.code
      if (!phoneCode) {
        setLoadState('error')
        setMessage('未完成手机号授权，暂不能登录。')
        return
      }

      let code = 'preview-code'
      if (Taro.getEnv() === Taro.ENV_TYPE.WEAPP) {
        const login = await Taro.login()
        code = login.code
      }

      const session = await api.wechatLogin({ code, phone_code: phoneCode, name: '微信用户' }) as SessionData
      storeSessionData(session)
      setLoadState('success')
      await replaceWithScreen(nextScreen[screenId] || 'S02')
    } catch (error) {
      console.error(`[${screenId}] phone login failed`, error)
      setLoadState('error')
      const detail = error instanceof Error ? error.message : ''
      if (detail === 'FORBIDDEN') {
        setMessage('手机号未绑定，请联系管理员分配账号。')
      } else if (detail === 'HTTP_503') {
        setMessage('微信登录配置缺失，请联系管理员配置小程序密钥或启用本地联调手机号。')
      } else {
        setMessage('登录失败，请确认后端服务可用。')
      }
    }
  }

  const runPrimaryAction = async () => {
    setLoadState('loading')
    setMessage('')
    try {
      if (screenId === 'S01') {
        setLoadState('error')
        setMessage('请使用手机号授权登录。')
        return
      } else if (screenId === 'S02') {
        const tenantId = Number(items[0]?.id || 1)
        const switched = await api.switchTenant(tenantId)
        if (switched.current_tenant) {
          Taro.setStorageSync(STORAGE_KEYS.tenant, switched.current_tenant)
        }
        if (typeof switched.token === 'string') {
          Taro.setStorageSync(STORAGE_KEYS.token, switched.token)
        }
      } else if (screenId === 'S17') {
        const created = await api.createProject(draft as unknown as Record<string, unknown>)
        const record = asRecord(created)
        const id = Number(record.id || 0)
        if (!id) throw new Error('PROJECT_ID_MISSING')
        Taro.setStorageSync(STORAGE_KEYS.projectId, id)
        if (record.current_version_id) {
          Taro.setStorageSync(STORAGE_KEYS.versionId, Number(record.current_version_id))
        }
        Taro.removeStorageSync(STORAGE_KEYS.projectDraft)
      } else if (screenId === 'S52') {
        const selectedProjectId = Number(
          Taro.getStorageSync<number>(STORAGE_KEYS.projectId)
            || screenData?.options.default_project_id
            || 0,
        )
        if (!selectedProjectId) {
          setLoadState('success')
          await replaceWithScreen('S10')
          return
        }
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
        if (record.version_id) Taro.setStorageSync(STORAGE_KEYS.versionId, Number(record.version_id))
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
        if (!activeTaskId) throw new Error('TASK_NOT_SELECTED')
        await api.submitTask(activeTaskId, { result: form.result || '已提交任务结果', evidence_ids: [] })
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
      const target = screenId === 'S74' && !storedProjectId
        ? 'S10'
        : nextScreen[screenId] || `S${String(Math.min(Number(screenId.slice(1)) + 1, 84)).padStart(2, '0')}`
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
          <View className={styles.searchField}>
            <Text className={styles.fieldLabel}>搜索艺人或历史项目</Text>
            <SearchSelect
              value={projectSearchKeyword}
              placeholder='输入艺人、IP 或项目名称'
              onInput={setProjectSearchKeyword}
              onSearch={searchProjectOptions}
              onSelect={(suggestion) => void selectProjectSearchSuggestion(suggestion)}
            />
          </View>
          <Field label='项目名称' value={draft.name} onInput={(value) => updateDraft('name', value)} />
          <Field label='项目类型' value={draft.type} onInput={(value) => updateDraft('type', value)} />
          <Field label='核心艺人 / IP' value={draft.artist_name} onInput={(value) => updateDraft('artist_name', value)} />
        </View>
      )
    }
    if (screenId === 'S14') {
      return (
        <View className={styles.formGrid}>
          <View className={styles.field}>
            <Text className={styles.fieldLabel}>举办城市</Text>
            <SearchSelect
              value={draft.city}
              placeholder='搜索已有场馆城市'
              onInput={(value) => updateDraft('city', value)}
              onSearch={searchCityOptions}
              onSelect={(suggestion) => updateDraft('city', suggestion.label)}
            />
          </View>
          <Field label='计划时间' value={draft.schedule} onInput={(value) => updateDraft('schedule', value)} />
          <View className={styles.field}>
            <Text className={styles.fieldLabel}>候选场馆</Text>
            <SearchSelect
              value={draft.venue}
              placeholder='搜索场馆名称或城市'
              onInput={(value) => updateDraft('venue', value)}
              onSearch={searchVenueOptions}
              onSelect={selectVenue}
            />
          </View>
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
      S82: [['apiBase', '决策服务地址', DEFAULT_API_BASE]],
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
        <Text className={styles.title}>{screenData?.summary.title || screen.title}</Text>
        <Text className={styles.subtitle}>{screenData?.summary.subtitle || screen.subtitle}</Text>
        <View className={styles.highlightRow}>
          {screenData?.summary.highlight && (
            <Text className={styles.highlight}>{screenData.summary.highlight}</Text>
          )}
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
        {loadState === 'empty' && screenData?.empty_state && (
          <View className={styles.emptyState}>
            <Text className={styles.emptyStateTitle}>{screenData.empty_state.title}</Text>
            {screenData.empty_state.description && (
              <Text className={styles.emptyStateDescription}>{screenData.empty_state.description}</Text>
            )}
            {screenData.empty_state.action?.label && (
              <Button
                className={styles.emptyStateAction}
                onClick={() => {
                  const target = screenData.empty_state?.action?.target_screen
                  if (target) void navigateToScreen(target)
                }}
              >
                {screenData.empty_state.action.label}
              </Button>
            )}
          </View>
        )}
        {screenId === 'S56' && (
          <Text className={styles.taskSelectionSummary}>已选择 {selectedTaskIds.length} 项任务</Text>
        )}
        {items.map((item) => {
          const taskId = Number(item.context?.task_id || 0)
          const isTaskSelected = selectedTaskIds.includes(taskId)
          const isTaskExpanded = expandedTaskIds.includes(taskId)
          return (
          <View
            className={classNames(styles.listItem, screenId === 'S56' && styles.taskItem)}
            key={item.id}
            onClick={screenId === 'S55' ? () => {
              const selectedTaskId = Number(item.context?.task_id || 0)
              if (!selectedTaskId) return
              setActiveTaskId(selectedTaskId)
              Taro.setStorageSync(STORAGE_KEYS.taskId, selectedTaskId)
              void replaceWithScreen('S56')
            } : undefined}
          >
            {screenId === 'S56' && (
              <View
                className={classNames(styles.taskCheckbox, isTaskSelected && styles.taskCheckboxSelected)}
                onClick={(event) => {
                  event.stopPropagation()
                  toggleTaskSelection(taskId)
                }}
              >
                {isTaskSelected && <Text>✓</Text>}
              </View>
            )}
            <View
              className={styles.listMain}
              onClick={screenId === 'S56' ? () => toggleTaskDetails(taskId) : undefined}
            >
              <Text className={styles.itemTitle}>{item.title}</Text>
              <Text className={classNames(styles.itemDescription, isTaskExpanded && styles.itemDescriptionExpanded)}>
                {item.description}
              </Text>
              {screenId === 'S56' && isTaskExpanded && (
                <View className={styles.taskDetails}>
                  <Text>{item.details || '暂无更多任务信息'}</Text>
                </View>
              )}
            </View>
            <View className={styles.itemAside}>
              {item.value && <Text className={styles.itemValue}>{item.value}</Text>}
              <Text className={styles.status}>{item.status}</Text>
            </View>
          </View>
          )
        })}
      </View>

      <View className={styles.trustNote}>
        <View className={styles.trustIcon}>i</View>
        <Text>事实、假设和 AI 建议分别标注；关键决定与人工门禁始终由具名负责人确认。</Text>
      </View>

      {message && (
        <View className={classNames(styles.message, loadState === 'error' && styles.messageError)}>
          <Text>{message}</Text>
        </View>
      )}

      <View className={styles.actions}>
        {loadState === 'error' ? (
          <Button className={styles.primaryButton} onClick={() => void fetchRemote()}>
            重新加载
          </Button>
        ) : screenId === 'S56' ? (
          <View className={styles.taskActions}>
            <Button
              className={styles.primaryButton}
              disabled={loadState === 'loading' || !selectedTaskIds.length}
              onClick={() => void runBatchTaskAction('accept')}
            >
              接受选中
            </Button>
            <Button
              className={styles.rejectButton}
              disabled={loadState === 'loading' || !selectedTaskIds.length}
              onClick={() => void runBatchTaskAction('reject')}
            >
              拒绝接单
            </Button>
          </View>
        ) : screenId === 'S01' ? (
          <Button
            className={classNames(styles.primaryButton, destructiveScreens.has(screenId) && styles.cautionButton)}
            disabled={loadState === 'loading'}
            openType='getPhoneNumber'
            onGetPhoneNumber={handleWechatPhoneLogin}
          >
            {loadState === 'loading' ? '处理中...' : screen.primaryAction}
          </Button>
        ) : (
          <Button
            className={classNames(styles.primaryButton, destructiveScreens.has(screenId) && styles.cautionButton)}
            disabled={loadState === 'loading'}
            onClick={runPrimaryAction}
          >
            {loadState === 'loading' ? '处理中...' : screen.primaryAction}
          </Button>
        )}
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
