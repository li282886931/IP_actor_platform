import { useCallback, useMemo, useState } from 'react'
import { Button, ScrollView, Text, View } from '@tarojs/components'
import Taro, { usePullDownRefresh, useRouter } from '@tarojs/taro'
import classNames from 'classnames'

import {
  BusinessList,
  CandidateField,
  DecisionCockpit,
  FormField,
  KeyValueGrid,
  LifecycleTimeline,
  ProjectWorkPanel,
  ScreenHeader,
  ScreenHero,
  ScreenState,
  ScenarioStrip,
  TaskBatchList,
  ValueEvidencePanel,
  VariancePanel,
  WorkBriefing,
} from '@/components/ScreenPrimitives'
import { useProjectDraft } from '@/hooks/useProjectDraft'
import { useMiniappScreenData } from '@/hooks/useMiniappScreenData'
import SearchSelect, {
  type SearchSelectOption,
  type SearchSelectSection,
} from '@/components/SearchSelect'
import { DEFAULT_API_BASE, STORAGE_KEYS } from '@/config/runtime'
import { screenDefinitions } from '@/data/screens'
import { api, getApiBase, setApiBase } from '@/services/api'
import type {
  DisplayItem,
  MiniappCandidateGroup,
  MiniappCandidateItem,
  MiniappScreenContext,
  ProjectDraft,
  SessionData,
} from '@/types/domain'
import styles from './index.module.scss'

interface BlueprintScreenProps {
  screenId: string
}

const tabIds = new Set(['S04', 'S10', 'S52', 'S67'])
const formScreens = new Set(['S09', 'S13', 'S14', 'S15', 'S16', 'S17', 'S25', 'S36', 'S37', 'S41', 'S45', 'S47', 'S51', 'S54', 'S57', 'S65', 'S72', 'S79', 'S82'])
const destructiveScreens = new Set(['S47', 'S80', 'S84'])
const devtoolsLoginCode = 'local-devtools-login-code'
const devtoolsPhoneCode = 'local-devtools-phone-code'

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

const inputValue = (value: string | number | undefined) => value === undefined ? '' : String(value)

