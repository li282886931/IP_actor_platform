export const DEFAULT_API_BASE = 'http://127.0.0.1:8000'

export const REQUEST_TIMEOUT_MS = 120000

export const CLIENT_SOURCE = 'mp'

export const STORAGE_KEYS = {
  apiBase: 'starhub-api-base',
  token: 'starhub-token',
  tenant: 'starhub-tenant',
  user: 'starhub-user',
  projectDraft: 'starhub-project-draft',
  projectId: 'starhub-project-id',
  versionId: 'starhub-version-id',
  taskId: 'starhub-task-id',
} as const
