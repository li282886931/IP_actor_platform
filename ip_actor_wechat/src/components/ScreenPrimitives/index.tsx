import type { CSSProperties } from 'react'
import { Button, Input, Text, View } from '@tarojs/components'
import classNames from 'classnames'

import SearchSelect, {
  type SearchSelectOption,
  type SearchSelectSection,
} from '@/components/SearchSelect'
import type { DisplayItem } from '@/types/domain'
import styles from './index.module.scss'

export interface KeyValueItem {
  label: string
  value: string
}

export function ScreenHeader({
  screenCode,
  showHome = false,
  onHome,
  onBack,
  title,
  homeLabel = '主页',
  homeAriaLabel,
}: {
  screenCode?: string
  showHome?: boolean
  onHome?: () => void
  onBack?: () => void
  title?: string
  homeLabel?: string
  homeAriaLabel?: string
}) {
  return (
    <View className={styles.header}>
      {onBack ? (
        <Button className={styles.backButton} onClick={onBack} aria-label='返回'>‹</Button>
      ) : showHome && (
        <Button className={styles.homeButton} onClick={onHome} aria-label={homeAriaLabel}>{homeLabel}</Button>
      )}
      {title ? (
        <Text className={styles.headerTitle}>{title}</Text>
      ) : (
        <View className={styles.brand}>
          <View className={styles.brandMark}>R</View>
          <View>
            <Text className={styles.brandName}>锐音场</Text>
            <Text className={styles.brandMeta}>RUIYINCHANG</Text>
          </View>
        </View>
      )}
      {screenCode ? <View className={styles.screenCode}>{screenCode}</View> : <View className={styles.headerSpacer} />}
    </View>
  )
}

export function ScreenHero({
  group,
  title,
  subtitle,
  highlight,
  context,
  status,
}: {
  group?: string
  title: string
  subtitle?: string | null
  highlight?: string | null
  context?: string
  status?: string | null
}) {
  return (
    <View className={styles.hero}>
      {group && <Text className={styles.eyebrow}>{group}</Text>}
      <Text className={styles.title}>{title}</Text>
      {subtitle && <Text className={styles.subtitle}>{subtitle}</Text>}
      {(highlight || context || status) && (
        <View className={styles.highlightRow}>
          <View>
            {highlight && <Text className={styles.highlight}>{highlight}</Text>}
            {status && <Text className={styles.status}>{status}</Text>}
          </View>
          {context && <Text className={styles.context}>{context}</Text>}
        </View>
      )}
    </View>
  )
}

export function ScreenState({
  state,
  message,
  emptyState,
  onRetry,
  onEmptyAction,
}: {
  state: 'idle' | 'loading' | 'empty' | 'error' | 'success'
  message?: string
  emptyState?: { title: string, description?: string | null, actionLabel?: string | null }
  onRetry?: () => void
  onEmptyAction?: () => void
}) {
  if (state === 'loading') return <View className={styles.loadingLine}>正在连接决策服务...</View>
  if (state === 'empty' && emptyState) {
    return (
      <View className={styles.emptyState}>
        <Text className={styles.emptyStateTitle}>{emptyState.title}</Text>
        {emptyState.description && <Text className={styles.emptyStateDescription}>{emptyState.description}</Text>}
        {emptyState.actionLabel && <Button className={styles.emptyStateAction} onClick={onEmptyAction}>{emptyState.actionLabel}</Button>}
      </View>
    )
  }
  if (state === 'error') {
    return (
      <View className={styles.errorState}>
        {message && <Text>{message}</Text>}
        {onRetry && <Button className={styles.emptyStateAction} onClick={onRetry}>重新加载</Button>}
      </View>
    )
  }
  return null
}

export function KeyValueGrid({ items }: { items: KeyValueItem[] }) {
  return (
    <View className={styles.keyValueGrid}>
      {items.map((item) => (
        <View className={styles.keyValueItem} key={item.label}>
          <Text className={styles.keyLabel}>{item.label}</Text>
          <Text className={styles.keyValue}>{item.value}</Text>
        </View>
      ))}
    </View>
  )
}

export function ValueEvidencePanel({
  evidence,
}: {
  evidence: Array<{ title: string, metric?: string | null, source_label: string }>
}) {
  if (!evidence.length) return null
  return (
    <View className={styles.insightPanel}>
      <Text className={styles.insightTitle}>价值证据</Text>
      {evidence.map((item) => (
        <View className={styles.insightRow} key={`${item.title}-${item.source_label}`}>
          <View className={styles.listMain}>
            <Text className={styles.itemTitle}>{item.title}</Text>
            <Text className={styles.sourceLabel}>{item.source_label}</Text>
          </View>
          {item.metric && <Text className={styles.itemValue}>{item.metric}</Text>}
        </View>
      ))}
    </View>
  )
}

