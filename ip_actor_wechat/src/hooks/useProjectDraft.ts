import { useCallback, useState } from 'react'
import Taro from '@tarojs/taro'

import { STORAGE_KEYS } from '@/config/runtime'
import type { ProjectDraft } from '@/types/domain'

const initialDraft: ProjectDraft = {
  name: '',
  type: 'concert',
  artist_name: '',
  city: '',
  venue: '',
  schedule: '',
}

const numericKeys = new Set<keyof ProjectDraft>([
  'artist_id', 'venue_id', 'source_project_id', 'expected_attendance', 'available_funds',
  'avg_ticket_price', 'artist_fee', 'venue_cost', 'marketing_cost', 'production_cost', 'venue_capacity',
])

const candidatePatchKeys = new Set<keyof ProjectDraft>([
  'name', 'type', 'artist_id', 'artist_name', 'city', 'venue_id', 'venue', 'source_project_id',
  'schedule', 'expected_attendance', 'available_funds', 'avg_ticket_price', 'artist_fee',
  'venue_cost', 'marketing_cost', 'production_cost', 'venue_capacity',
])

const readDraft = (): ProjectDraft => {
  const stored = Taro.getStorageSync<ProjectDraft>(STORAGE_KEYS.projectDraft)
  return stored && typeof stored === 'object' ? { ...initialDraft, ...stored } : { ...initialDraft }
}

export function useProjectDraft() {
  const [draft, setDraft] = useState<ProjectDraft>(readDraft)

  const persist = useCallback((next: ProjectDraft) => {
    setDraft(next)
    Taro.setStorageSync(STORAGE_KEYS.projectDraft, next)
  }, [])

  const updateDraft = useCallback((key: keyof ProjectDraft, value: string) => {
    persist({
      ...draft,
      [key]: numericKeys.has(key) ? (value === '' ? undefined : Number(value)) : value,
    })
  }, [draft, persist])

  const applyCandidatePatch = useCallback((patch: Partial<ProjectDraft> | Record<string, unknown>) => {
    const supportedPatch = Object.fromEntries(
      Object.entries(patch).filter(([key, value]) => (
        candidatePatchKeys.has(key as keyof ProjectDraft)
        && (typeof value === 'string' || typeof value === 'number')
      )),
    ) as Partial<ProjectDraft>
    persist({ ...draft, ...supportedPatch })
  }, [draft, persist])

  return { draft, updateDraft, applyCandidatePatch }
}
