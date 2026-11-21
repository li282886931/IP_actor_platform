import { useRef, useState } from 'react'
import { Fields, Values, kindLabels, parseFields, recordFields, statusLabels } from '../pages/decisionFields'
import ScoreBreakdown from './ScoreBreakdown'

const kindsByRole = { B: ['incremental', 'brand_match', 'city_fit', 'artist_benchmark'], Brand: ['sponsorship', 'brand_match'], Investor: ['investment'], G: ['asset', 'impact', 'city_fit'],
  Artist: ['artist_post', 'artist_metrics', 'artist_benchmark'], C: ['wishlist', 'checkin'] }
const auxiliary = kind => ['brand_match', 'city_fit', 'artist_benchmark'].includes(kind)
const needsProject = kind => auxiliary(kind) || ['incremental', 'sponsorship', 'investment', 'impact', 'asset', 'artist_metrics'].includes(kind)
export default function OperatingRecords({ role, data, selectedProject, mutate, busy, onError }) {
  const [kind, setKind] = useState(kindsByRole[role][0]), [title, setTitle] = useState(''), [values, setValues] = useState({})
  const [flows, setFlows] = useState([]), [editing, setEditing] = useState(null), [proofs, setProofs] = useState(''), [note, setNote] = useState('')
  const draftKey = useRef(crypto.randomUUID())
  const [modelRule, setModelRule] = useState(''), [metrics, setMetrics] = useState({})
  const modelRules = (data.rules || []).filter(r => r.config.auxiliary_models?.[kind])
  const model = modelRules.find(r => r.id === Number(modelRule))?.config.auxiliary_models[kind]
  const fields = [...recordFields[kind], ...(['artist_post', 'wishlist', 'checkin'].includes(kind) ? [] : [{ key: 'evidence_ids', label: '证明材料编号（逗号分隔）', type: 'ids' }])]
  const records = data.records.filter(r => kindsByRole[role].includes(r.kind))
  async function save(e) {
    e.preventDefault()
    try {
      const payload = parseFields(fields, values)
      if (auxiliary(kind)) {
        payload.rule_version_id = Number(modelRule)
        payload.source = values.source || ''
        payload.metrics = Object.fromEntries(Object.entries(metrics).filter(([, v]) => v !== '').map(([k, v]) => [k, Number(v)]))
      }
      if (kind === 'investment') payload.cashflows = flows.map(f => ({ date: f.date, amount: Number(f.amount) }))
      if (await mutate('records', { kind, title, payload, record_key: editing?.record_key || draftKey.current,
        ...(editing ? { revision: editing.revision } : {}), ...(needsProject(kind) || editing?.project_id ? { project_id: editing?.project_id || Number(selectedProject) } : {}) })) {
        setTitle(''); setValues({}); setMetrics({}); setFlows([]); setEditing(null); draftKey.current = crypto.randomUUID()
      }
    } catch (e) { onError(e.message) }
  }
  function edit(row) {
    setKind(row.kind); setTitle(row.title); setEditing(row)
    setValues(Object.fromEntries(Object.entries(row.payload).filter(([, v]) => typeof v !== 'object' || Array.isArray(v)).map(([k, v]) => [k, Array.isArray(v) ? v.filter(x => typeof x !== 'object').join(',') : typeof v === 'boolean' ? String(v) : v ?? ''])))
    setFlows(row.payload.cashflows || [])
    setModelRule(String(row.payload.rule_version_id || '')); setMetrics(row.payload.metrics || {})
  }
  async function verify(row) {
    try {
      const ids = parseFields([{ key: 'evidence_ids', type: 'ids' }], { evidence_ids: proofs }).evidence_ids || []
      await mutate(`records/${row.id}/verify`, { evidence_ids: ids, note })
    } catch (e) { onError(e.message) }
  }
  return <>
    <section className="panel"><div className="panel-heading"><h3>{editing ? '修改经营记录' : '新增经营记录'}</h3><span>真实参数，缺项不计算</span></div>
      <form onSubmit={save}><div className="decision-form-grid"><label>记录类型<select aria-label="记录类型" value={kind} disabled={Boolean(editing)} onChange={e => { setKind(e.target.value); setValues({}); setMetrics({}); setModelRule(''); setFlows([]) }}>{kindsByRole[role].map(k => <option key={k} value={k}>{kindLabels[k]}</option>)}</select></label>
        <label>记录名称<input required aria-label="记录名称" value={title} onChange={e => setTitle(e.target.value)} /></label></div>
        {needsProject(kind) && !selectedProject && <p className="role-disclosure">请先选择已授权项目。</p>}
        <Fields fields={fields} values={values} setValues={setValues} />
        {auxiliary(kind) && <>
          <label>辅助评分规则版本<select required aria-label="辅助评分规则版本" value={modelRule} onChange={e => { setModelRule(e.target.value); setMetrics({}) }}><option value="">选择已配置的模型版本</option>{modelRules.map(r => <option key={r.id} value={r.id}>v{r.version_no} · {r.name} · {statusLabels[r.status]}</option>)}</select></label>
          {!modelRules.length && <p className="role-disclosure">请由项目运营安装或配置完整规则包。</p>}
          {model && <><p>{model.source}。{kind === 'artist_benchmark' ? '输入相对已核验参考基准的系数，超过1时保留原值、评分封顶。' : '逐项填写有来源的0–1比例。'}</p>
            <Fields fields={model.criteria.map(c => ({ key: c.key, label: `${c.label}（${kind === 'artist_benchmark' ? '基准系数' : '0–1'}）`, type: 'number' }))} values={metrics} setValues={setMetrics} /></>}
          <label>指标来源与参考基准<textarea required aria-label="指标来源与参考基准" value={values.source || ''} onChange={e => setValues(old => ({ ...old, source: e.target.value }))} /></label>
        </>}
        {kind === 'investment' && <fieldset className="decision-cashflows"><legend>实际日期现金流（投入为负，回款为正）</legend>
          {flows.map((f, i) => <div className="decision-flow-row" key={i}><input type="date" required aria-label={`现金流${i + 1}日期`} value={f.date} onChange={e => setFlows(old => old.map((x, j) => i === j ? { ...x, date: e.target.value } : x))} />
            <input type="number" step="any" required aria-label={`现金流${i + 1}金额`} value={f.amount} onChange={e => setFlows(old => old.map((x, j) => i === j ? { ...x, amount: e.target.value } : x))} />
            <button type="button" className="button button-secondary" onClick={() => setFlows(old => old.filter((_, j) => i !== j))}>移除</button></div>)}
          <button type="button" className="button button-secondary" onClick={() => setFlows(old => [...old, { date: '', amount: '' }])}>添加现金流</button></fieldset>}
        <div className="collab-actions">{editing && <button type="button" className="button button-secondary" onClick={() => { setEditing(null); setValues({}); setTitle('') }}>取消修改</button>}<button className="button button-primary" disabled={busy || (needsProject(kind) && !selectedProject)}>保存测算记录</button></div>
      </form>
    </section>
    <section className="panel"><h3>已保存记录</h3>{!records.length && <p className="role-muted">暂无经营记录，录入后展示实际计算结果。</p>}
      {records.map(row => <article className="decision-record" key={row.id}><div className="workspace-compact-row"><div><strong>{row.title}</strong><small>{kindLabels[row.kind]} · {statusLabels[row.status]} · 修订 {row.revision}</small></div><button className="button button-secondary" onClick={() => edit(row)}>编辑</button></div>
        {auxiliary(row.kind) ? <ScoreBreakdown result={row.result} /> : <Values values={row.result} />}<details><summary>查看参数与来源</summary><Values values={row.payload} />{auxiliary(row.kind) && <p>来源：{row.payload.source} · 规则 #{row.payload.rule_version_id} · 模型快照随记录保存</p>}</details>
        {!['artist_post', 'wishlist', 'checkin'].includes(row.kind) && <details><summary>人工核验经营数据</summary><div className="decision-form-grid">
          <label>已核验材料编号<input aria-label={`记录${row.id}核验材料编号`} value={proofs} onChange={e => setProofs(e.target.value)} /></label>
          <label>核验说明<input aria-label={`记录${row.id}核验说明`} value={note} onChange={e => setNote(e.target.value)} /></label></div>
          <button className="button button-secondary" disabled={busy || !proofs || !note} onClick={() => verify(row)}>核验这条记录</button></details>}
      </article>)}
    </section>
  </>
}