export function ProjectWorkPanel({
  projectWork,
}: {
  projectWork?: {
    plan_version?: number
    open_alert_count?: number
    recommendation?: string
    human_gate?: string
  } | null
}) {
  if (!projectWork) return null
  return (
    <View className={styles.insightPanel}>
      <Text className={styles.insightTitle}>项目工作</Text>
      <View className={styles.insightRow}>
        <Text className={styles.itemTitle}>计划 V{projectWork.plan_version || 0}</Text>
        <Text className={styles.itemValue}>待处理预警 {projectWork.open_alert_count || 0} 项</Text>
      </View>
      {projectWork.recommendation && <Text className={styles.sourceLabel}>{projectWork.recommendation}</Text>}
      {projectWork.human_gate && <Text className={styles.sourceLabel}>{projectWork.human_gate}</Text>}
    </View>
  )
}

export function DecisionCockpit({
  cockpit,
}: {
  cockpit: {
    neutral_profit?: number | null
    breakeven_attendance?: number | null
    maximum_funding_gap?: number | null
    status?: string | null
    combination?: Record<string, unknown>
    missing_fields?: string[]
  }
}) {
  const missing = cockpit.missing_fields || []
  const value = (item: number | null | undefined) => item === null || item === undefined ? '待补齐' : String(item)
  return (
    <View className={styles.insightPanel}>
      <Text className={styles.insightTitle}>项目收益边界</Text>
      <KeyValueGrid items={[
        { label: '中性利润', value: missing.length ? '待补齐' : value(cockpit.neutral_profit) },
        { label: '保本人数', value: missing.length ? '待补齐' : value(cockpit.breakeven_attendance) },
        { label: '资金缺口', value: missing.length ? '待补齐' : value(cockpit.maximum_funding_gap) },
        { label: '测算状态', value: cockpit.status || '待补齐' },
      ]} />
      {cockpit.combination && <KeyValueGrid items={Object.entries(cockpit.combination)
        .filter(([, item]) => item !== null && item !== undefined && item !== '')
        .map(([label, item]) => ({ label, value: Array.isArray(item) ? item.join(' / ') : String(item) }))} />}
    </View>
  )
}

export function ScenarioStrip({
  scenarios,
}: {
  scenarios: Record<string, { profit?: number | null, attendance?: number | null }> | undefined
}) {
  const entries = [['conservative', '保守'], ['neutral', '中性'], ['optimistic', '乐观']] as const
  if (!scenarios || !Object.keys(scenarios).length) return null
  return (
    <View className={styles.scenarioStrip}>
      {entries.map(([key, label]) => {
        const scenario = scenarios[key]
        if (!scenario) return null
        return (
          <View className={styles.scenarioItem} key={key}>
            <Text className={styles.sourceLabel}>{label}</Text>
            <Text className={styles.itemValue}>{scenario.profit ?? '待补齐'}</Text>
            <Text className={styles.itemDescription}>预计人数 {scenario.attendance ?? '待补齐'}</Text>
          </View>
        )
      })}
    </View>
  )
}

export function WorkBriefing({
  briefing,
}: {
  briefing?: {
    today_change_count?: number
    top_task?: { title?: string, status?: string, project_name?: string } | null
    active_project_count?: number
  } | null
}) {
  if (!briefing) return null
  return (
    <View className={styles.insightPanel}>
      <Text className={styles.insightTitle}>今日变化 {briefing.today_change_count || 0} 项</Text>
      {briefing.top_task && (
        <View className={styles.insightRow}>
          <View className={styles.listMain}>
            <Text className={styles.itemTitle}>{briefing.top_task.title || '暂无最重要事项'}</Text>
            <Text className={styles.itemDescription}>{briefing.top_task.project_name || ''}</Text>
          </View>
          <Text className={styles.status}>{briefing.top_task.status || ''}</Text>
        </View>
      )}
    </View>
  )
}

export function LifecycleTimeline({ currentStage }: { currentStage?: string | null }) {
  const stages = ['预测', '决策', '执行', '售票', '结算', '校准']
  return (
    <View className={styles.timeline}>
      {stages.map((stage) => <Text className={classNames(styles.timelineStep, stage === currentStage && styles.timelineStepActive)} key={stage}>{stage}</Text>)}
    </View>
  )
}

