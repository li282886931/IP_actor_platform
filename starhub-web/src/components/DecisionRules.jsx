import { useState } from 'react'
import { Fields } from '../pages/decisionFields'

const thresholdFields = [
  ['comprehensive_breakeven', '综合保本红线（0–1）'], ['stop_loss', '止损比例（0–1）'], ['public_sale', '最低公售比例（0–1）'],
  ['artist_fee', '艺人费用预警比例（0–1）'], ['presale', '预售预警比例（0–1）'], ['large_spend', '不可退大额标准（元）'],
  ['application_days', '报批提前天数'], ['permit_days', '批文提前天数'],
].map(([key, label]) => ({ key, label, type: 'number' }))
const metrics = ['pure_breakeven', 'comprehensive_breakeven', 'artist_fee_ratio', 'stop_loss_ratio', 'public_sale_ratio', 'presale_ratio', 'predicted_profit', 'expected_occupancy', 'cost_overrun_ratio', 'weather_risk', 'reputation_risk', 'schedule_conflict']
const metricLabels = ['纯票房保本率', '综合保本率', '艺人费用比例', '止损比例', '公售比例', '预售比例', '预测利润', '预计上座率', '成本超支比例', '天气风险值', '舆情风险值', '档期冲突']
const operations = [['gt', '>'], ['gte', '≥'], ['lt', '<'], ['lte', '≤'], ['eq', '=']]
function Normalization({ item, update, prefix, metricOptions }) {
  return <div className="decision-form-grid">
    <label>归一方向<select aria-label={`${prefix}归一方向`} value={item.method || 'manual'} onChange={e => update('method', e.target.value)}>
      {metricOptions && <option value="manual">人工评分</option>}<option value="linear_high">正向（越高越好）</option><option value="linear_low">反向（越低越好）</option></select></label>
    {metricOptions && <label>绑定指标<select aria-label={`${prefix}绑定指标`} value={item.metric || ''} onChange={e => update('metric', e.target.value || null)}>
      <option value="">未绑定</option>{Object.entries(metricOptions).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>}
    {['floor', 'ceiling', 'weight', 'max_score'].map((k, i) => <label key={k}>{['下界', '上界', '权重', '满分'][i]}<input required type="number" step="any" min={i > 1 ? '.001' : undefined} aria-label={`${prefix}${['下界', '上界', '权重', '满分'][i]}`} value={item[k] ?? (k === 'floor' ? 0 : k === 'ceiling' ? 1 : '')} onChange={e => update(k, e.target.value)} /></label>)}
    <label>定义来源<input aria-label={`${prefix}来源`} value={item.source || ''} onChange={e => update('source', e.target.value)} /></label>
  </div>
}
function PredicateFields({ item, update, prefix, metricOptions }) {
  return <>
    <label>指标<select aria-label={`${prefix}指标`} value={item.field} onChange={e => update('field', e.target.value)}>{Object.entries(metricOptions).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
    <label>比较<select aria-label={`${prefix}比较`} value={item.op} onChange={e => update('op', e.target.value)}>{operations.map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
    <label>阈值引用<select aria-label={`${prefix}阈值引用`} value={item.threshold_ref || ''} onChange={e => update('threshold_ref', e.target.value || null)}><option value="">固定值</option>{thresholdFields.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}</select></label>
    {!item.threshold_ref && !item.compare_field && <label>固定阈值<input required type="number" step="any" aria-label={`${prefix}阈值`} value={item.value} onChange={e => update('value', e.target.value)} /></label>}
  </>
}
const parseCriterion = d => ({ ...d, weight: Number(d.weight), max_score: Number(d.max_score),
  ...(d.method && d.method !== 'manual' ? { floor: Number(d.floor), ceiling: Number(d.ceiling) } : {}) })
export default function DecisionRules({ config, setConfig, catalog, rules, mutate, busy }) {
  const [name, setName] = useState(''), [source, setSource] = useState(''), [reviewed, setReviewed] = useState(false)
  const update = (key, i, field, value) => setConfig(old => ({ ...old, [key]: old[key].map((d, j) => i === j ? { ...d, [field]: value } : d) }))
  const metricOptions = catalog?.metrics || Object.fromEntries(metrics.map((k, i) => [k, metricLabels[i]]))
  const updateAux = (model, i, field, value) => setConfig(old => ({ ...old, auxiliary_models: { ...old.auxiliary_models,
    [model]: { ...old.auxiliary_models[model], criteria: old.auxiliary_models[model].criteria.map((c, j) => i === j ? { ...c, [field]: value } : c) } } }))
  function loadCatalog() {
    setConfig(structuredClone(catalog.config)); setName(catalog.name); setSource(catalog.source); setReviewed(false)
  }
  async function save(e) {
    e.preventDefault()
    const parsed = { ...config, thresholds: Object.fromEntries(Object.entries(config.thresholds).map(([k, v]) => [k, v === '' || v == null ? null : Number(v)])),
      dimensions: config.dimensions.map(parseCriterion),
      conditions: config.conditions.map(c => ({ ...c, value: Number(c.value),
        ...(c.applies_when ? { applies_when: c.applies_when.map(p => ({ ...p, value: Number(p.value) })) } : {}) })),
      ...(config.auxiliary_models ? { auxiliary_models: Object.fromEntries(Object.entries(config.auxiliary_models).map(([k, m]) => [k, { ...m, criteria: m.criteria.map(parseCriterion) }])) } : {}) }
    await mutate('rules', { name, source, config: parsed, reviewed })
  }
  return <details className="panel decision-rule-editor"><summary>规则版本与评分配置</summary>
    <p>内置包补齐12维、32条规则、12类风险与3套辅助模型。定义包含平台建议，默认待核验；保存产生新版本，历史报告保持原口径。</p>
    {catalog && <div className="decision-catalog-actions"><p>{catalog.notice}</p><div className="collab-actions">
      <button type="button" className="button button-secondary" disabled={busy} onClick={loadCatalog}>载入完整建议包</button>
      <button type="button" className="button button-secondary" disabled={busy} onClick={() => mutate('catalog/install', {})}>安装待核验规则包</button></div></div>}
    <label>载入已有版本<select aria-label="载入已有版本" defaultValue="" onChange={e => { const rule = rules.find(r => r.id === Number(e.target.value)); if (rule) { setConfig(structuredClone(rule.config)); setName(`${rule.name}修订`); setSource(rule.source); setReviewed(false) } }}><option value="">选择版本</option>{rules.map(r => <option key={r.id} value={r.id}>v{r.version_no} · {r.name} · {r.status === 'verified' ? '已核验' : '待核验'}</option>)}</select></label>
    <form onSubmit={save}><div className="decision-form-grid"><label>新版本名称<input required aria-label="新版本名称" value={name} onChange={e => setName(e.target.value)} /></label>
      <label>规则来源与回测依据<input required aria-label="规则来源与回测依据" value={source} onChange={e => setSource(e.target.value)} /></label></div>
      <Fields fields={thresholdFields} values={config.thresholds} setValues={update => setConfig(old => ({ ...old, thresholds: update(old.thresholds) }))} />
      <div className="panel-heading"><h3>12维评分卡</h3><button type="button" className="button button-secondary" disabled={busy} onClick={() => setConfig(old => ({ ...old, dimensions: Array.from({ length: 12 }, (_, i) => ({
        key: `dimension${i + 1}`, label: '', category: i < 6 ? 'income' : 'risk', weight: 1, max_score: 10,
      })) }))}>录入12维</button></div>
      <p>六项收入、六项成本风险，权重归一到120分。自动模型绑定真实指标；缺少任何维度不输出完整总分。</p>
      <div className="decision-config-rows">{config.dimensions.map((d, i) => <div className="decision-config-item" key={d.key}>
        <div className="decision-dimension"><span>{d.category === 'income' ? '收入' : '成本风险'} {i % 6 + 1}</span><input aria-label={`维度${i + 1}名称`} required placeholder="核验维度名称" value={d.label} onChange={e => update('dimensions', i, 'label', e.target.value)} /><span>权重 {d.weight} · 满分 {d.max_score}</span></div>
        <details open={config.dimensions.length === 1}><summary>指标绑定、权重与归一参数</summary><Normalization item={d} prefix={`维度${i + 1}`} metricOptions={metricOptions} update={(field, value) => update('dimensions', i, field, value)} /></details>
      </div>)}</div>
      <div className="panel-heading"><h3>IF-THEN 经验规则（{config.conditions.length}/32）</h3><button type="button" className="button button-secondary" disabled={busy || config.conditions.length >= 32} onClick={() => setConfig(old => ({ ...old, conditions: [...old.conditions, {
        key: `condition${Date.now()}`, field: 'comprehensive_breakeven', op: 'gt', value: '', severity: 'warning', message: '',
      }] }))}>添加规则</button></div>
      {config.conditions.map((c, i) => <details className="decision-config-item" key={c.key}><summary>{c.key} · {c.message || '填写规则说明'} · {({ warning: '预警', veto: '否决', plan: '预案' })[c.severity]}</summary>
        <div className="decision-form-grid">
          <PredicateFields item={c} prefix={`规则${i + 1}`} metricOptions={metricOptions} update={(field, value) => update('conditions', i, field, value)} />
          <label>与指标对比<select aria-label={`规则${i + 1}对比指标`} disabled={Boolean(c.threshold_ref)} value={c.compare_field || ''} onChange={e => update('conditions', i, 'compare_field', e.target.value || null)}><option value="">使用阈值</option>{Object.entries(metricOptions).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
          <label>动作<select aria-label={`规则${i + 1}结果`} value={c.severity} onChange={e => update('conditions', i, 'severity', e.target.value)}>{[['warning', '预警'], ['veto', '否决'], ['plan', '预案']].map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
          <label>处理建议<input required aria-label={`规则${i + 1}说明`} value={c.message} onChange={e => update('conditions', i, 'message', e.target.value)} /></label>
          <label>来源<input aria-label={`规则${i + 1}来源`} value={c.source || ''} onChange={e => update('conditions', i, 'source', e.target.value)} /></label>
          <label>风险分类<select aria-label={`规则${i + 1}风险分类`} value={c.risk_category || ''} onChange={e => update('conditions', i, 'risk_category', e.target.value || null)}><option value="">未分类</option>{(config.risk_categories || []).map(r => <option key={r.key} value={r.key}>{r.label}</option>)}</select></label>
        </div>
        <p>适用条件均满足时检查；任一为否则跳过，未知则待补齐。</p>
        {(c.applies_when || []).map((p, n) => <div key={n} className="decision-form-grid">
          <PredicateFields item={p} prefix={`规则${i + 1}适用${n + 1}`} metricOptions={metricOptions} update={(field, value) => update('conditions', i, 'applies_when', c.applies_when.map((old, j) => j === n ? { ...old, [field]: value } : old))} />
          <button type="button" className="button button-secondary" onClick={() => update('conditions', i, 'applies_when', c.applies_when.filter((_, j) => j !== n))}>移除适用条件</button>
        </div>)}
        <div className="collab-actions"><button type="button" className="button button-secondary" onClick={() => update('conditions', i, 'applies_when', [...(c.applies_when || []), { field: 'expected_occupancy', op: 'gt', value: 0 }])}>添加适用条件</button>
          <button type="button" className="button button-secondary" onClick={() => setConfig(old => ({ ...old, conditions: old.conditions.filter((_, j) => j !== i) }))}>移除规则</button></div>
      </details>)}
      {!!config.risk_categories?.length && <details><summary>12类风险核验目录</summary>{config.risk_categories.map(r => <p key={r.key}>{r.label} · {r.verification} · {r.action}</p>)}</details>}
      {Object.entries(config.auxiliary_models || {}).map(([key, model]) => <details className="decision-config-item" key={key}><summary>{model.label} · {model.criteria.length}项 · 满分{model.max_total}</summary><p>{model.source}</p>
        {model.criteria.map((c, i) => <details key={c.key}><summary>{c.label} · 权重{c.weight}</summary><Normalization item={c} prefix={`${model.label}${i + 1}`} update={(field, value) => updateAux(key, i, field, value)} /></details>)}</details>)}
      <label className="decision-checkbox"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} />已人工核验阈值、维度与回测依据</label>
      <div className="collab-actions"><button className="button button-primary" disabled={busy}>保存新规则版本</button></div>
    </form>
  </details>
}