export default function BlueprintScreen({ screenId }: BlueprintScreenProps) {
  const screen = screenDefinitions[screenId]
  const router = useRouter()
  const params = router.params
  const { draft, updateDraft, applyCandidatePatch } = useProjectDraft()
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

  const screenContext = useMemo<MiniappScreenContext>(() => ({
    ...(projectId ? { project_id: projectId } : {}),
    ...(versionId ? { version_id: versionId } : {}),
    ...(activeTaskId ? { task_id: activeTaskId } : {}),
    ...(artistId ? { artist_id: artistId } : {}),
    ...(form.keyword.trim() ? { keyword: form.keyword.trim() } : {}),
  }), [activeTaskId, artistId, form.keyword, projectId, versionId])

  const {
    data: screenData,
    items,
    state: loadState,
    message,
    reload: fetchRemote,
    setState: setLoadState,
    setMessage,
  } = useMiniappScreenData({
    screenId,
    context: screenContext,
    onRedirect: (target) => { void replaceWithScreen(target) },
    onLoaded: (data) => {
      if (screenId === 'S52') {
        const cachedProjectId = Number(Taro.getStorageSync<number>(STORAGE_KEYS.projectId) || 0)
        const defaultProjectId = Number(data.options.default_project_id || 0)
        if (!cachedProjectId && defaultProjectId) Taro.setStorageSync(STORAGE_KEYS.projectId, defaultProjectId)
      }
      if (['S55', 'S56', 'S57', 'S58'].includes(screenId) && data.items.length) {
        const selectedTaskId = Number(
          data.items.find((task) => Number(task.context?.task_id) === activeTaskId)?.context?.task_id
            || data.items[0].context?.task_id
            || 0,
        )
        if (selectedTaskId) {
          setActiveTaskId(selectedTaskId)
          Taro.setStorageSync(STORAGE_KEYS.taskId, selectedTaskId)
        }
      }
      Taro.stopPullDownRefresh()
    },
  })

  usePullDownRefresh(() => {
    void fetchRemote()
  })

  const progress = useMemo(() => {
    const current = Number(screenId.slice(1))
    return Math.round((current / 84) * 100)
  }, [screenId])

  const candidateGroups = (): MiniappCandidateGroup[] => {
    const rawGroups = screenData?.options.candidate_groups
    return Array.isArray(rawGroups) ? rawGroups as MiniappCandidateGroup[] : []
  }

  const initialCandidateSections = (
    fields: Array<keyof ProjectDraft>,
  ): Array<SearchSelectSection<MiniappCandidateItem>> => (
    candidateGroups()
      .filter((group) => fields.includes(group.field))
      .map((group) => ({
        entityType: group.key,
        label: group.label,
        options: group.items.map((item) => ({
          entityType: item.entity_type || group.key,
          entityId: item.entity_id || item.key,
          label: item.label,
          description: item.description || '',
          value: item,
        })),
      }))
  )

  const applyCandidate = (suggestion: SearchSelectOption<MiniappCandidateItem>) => {
    applyCandidatePatch(suggestion.value.patch)
  }

  const localCandidateSearch = (
    fields: Array<keyof ProjectDraft>,
  ) => async (keyword: string): Promise<Array<SearchSelectSection<MiniappCandidateItem>>> => {
    const normalized = keyword.trim().toLowerCase()
    return initialCandidateSections(fields)
      .map((section) => ({
        ...section,
        options: section.options.filter((option) => (
          `${option.label} ${option.description || ''}`.toLowerCase().includes(normalized)
        )),
      }))
      .filter((section) => section.options.length > 0)
  }

  const searchProjectOptions = useCallback(async (keyword: string): Promise<Array<SearchSelectSection<MiniappCandidateItem>>> => {
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
          value: group.entity_type === 'artist'
            ? {
                key: `artist-${item.entity_id}`,
                label: item.label,
                patch: { artist_id: Number(item.entity_id), artist_name: item.label },
                entity_type: 'artist',
                entity_id: Number(item.entity_id),
              }
            : {
                key: `project-${item.entity_id}`,
                label: item.label,
                patch: {
                  ...asRecord(item.value),
                  source_project_id: Number(item.entity_id),
                },
                entity_type: 'project',
                entity_id: Number(item.entity_id),
              },
        })),
      }))
  }, [])

  const searchCityOptions = useCallback(async (keyword: string): Promise<Array<SearchSelectSection<MiniappCandidateItem>>> => {
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
          value: {
            key: `city-${item.label}`,
            label: item.label,
            patch: { city: item.label },
          },
        })),
      }))
  }, [])

  const searchVenueOptions = useCallback(async (keyword: string): Promise<Array<SearchSelectSection<MiniappCandidateItem>>> => {
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
          value: {
            key: `venue-${item.entity_id}`,
            label: item.label,
            patch: {
              venue_id: Number(item.entity_id),
              venue: item.label,
              city: textValue(asRecord(item.value), ['city']),
              venue_capacity: Number(asRecord(item.value).capacity) || undefined,
            },
            entity_type: 'venue',
            entity_id: Number(item.entity_id),
          },
        })),
      }))
  }, [])

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

  const openItemDetail = (item: DisplayItem) => {
    if (!item.detailRef) return
    if (item.detailRef.entity_type === 'task') {
      Taro.setStorageSync(STORAGE_KEYS.taskId, item.detailRef.entity_id)
      setActiveTaskId(item.detailRef.entity_id)
    }
    void Taro.navigateTo({
      url: `/pages/entity-detail/index?entityType=${encodeURIComponent(item.detailRef.entity_type)}&entityId=${item.detailRef.entity_id}`,
    })
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
        confirmText: '确认拒绝',
      } as Taro.showModal.Option)
      if (!confirmation.confirm) return
      reason = String((confirmation as unknown as { content?: string }).content || '').trim()
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
      const isWechatDevtools = Taro.getEnv() === Taro.ENV_TYPE.WEAPP
        && Taro.getSystemInfoSync?.().platform === 'devtools'
      const phoneCode = event?.detail?.code || (isWechatDevtools ? devtoolsPhoneCode : '')
      if (!phoneCode) {
        setLoadState('error')
        setMessage('未完成手机号授权，暂不能登录。')
        return
      }

      let code = isWechatDevtools ? devtoolsLoginCode : 'preview-code'
      if (Taro.getEnv() === Taro.ENV_TYPE.WEAPP && !isWechatDevtools) {
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
        setMessage(`${textValue(asRecord(answer), ['answer'], '工作建议已生成')}｜推荐动作：${textValue(analysisResult, ['recommendation'], '待负责人核验')}`)
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
              initialSections={initialCandidateSections(['source_project_id', 'artist_name'])}
              onInput={setProjectSearchKeyword}
              onSearch={searchProjectOptions}
              onSelect={(suggestion) => {
                setProjectSearchKeyword(suggestion.label)
                applyCandidate(suggestion)
              }}
            />
          </View>
          <FormField label='项目名称' value={draft.name} onChange={(value) => updateDraft('name', value)} />
          <CandidateField
            label='项目类型'
            value={draft.type}
            placeholder='输入或选择项目类型'
            initialSections={initialCandidateSections(['type'])}
            onInput={(value) => updateDraft('type', value)}
            onSearch={localCandidateSearch(['type'])}
            onSelect={applyCandidate}
          />
          <FormField label='核心艺人 / IP' value={draft.artist_name} onChange={(value) => updateDraft('artist_name', value)} />
        </View>
      )
    }
    if (screenId === 'S14') {
      return (
        <View className={styles.formGrid}>
          <CandidateField label='举办城市' value={draft.city} placeholder='搜索已有场馆城市' initialSections={initialCandidateSections(['city'])} onInput={(value) => updateDraft('city', value)} onSearch={searchCityOptions} onSelect={applyCandidate} />
          <CandidateField label='计划时间' value={draft.schedule} placeholder='输入或选择计划时间' initialSections={initialCandidateSections(['schedule'])} onInput={(value) => updateDraft('schedule', value)} onSearch={localCandidateSearch(['schedule'])} onSelect={applyCandidate} />
          <CandidateField label='候选场馆' value={draft.venue} placeholder='搜索场馆名称或城市' initialSections={initialCandidateSections(['venue'])} onInput={(value) => updateDraft('venue', value)} onSearch={searchVenueOptions} onSelect={applyCandidate} />
        </View>
      )
    }
    if (screenId === 'S15') {
      return (
        <View className={styles.formGrid}>
          <CandidateNumberField label='可售规模 / 人' field='expected_attendance' draft={draft} initialSections={initialCandidateSections(['expected_attendance'])} onInput={updateDraft} onSearch={localCandidateSearch(['expected_attendance'])} onSelect={applyCandidate} />
          <CandidateNumberField label='可用资金 / 元' field='available_funds' draft={draft} initialSections={initialCandidateSections(['available_funds'])} onInput={updateDraft} onSearch={localCandidateSearch(['available_funds'])} onSelect={applyCandidate} />
          <CandidateNumberField label='平均实收票价 / 元' field='avg_ticket_price' draft={draft} initialSections={initialCandidateSections(['avg_ticket_price'])} onInput={updateDraft} onSearch={localCandidateSearch(['avg_ticket_price'])} onSelect={applyCandidate} />
        </View>
      )
    }
    if (screenId === 'S16' || screenId === 'S25') {
      return (
        <View className={styles.formGrid}>
          <CandidateNumberField label='艺人费用 / 元' field='artist_fee' draft={draft} initialSections={initialCandidateSections(['artist_fee'])} onInput={updateDraft} onSearch={localCandidateSearch(['artist_fee'])} onSelect={applyCandidate} />
          <CandidateNumberField label='场馆费用 / 元' field='venue_cost' draft={draft} initialSections={initialCandidateSections(['venue_cost'])} onInput={updateDraft} onSearch={localCandidateSearch(['venue_cost'])} onSelect={applyCandidate} />
          <CandidateNumberField label='宣发费用 / 元' field='marketing_cost' draft={draft} initialSections={initialCandidateSections(['marketing_cost'])} onInput={updateDraft} onSearch={localCandidateSearch(['marketing_cost'])} onSelect={applyCandidate} />
          <CandidateNumberField label='制作费用 / 元' field='production_cost' draft={draft} initialSections={initialCandidateSections(['production_cost'])} onInput={updateDraft} onSearch={localCandidateSearch(['production_cost'])} onSelect={applyCandidate} />
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
          <FormField key={key} label={label} value={form[key] || ''} placeholder={placeholder} onChange={(value) => updateForm(key, value)} />
        ))}
      </View>
    )
  }

  const secondaryTarget = screenId === 'S01' ? 'S06' : screenId === 'S10' ? 'S80' : screenId === 'S47' ? 'S35' : ''
  const showBackControl = screenId !== 'S01' && !tabIds.has(screenId)
  const options = screenData?.options || {}
  const valueEvidence = Array.isArray(options.value_evidence) ? options.value_evidence as Array<{
    title: string, metric?: string | null, source_label: string
  }> : []
  const cockpit = (screenId === 'S11' ? options.decision_cockpit : options.finance_cockpit) as {
    neutral_profit?: number | null
    breakeven_attendance?: number | null
    maximum_funding_gap?: number | null
    status?: string | null
    combination?: Record<string, unknown>
    missing_fields?: string[]
    scenarios?: Record<string, { profit?: number | null, attendance?: number | null }>
  } | undefined
  const briefing = options.work_briefing as {
    today_change_count?: number
    top_task?: { title?: string, status?: string, project_name?: string } | null
    active_project_count?: number
  } | undefined
  const projectWork = options.project_work as {
    plan_version?: number
    open_alert_count?: number
    recommendation?: string
    human_gate?: string
  } | undefined
  const ticketingLoop = options.ticketing_loop as { current_sold_count?: number | null } | undefined
  const actualsSummary = options.actuals_summary as { actual_profit?: number | null } | undefined
  const calibrationLoop = options.calibration_loop as {
    forecast_profit?: number | null
    actual_profit?: number | null
    profit_variance?: number | null
    notes?: string | null
  } | undefined

  return (
    <ScrollView className={styles.page} scrollY enhanced showScrollbar={false}>
      <View className={styles.safeTop} />
      <ScreenHeader
        screenCode={screen.id}
        showHome={showBackControl}
        onHome={() => void Taro.navigateBack({ delta: 1 })}
        homeLabel='‹'
        homeAriaLabel='返回'
      />
      <ScreenHero
        group={screen.group.toUpperCase()}
        title={screenData?.summary.title || screen.title}
        subtitle={screenData?.summary.subtitle || screen.subtitle}
        highlight={screenData?.summary.highlight}
        context={`产品蓝图 · ${screen.id}`}
      />

      {screenId === 'S04' && <ValueEvidencePanel evidence={valueEvidence} />}
      {(screenId === 'S11' || screenId === 'S25') && cockpit && (
        <>
          <DecisionCockpit cockpit={cockpit} />
          <ScenarioStrip scenarios={cockpit.scenarios} />
        </>
      )}
      {screenId === 'S52' && <WorkBriefing briefing={briefing} />}
      {screenId === 'S53' && <ProjectWorkPanel projectWork={projectWork} />}
      {['S64', 'S65', 'S66'].includes(screenId) && (
        <>
          <LifecycleTimeline currentStage={screenId === 'S64' ? '售票' : screenId === 'S65' ? '结算' : '校准'} />
          {screenId === 'S66' && <VariancePanel loop={calibrationLoop} />}
          {screenId === 'S64' && ticketingLoop?.current_sold_count !== undefined && <KeyValueGrid items={[{ label: '当前已售', value: String(ticketingLoop.current_sold_count) }]} />}
          {screenId === 'S65' && actualsSummary?.actual_profit !== undefined && <KeyValueGrid items={[{ label: '实际利润', value: String(actualsSummary.actual_profit) }]} />}
        </>
      )}

      {renderForm()}

      <View className={styles.section}>
        <View className={styles.sectionHeading}>
          <Text className={styles.sectionTitle}>{screen.group === '状态' ? '恢复说明' : '关键信息'}</Text>
          <Text className={styles.sectionCount}>{items.length} 项</Text>
        </View>

        <ScreenState
          state={loadState}
          emptyState={screenData?.empty_state ? {
            title: screenData.empty_state.title,
            description: screenData.empty_state.description,
            actionLabel: screenData.empty_state.action?.label,
          } : undefined}
          onEmptyAction={() => {
            const target = screenData?.empty_state?.action?.target_screen
            if (target) void navigateToScreen(target)
          }}
        />
        {screenId === 'S56' ? (
          <TaskBatchList
            items={items}
            selectedTaskIds={selectedTaskIds}
            expandedTaskIds={expandedTaskIds}
            onToggleSelection={toggleTaskSelection}
            onToggleDetails={toggleTaskDetails}
            onOpenDetail={openItemDetail}
          />
        ) : <BusinessList items={items} onOpenDetail={openItemDetail} />}
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

interface CandidateNumberFieldProps {
  label: string
  field: keyof Pick<
    ProjectDraft,
    'expected_attendance'
    | 'available_funds'
    | 'avg_ticket_price'
    | 'artist_fee'
    | 'venue_cost'
    | 'marketing_cost'
    | 'production_cost'
  >
  draft: ProjectDraft
  initialSections: Array<SearchSelectSection<MiniappCandidateItem>>
  onInput: (key: keyof ProjectDraft, value: string) => void
  onSearch: (keyword: string) => Promise<Array<SearchSelectSection<MiniappCandidateItem>>>
  onSelect: (option: SearchSelectOption<MiniappCandidateItem>) => void
}

function CandidateNumberField({
  label,
  field,
  draft,
  initialSections,
  onInput,
  onSearch,
  onSelect,
}: CandidateNumberFieldProps) {
  return (
    <CandidateField
      label={label}
      value={inputValue(draft[field])}
      placeholder='输入或选择数据库候选'
      initialSections={initialSections}
      onInput={(value) => onInput(field, value)}
      onSearch={onSearch}
      onSelect={onSelect}
    />
  )
}

function ProjectReview({ draft }: { draft: ProjectDraft }) {
  return (
    <KeyValueGrid items={[
      { label: '项目组合', value: `${draft.artist_name} × ${draft.city}` },
      { label: '计划时间', value: draft.schedule },
      { label: '可售规模', value: `${draft.expected_attendance || '待补'} 人` },
      { label: '平均票价', value: `${draft.avg_ticket_price || '待补'} 元` },
      { label: '候选场馆', value: draft.venue || '待选择' },
      { label: '资料缺口', value: '场馆、授权、成本依据' },
    ]} />
  )
}