export function VariancePanel({
  loop,
}: {
  loop?: {
    forecast_profit?: number | null
    actual_profit?: number | null
    profit_variance?: number | null
    notes?: string | null
  } | null
}) {
  if (!loop) return null
  return (
    <View className={styles.insightPanel}>
      <Text className={styles.insightTitle}>预测与实际差异</Text>
      <KeyValueGrid items={[
        { label: '预测利润', value: loop.forecast_profit === null || loop.forecast_profit === undefined ? '待补齐' : String(loop.forecast_profit) },
        { label: '实际利润', value: loop.actual_profit === null || loop.actual_profit === undefined ? '待补齐' : String(loop.actual_profit) },
        { label: '利润差异', value: loop.profit_variance === null || loop.profit_variance === undefined ? '待补齐' : String(loop.profit_variance) },
      ]} />
      {loop.notes && <Text className={styles.itemDescription}>{loop.notes}</Text>}
    </View>
  )
}

export type MetricTone = 'default' | 'success' | 'warning' | 'danger'

export interface MetricItem {
  label: string
  value: string
  hint?: string
  tone?: MetricTone
  onTap?: () => void
}

const metricToneClass: Record<MetricTone, string> = {
  default: '',
  success: styles.metricValueSuccess,
  warning: styles.metricValueWarning,
  danger: styles.metricValueDanger,
}

export function MetricGrid({ items }: { items: MetricItem[] }) {
  if (!items.length) return null
  return (
    <View className={styles.metricGrid}>
      {items.map((item) => (
        <View
          className={classNames(styles.metricCard, item.onTap && styles.metricCardTap)}
          key={item.label}
          onClick={item.onTap}
        >
          <Text className={classNames(styles.metricValue, metricToneClass[item.tone || 'default'])}>{item.value}</Text>
          <Text className={styles.metricLabelText}>{item.label}</Text>
          {item.hint ? <Text className={styles.metricHint}>{item.hint}</Text> : null}
        </View>
      ))}
    </View>
  )
}

export type RingTone = 'gold' | 'success' | 'warning' | 'danger'

const ringColor: Record<RingTone, string> = {
  gold: '#d4af37',
  success: '#5cc793',
  warning: '#e2ab57',
  danger: '#f0837f',
}

export function ProgressRing({
  percent,
  label,
  caption,
  tone = 'gold',
}: {
  percent: number
  label: string
  caption?: string
  tone?: RingTone
}) {
  if (!Number.isFinite(percent)) return null
  const display = Math.round(percent)
  const clamped = Math.max(0, Math.min(100, display))
  return (
    <View className={styles.ringPanel}>
      <View
        className={styles.ringChart}
        style={{
          '--ring-progress': `${clamped * 3.6}deg`,
          backgroundImage: `conic-gradient(${ringColor[tone]} ${clamped * 3.6}deg, rgba(255, 255, 255, 0.08) 0deg)`,
        } as CSSProperties}
        role='img'
        aria-label={`${label} ${display}%`}
      >
        <View className={styles.ringInner}>
          <Text className={styles.ringValue}>{display}%</Text>
        </View>
      </View>
      <View className={styles.ringMeta}>
        <Text className={styles.ringLabel}>{label}</Text>
        {caption ? <Text className={styles.ringCaption}>{caption}</Text> : null}
      </View>
    </View>
  )
}

export function formatWan(value: number): string {
  const abs = Math.abs(value)
  if (abs >= 100000000) return `${(value / 100000000).toFixed(1)}亿`
  if (abs >= 10000) return `${(value / 10000).toFixed(1)}万`
  return String(Math.round(value))
}

export interface ScenarioBarItem {
  label: string
  value: number | null | undefined
}

export function ScenarioBars({
  title,
  items,
  note,
}: {
  title: string
  items: ScenarioBarItem[]
  note?: string
}) {
  const validItems = items.filter((item): item is { label: string, value: number } => (
    typeof item.value === 'number' && Number.isFinite(item.value)
  ))
  if (!validItems.length) return null
  const maxAbs = Math.max(...validItems.map((item) => Math.abs(item.value)), 1)
  return (
    <View className={styles.insightPanel}>
      <Text className={styles.insightTitle}>{title}</Text>
      {validItems.map((item) => {
        const negative = item.value < 0
        const width = Math.max(Math.abs(item.value) / maxAbs, item.value === 0 ? 0 : 0.02) * 50
        return (
          <View className={styles.barRow} key={item.label}>
            <Text className={styles.barLabel}>{item.label}</Text>
            <View className={styles.barTrack}>
              <View className={styles.barZero} />
              <View
                className={classNames(styles.barFill, negative ? styles.barFillNegative : styles.barFillPositive)}
                style={negative ? { right: '50%', width: `${width}%` } : { left: '50%', width: `${width}%` }}
              />
            </View>
            <Text className={classNames(styles.barValue, negative && styles.barValueNegative)}>
              {negative ? '-' : ''}{formatWan(Math.abs(item.value))}
            </Text>
          </View>
        )
      })}
      {note ? <Text className={styles.sourceLabel}>{note}</Text> : null}
    </View>
  )
}

