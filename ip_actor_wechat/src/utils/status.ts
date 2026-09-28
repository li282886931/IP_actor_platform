const statusLabels: Record<string, string> = {
  active: '进行中',
  archived: '已归档',
  available: '可用',
  blocked: '已阻塞',
  calculated: '已测算',
  closed: '已关闭',
  completed: '已完成',
  confirmed: '已确认',
  disabled: '已停用',
  draft: '草稿',
  enabled: '已启用',
  failed: '失败',
  in_progress: '进行中',
  on_sale: '售票中',
  open: '待处理',
  pending: '待处理',
  pending_confirmation: '待确认',
  queued: '排队中',
  read: '已读',
  revoked: '已撤回',
  running: '处理中',
  settled: '已结算',
  submitted: '待验收',
  unread: '未读',
  unverified: '待核验',
  verified: '已核验',
}

export const statusLabel = (status?: string | null) => (
  status ? statusLabels[status] || status : ''
)
