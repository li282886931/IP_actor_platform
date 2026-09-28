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
