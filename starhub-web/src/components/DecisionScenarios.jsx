import { useEffect, useRef, useState } from 'react'
import { calculateDecisionScenarios } from '../decisionApi'
import { Fields, parseFields, percent } from '../pages/decisionFields'

const fields = [
  ['capacity', '单场容量（人）'], ['base_price', '基准票价（元）'], ['base_occupancy', '基准上座率（0–1）'],
  ['net_ticket_rate', '票房实收率（0–1）'], ['price_elasticity', '有来源的价格弹性（−10–0）'],
  ['show_count', '演出场数'], ['shared_cost', '多场共用成本（元）'], ['cost_per_show', '单场成本（元）'],
  ['sponsorship_per_show', '单场赞助（元）'], ['subsidy_per_show', '单场补贴（元）'],
  ['cancellation_nonrefundable', '取消时不可退支出（元）'], ['insurance_recovery', '可确认保险回款（元）'],
  ['cost_actual', '当前实际成本（元）'], ['cost_budget', '核定预算（元）'],
].map(([key, label]) => ({ key, label, type: 'number', min: key === 'price_elasticity' ? -10 : 0 }))
fields.push({ key: 'source', label: '弹性与上座率来源', type: 'textarea' })

export default function DecisionScenarios({ projectId }) {
  const [values, setValues] = useState({}), [price, setPrice] = useState(''), [result, setResult] = useState(null)
  const [error, setError] = useState(''), [busy, setBusy] = useState(false), sequence = useRef(0)
  useEffect(() => { sequence.current++; setResult(null); setValues({}); setPrice(''); setError(''); setBusy(false) }, [projectId])
  useEffect(() => () => { sequence.current++ }, [])
  async function calculate(nextPrice = price) {
    const id = ++sequence.current
    setBusy(true); setError('')
    try {
      const response = await calculateDecisionScenarios(projectId, { ...parseFields(fields, values), prices: [Number(nextPrice)] })
      if (id === sequence.current) setResult(response.data.data)
    } catch (e) { if (id === sequence.current) setError(e.response?.data?.detail || '测算失败，请检查参数') }
    finally { if (id === sequence.current) setBusy(false) }
  }
  const base = Number(values.base_price)
  return <section className="panel"><h3>票价弹性、多场经济与取消损失</h3>
    <p className="role-muted">填入真实容量、成本和有来源的弹性假设。调整票价后，结果由后端重新计算。</p>
    <form onSubmit={e => { e.preventDefault(); calculate() }}><Fields fields={fields} values={values} setValues={update => { setValues(update); setResult(null) }} />
      <label>测算票价（元）<input aria-label="测算票价（元）" type="number" min="0.01" step="any" required value={price} onChange={e => { setPrice(e.target.value); setResult(null) }} /></label>
      {base > 0 && <label>拖动票价<input aria-label="拖动票价" type="range" min={base * .5} max={base * 1.5} step={.01} value={price || base}
        onChange={e => { setPrice(e.target.value); setResult(null) }} onPointerUp={e => calculate(e.currentTarget.value)}
        onKeyUp={e => calculate(e.currentTarget.value)} /></label>}
      <button className="button button-primary" disabled={busy || !projectId}>{busy ? '计算中…' : '计算敏感性'}</button>
    </form>
    {error && <p role="alert">{typeof error === 'string' ? error : '参数格式不正确'}</p>}
    {result && <div aria-live="polite">
      {result.missing_fields.length > 0 && <p>待补齐：{result.missing_fields.map(k => fields.find(f => f.key === k)?.label || k).join('、')}</p>}
      {result.scenarios.map(s => <p key={s.price}>票价 {s.price} 元 · 上座率 {percent(s.occupancy)} · 综合保本 {percent(s.comprehensive_breakeven)} · 利润 {s.profit.toLocaleString('zh-CN')} 元</p>)}
      <p>取消损失：{result.cancellation_loss == null ? '待补齐' : `${result.cancellation_loss} 元`} · 成本偏差 {percent(result.cost_overrun_ratio)}</p>
      <details><summary>公式与测算边界</summary><p>{result.formula}</p><p>{result.notice}</p></details>
    </div>}
  </section>
}
