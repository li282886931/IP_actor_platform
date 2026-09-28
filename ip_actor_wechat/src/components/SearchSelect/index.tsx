import { useEffect, useState } from 'react'
import { Input, Text, View } from '@tarojs/components'

import styles from './index.module.scss'

export interface SearchSelectOption<T = unknown> {
  entityType: string
  entityId: string | number
  label: string
  description?: string
  value: T
}

export interface SearchSelectSection<T = unknown> {
  entityType: string
  label: string
  options: Array<SearchSelectOption<T>>
}

interface SearchSelectProps<T = unknown> {
  value: string
  placeholder?: string
  onInput: (value: string) => void
  onSearch: (keyword: string) => Promise<Array<SearchSelectSection<T>>>
  onSelect: (option: SearchSelectOption<T>) => void
}

type SearchState = 'idle' | 'loading' | 'success' | 'empty' | 'error'

export default function SearchSelect<T>({
  value,
  placeholder,
  onInput,
  onSearch,
  onSelect,
}: SearchSelectProps<T>) {
  const [query, setQuery] = useState(value)
  const [sections, setSections] = useState<Array<SearchSelectSection<T>>>([])
  const [status, setStatus] = useState<SearchState>('idle')
  const [open, setOpen] = useState(false)

  useEffect(() => {
    setQuery(value)
  }, [value])

  useEffect(() => {
    const keyword = query.trim()
    if (!keyword) {
      setSections([])
      setStatus('idle')
      setOpen(false)
      return undefined
    }

    let active = true
    setStatus('loading')
    setOpen(true)
    const timer = setTimeout(() => {
      onSearch(keyword)
        .then((nextSections) => {
          if (!active) return
          const populatedSections = nextSections.filter((section) => section.options.length > 0)
          setSections(populatedSections)
          setStatus(populatedSections.length ? 'success' : 'empty')
        })
        .catch(() => {
          if (!active) return
          setSections([])
          setStatus('error')
        })
    }, 300)

    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [onSearch, query])

  const updateQuery = (nextValue: string) => {
    setQuery(nextValue)
    onInput(nextValue)
  }

  return (
    <View className={styles.root}>
      <Input
        className={styles.input}
        value={query}
        placeholder={placeholder}
        onFocus={() => {
          if (query.trim()) setOpen(true)
        }}
        onBlur={() => {
          setTimeout(() => setOpen(false), 150)
        }}
        onInput={(event) => {
          const nextValue = event.detail?.value ?? ''
          updateQuery(nextValue)
        }}
      />
      {open && (
        <View className={styles.dropdown}>
          {status === 'loading' && <Text className={styles.state}>正在搜索...</Text>}
          {status === 'empty' && <Text className={styles.state}>未找到匹配结果</Text>}
          {status === 'error' && <Text className={styles.state}>搜索失败，请稍后重试</Text>}
          {status === 'success' && sections.map((section) => (
            <View className={styles.group} key={section.entityType}>
              <Text className={styles.groupLabel}>{section.label}</Text>
              {section.options.map((option) => (
                <View
                  className={styles.option}
                  key={`${option.entityType}-${option.entityId}`}
                  onClick={() => {
                    setQuery(option.label)
                    setOpen(false)
                    onInput(option.label)
                    onSelect(option)
                  }}
                >
                  <View className={styles.optionMain}>
                    <Text className={styles.optionLabel}>{option.label}</Text>
                    {option.description && (
                      <Text className={styles.optionDescription}>{option.description}</Text>
                    )}
                  </View>
                  <Text className={styles.selectLabel}>选择</Text>
                </View>
              ))}
            </View>
          ))}
        </View>
      )}
    </View>
  )
}
