export interface DisplayItem {
  id: string
  title: string
  description: string
  status: string
  value?: string
}

export interface ProjectDraft {
  name: string
  type: string
  artist_name: string
  city: string
  venue: string
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

