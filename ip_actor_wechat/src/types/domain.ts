export interface DisplayItem {
  id: string
  title: string
  description: string
  status: string
  value?: string
  details?: string
  context?: Record<string, unknown>
  detailRef?: MiniappEntityRef | null
}

export interface ProjectDraft {
  name: string
  type: string
  artist_id?: number
  artist_name: string
  city: string
  venue_id?: number
  venue: string
  source_project_id?: number
  schedule: string
  expected_attendance?: number
  available_funds?: number
  avg_ticket_price?: number
  artist_fee?: number
  venue_cost?: number
  marketing_cost?: number
  production_cost?: number
}

export interface SessionData {
  token?: string
  user?: Record<string, unknown>
  current_tenant?: Record<string, unknown>
}

export interface MiniappScreenSummary {
  title: string
  subtitle?: string | null
  highlight?: string | null
}

export interface MiniappScreenItem {
  id: string
  entity_type: string
  title: string
  description?: string | null
  status?: string | null
  value?: string | null
  details?: string | null
  context: Record<string, unknown>
  detail_ref?: MiniappEntityRef | null
}

export interface MiniappEntityRef {
  entity_type: string
  entity_id: number
}

export interface MiniappEntityField {
  key: string
  label: string
  value: string
}

export interface MiniappEntitySection {
  key: string
  title: string
  content: string
}

export interface MiniappEntityRelatedItem {
  title: string
  subtitle?: string | null
  detail_ref: MiniappEntityRef
}

export interface MiniappEntityDetail {
  entity_type: string
  entity_id: number
  title: string
  subtitle?: string | null
  status?: string | null
  media_url?: string | null
  fields: MiniappEntityField[]
  sections: MiniappEntitySection[]
  related_items: MiniappEntityRelatedItem[]
  actions: Array<{
    label: string
    target_screen?: string | null
  }>
}

export interface MiniappScreenEmptyState {
  title: string
  description?: string | null
  action?: {
    label: string
    target_screen?: string | null
  } | null
}

export interface MiniappScreenData {
  screen_id: string
  summary: MiniappScreenSummary
  items: MiniappScreenItem[]
  options: Record<string, unknown>
  context: Record<string, unknown>
  empty_state?: MiniappScreenEmptyState | null
}

export interface MiniappScreenContext {
  project_id?: number
  version_id?: number
  task_id?: number
  artist_id?: number
  keyword?: string
}

export interface MiniappSearchItem {
  entity_type: string
  entity_id: string | number
  label: string
  description?: string | null
  value: unknown
}

export interface MiniappSearchGroup {
  entity_type: string
  label: string
  items: MiniappSearchItem[]
}

export interface MiniappSearchResult {
  keyword: string
  groups: MiniappSearchGroup[]
}
