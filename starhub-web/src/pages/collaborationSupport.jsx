import { useEffect, useRef, useState } from 'react'
import { collaborationMutation, getCollaboration } from '../collaborationApi'

export const titles = { Admin: '授权与异常协作', B: '项目执行协作', Brand: '品牌合作协作', G: '材料核验协作', Investor: '投资评估协作', Artist: '艺人履约协作', C: '收藏与预约' }
export const kinds = { invitation: '合作邀请', brand_demand: '品牌需求', rights: '合作权益', supplement: '补充材料', official_result: '审批结果登记', impact: '实际成效登记', investment: '投资意见', profile_change: '资料修改申请', incident: '异常分派', task: '执行任务' }
export const roleKinds = { Admin: ['task', 'incident'], B: ['invitation', 'task', 'rights'], Brand: ['brand_demand', 'rights'], G: ['supplement', 'official_result', 'impact'], Investor: ['investment'], Artist: ['profile_change'], C: [] }
export const targets = { invitation: ['Brand', 'Investor', 'Artist'], task: ['root', 'B', 'Brand', 'G', 'Investor', 'Artist'], rights: ['B', 'Brand'], brand_demand: ['B'], supplement: ['B'], official_result: ['B', 'root'], impact: ['B', 'root'], investment: ['B'], profile_change: ['root'], incident: ['root', 'B'] }
export const statusText = { draft: '私有草稿', shared: '待处理', replied: '待确认', confirmed: '双方已确认', in_progress: '执行中', submitted: '待验收', needs_more: '需补充', accepted: '已验收', declined: '已拒绝', withdrawn: '已撤回', disputed: '有争议' }
export const actionText = { edit: '修改草稿', share: '发送事项', withdraw: '撤回事项', reply: '提交回复', decline: '拒绝邀请', confirm: '确认权益', deliver: '提交交付', approve: '确认验收', return: '退回补充', dispute: '登记争议', start: '开始执行', submit: '提交结果' }
export const ended = row => ['accepted', 'declined', 'withdrawn', 'disputed'].includes(row.status)
export const labelMap = { purpose: '邀请目的', start: '开始时间', end: '结束时间', goal: '合作目标', city: '目标城市', audience: '目标受众', resources: '可提供资源', budget: '预算（元）', deliverables: '权益交付清单', due_date: '截止日期', acceptance: '验收标准', amount: '金额（元）', materials: '待补材料', authority: '发文机构', reference: '官方文号', source_url: '原始来源链接', recorded_at: '来源登记时间', result: '登记结果', value: '实际数值', unit: '数值单位', region: '成效地域', period: '统计期间', conditions: '投资条件', name: '艺人名称', tags: '艺人标签', profile: '艺人介绍', introduction: '介绍正文', source_type: '异常类型', source_id: '来源编号', instructions: '执行要求', evidence_ids: '证明材料编号', confirmations: '已确认账号', delivery_user_id: '交付负责人编号', brand_user_id: '品牌验收负责人编号', changes: '修改内容', base: '修改前资料', artist_id: '艺人编号', note: '说明', last_note: '最近处理结果', last_actor_id: '最近处理人编号', status: '状态', revision: '修订号', title: '事项标题', owner_id: '发起人编号', recipient_id: '处理人编号', version_id: '测算版本编号', project_id: '项目编号', id: '记录编号', response: '回复结果', rejection_reason: '退回原因', task_id: '执行任务编号' }
const field = (key, type = 'text', required = true, options) => ({ key, type, required, options })
const source = [field('authority'), field('reference'), field('source_url', 'url'), field('recorded_at', 'datetime-local'), field('result', 'textarea')]
export const fieldsByKind = {
  invitation: [field('purpose', 'textarea'), field('start', 'datetime-local', false), field('end', 'datetime-local', false)],
  task: [field('instructions', 'textarea'), field('due_date', 'date', false)],
  brand_demand: [field('goal', 'select', true, ['曝光', '互动', '转化']), field('city'), field('audience'), field('resources', 'textarea'), field('budget', 'number', false)],
  rights: [field('deliverables', 'textarea'), field('due_date', 'date'), field('acceptance', 'textarea'), field('amount', 'number', false)],
  supplement: [field('materials', 'textarea'), field('due_date', 'date')],
  official_result: source,
  impact: [...source, field('value', 'number'), field('unit'), field('region'), field('period')],
  investment: [field('conditions', 'textarea'), field('amount', 'number', false)],
  profile_change: [field('name', 'text', false), field('tags', 'text', false), field('profile', 'textarea', false)],
  incident: [field('source_type', 'select', true, ['job', 'quality']), field('source_id', 'number'), field('instructions', 'textarea')],
}
export const splitList = value => value.split(/[,，\n]/).map(x => x.trim()).filter(Boolean)
export function payloadFor(kind, values) {
  const payload = {}
  for (const f of fieldsByKind[kind] || []) {
    const v = values[f.key]
    if (v === '' || v === undefined || v === null) continue
    payload[f.key] = f.type === 'number' ? Number(v) : f.type === 'datetime-local' ? new Date(v).toISOString() : f.key === 'profile' ? { introduction: v } : v
  }
  if (kind !== 'profile_change' && values.evidence_ids?.trim()) {
    const ids = splitList(values.evidence_ids)
    if (ids.some(v => !/^[1-9]\d*$/.test(v))) throw new Error('证明材料编号须为正整数，以逗号分隔')
    payload.evidence_ids = ids.map(Number)
  }
  return payload
}
export function formValues(kind, payload = {}) {
  const source = kind === 'profile_change' ? payload.changes || payload : payload
  return Object.fromEntries([...fieldsByKind[kind].map(f => {
    let value = source[f.key] ?? ''
    if (f.type === 'datetime-local' && value) {
      const date = new Date(value)
      value = new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
    }
    if (f.key === 'profile') value = value.introduction || ''
    return [f.key, value]
  }), ['evidence_ids', (source.evidence_ids || []).join(',')]])
}
export function focusScore(project, focus = {}) {
  return (focus.cities?.includes(project.city) ? 4 : 0) + (focus.goals?.includes(project.goal) ? 2 : 0) + (focus.risk_levels?.includes(project.risk_level) ? 1 : 0)
}
export function StructuredValues({ value, depth = 0 }) {
  if (value === null || value === undefined || value === '') return <span>未填写</span>
  if (Array.isArray(value)) return <span>{value.length ? value.map(v => typeof v === 'object' ? JSON.stringify(v) : String(v)).join('、') : '无'}</span>
  if (typeof value !== 'object') return <span>{statusText[value] || String(value)}</span>
  return <dl className="collab-values">{Object.entries(value).filter(([k]) => !['tenant_id', 'created_at', 'updated_at'].includes(k)).map(([key, v]) => <div key={key}><dt>{labelMap[key] || key}</dt><dd>{depth < 4 ? <StructuredValues value={v} depth={depth + 1} /> : JSON.stringify(v)}</dd></div>)}</dl>
}
export function PayloadFields({ kind, values, onChange, prefix = '' }) {
  const fields = [...fieldsByKind[kind], ...(kind === 'profile_change' ? [] : [field('evidence_ids', 'text', false)])]
  return <div className="collab-form-grid">{fields.map(f => <label key={f.key}>
    <span>{labelMap[f.key]}{!f.required && '（选填）'}</span>
    {f.type === 'textarea' ? <textarea aria-label={`${prefix}${labelMap[f.key]}`} required={f.required} value={values[f.key] ?? ''} onChange={e => onChange(f.key, e.target.value)} rows={3} />
      : f.type === 'select' ? <select aria-label={`${prefix}${labelMap[f.key]}`} required={f.required} value={values[f.key] ?? ''} onChange={e => onChange(f.key, e.target.value)}><option value="">请选择</option>{f.options.map(v => <option key={v} value={v}>{v === 'job' ? '采集失败' : v === 'quality' ? '质量问题' : v}</option>)}</select>
        : <input aria-label={`${prefix}${labelMap[f.key]}`} type={f.type} required={f.required} min={f.type === 'number' && f.key !== 'value' ? 0 : undefined} step={f.type === 'number' ? 'any' : undefined} value={values[f.key] ?? ''} onChange={e => onChange(f.key, e.target.value)} />}
  </label>)}</div>
}
export function useCollaboration() {
  const [data, setData] = useState(null), [error, setError] = useState(''), [busy, setBusy] = useState(false)
  const mounted = useRef(true), sequence = useRef(0), request = useRef(null), lock = useRef(false)
  async function reload() {
    const id = ++sequence.current
    try {
      const response = await getCollaboration()
      if (mounted.current && id === sequence.current) setData(response.data.data)
    } catch (e) { if (mounted.current) setError(e.response?.data?.detail || '协作记录加载失败，请重试') }
  }
  useEffect(() => { mounted.current = true; reload(); return () => { mounted.current = false; sequence.current++ } }, [])
  async function mutate(path, body) {
    if (lock.current) return false
    lock.current = true; setBusy(true); setError('')
    const signature = JSON.stringify([path, body])
    if (request.current?.signature !== signature) request.current = { signature, key: crypto.randomUUID() }
    try {
      await collaborationMutation(path, body, request.current.key)
      request.current = null
      await reload()
      return true
    } catch (e) {
      if (mounted.current) setError(e.response?.data?.detail || e.message || '操作失败，请重试')
      if (e.response) request.current = null
      if (e.response?.status === 409) await reload()
      return false
    } finally { lock.current = false; if (mounted.current) setBusy(false) }
  }
  return { data, error, setError, busy, mutate, reload }
}