export function FormField({
  label,
  value,
  placeholder,
  type = 'text',
  onChange,
}: {
  label: string
  value: string
  placeholder?: string
  type?: 'text' | 'number'
  onChange: (value: string) => void
}) {
  return (
    <View className={styles.field}>
      <Text className={styles.fieldLabel}>{label}</Text>
      <Input className={styles.input} type={type} value={value} placeholder={placeholder} onInput={(event) => onChange(event.detail.value)} />
    </View>
  )
}

export function CandidateField<T>({
  label,
  value,
  placeholder,
  initialSections,
  onInput,
  onSearch,
  onSelect,
}: {
  label?: string
  value: string
  placeholder?: string
  initialSections: Array<SearchSelectSection<T>>
  onInput: (value: string) => void
  onSearch: (keyword: string) => Promise<Array<SearchSelectSection<T>>>
  onSelect: (option: SearchSelectOption<T>) => void
}) {
  return (
    <View className={styles.field}>
      {label && <Text className={styles.fieldLabel}>{label}</Text>}
      <SearchSelect value={value} placeholder={placeholder} initialSections={initialSections} onInput={onInput} onSearch={onSearch} onSelect={onSelect} />
    </View>
  )
}

export function BusinessList({
  items,
  onOpenDetail,
}: {
  items: DisplayItem[]
  onOpenDetail: (item: DisplayItem) => void
}) {
  return (
    <>
      {items.map((item) => (
        <View
          className={classNames(styles.listItem, item.detailRef && styles.clickableItem)}
          key={item.id}
          onClick={item.detailRef ? () => onOpenDetail(item) : undefined}
        >
          <View className={styles.listMain}>
            <Text className={styles.itemTitle}>{item.title}</Text>
            <Text className={styles.itemDescription}>{item.description}</Text>
            {Array.isArray(item.context?.actionability) && (
              <Text className={styles.sourceLabel}>
                {item.context.actionability
                  .map((action) => ({ accept: '可接受', reject: '可拒绝', block: '可阻塞', submit: '可提交' }[String(action)]))
                  .filter(Boolean)
                  .join(' · ')}
              </Text>
            )}
            {item.context?.evidence_required === true && <Text className={styles.sourceLabel}>需补证据</Text>}
          </View>
          <View className={styles.itemAside}>
            {item.value && <Text className={styles.itemValue}>{item.value}</Text>}
            <Text className={styles.status}>{item.status}</Text>
            {item.detailRef && <Text className={styles.detailChevron}>›</Text>}
          </View>
        </View>
      ))}
    </>
  )
}

export function TaskBatchList({
  items,
  selectedTaskIds,
  expandedTaskIds,
  onToggleSelection,
  onToggleDetails,
  onOpenDetail,
}: {
  items: DisplayItem[]
  selectedTaskIds: number[]
  expandedTaskIds: number[]
  onToggleSelection: (taskId: number) => void
  onToggleDetails: (taskId: number) => void
  onOpenDetail: (item: DisplayItem) => void
}) {
  return (
    <>
      <Text className={styles.taskSelectionSummary}>已选择 {selectedTaskIds.length} 项任务</Text>
      {items.map((item) => {
        const taskId = Number(item.context?.task_id || item.detailRef?.entity_id || 0)
        const selected = selectedTaskIds.includes(taskId)
        const expanded = expandedTaskIds.includes(taskId)
        return (
          <View className={classNames(styles.listItem, styles.taskItem)} key={item.id}>
            <Button className={classNames(styles.taskCheckbox, selected && styles.taskCheckboxSelected)} aria-label={`选择${item.title}`} onClick={() => onToggleSelection(taskId)}>
              {selected ? '✓' : ''}
            </Button>
            <View className={styles.listMain} onClick={() => onToggleDetails(taskId)}>
              <Text className={styles.itemTitle}>{item.title}</Text>
              <Text className={classNames(styles.itemDescription, expanded && styles.itemDescriptionExpanded)}>{item.description}</Text>
              {expanded && <View className={styles.taskDetails}><Text>{item.details || '暂无更多任务信息'}</Text></View>}
            </View>
            <View className={styles.itemAside}>
              <Text className={styles.status}>{item.status}</Text>
              {item.detailRef && <Button className={styles.detailButton} aria-label={`查看${item.title}详情`} onClick={() => onOpenDetail(item)}>›</Button>}
            </View>
          </View>
        )
      })}
    </>
  )
}
