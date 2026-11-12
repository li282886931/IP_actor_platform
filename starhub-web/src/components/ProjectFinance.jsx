import { useEffect, useRef, useState } from 'react'
import { calculateShow } from '../api'

const groups = [
  { title: '场馆与票房', fields: [
    ['venue_capacity', '场馆容量', '人'], ['expected_attendance', '预计人数', '人'],
    ['avg_ticket_price', '平均票价', '元'], ['available_funds', '可用资金', '元'],
  ] },
  { title: '成本明细', fields: [
    ['artist_fee', '艺人费用', '元'], ['venue_cost', '场馆费用', '元'],
    ['marketing_cost', '宣发费用', '元'], ['production_cost', '制作费用', '元'],
    ['security_cost', '安保费用', '元'], ['travel_cost', '交通费用', '元'],
    ['accommodation_cost', '住宿费用', '元'], ['insurance_cost', '保险费用', '元'],
    ['approval_cost', '审批费用', '元'], ['contingency_cost', '预备费用', '元'],
  ] },
  { title: '扣率与其他收入', fields: [
    ['tax_fee_rate', '税费率', '%'], ['ticketing_fee_rate', '票务服务费率', '%'],
    ['sponsorship_income', '赞助收入', '元'], ['merchandise_income', '周边收入', '元'],
    ['target_profit', '目标利润', '元'],
  ] },
  { title: '情景上座率假设', fields: [
    ['conservative_occupancy_rate', '保守上座率', '%'],
    ['neutral_occupancy_rate', '中性上座率', '%'],
    ['optimistic_occupancy_rate', '乐观上座率', '%'],
  ] },
]
const fields = groups.flatMap((group) => group.fields)
const labels = Object.fromEntries(fields.map(([key, label]) => [key, label]))
const defaults = { conservative_occupancy_rate: 60, neutral_occupancy_rate: 80, optimistic_occupancy_rate: 95 }
const money = (value) => value == null ? '待补齐' : `¥${Number(value).toLocaleString('zh-CN')}`
const percent = (value) => value == null ? '待测算' : `${(value * 100).toFixed(2)}%`

export default function ProjectFinance({ project, onSaved }) {
  const [form, setForm] = useState({})
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const request = useRef(0)
  const version = project.current_version
  const finance = version?.finance_result

  useEffect(() => {
    const saved = version?.input_snapshot?.show_calculation || {}
    setForm(Object.fromEntries(fields.map(([key]) => {
      const value = saved[key] ?? project[key] ?? defaults[key] ?? ''
      return [key, key.endsWith('fee_rate') && value !== '' ? Number((value * 100).toFixed(6)) : value]
    })))
    setNotice('')
    setError('')
    setBusy(false)
    request.current += 1
    return () => { request.current += 1 }
  }, [project.id, version?.id])

  const save = async (event) => {
    event.preventDefault()
    if (busy) return
    const current = ++request.current
    setBusy(true)
    setError('')
    setNotice('')
    const payload = Object.fromEntries(fields.map(([key]) => [
      key, form[key] === '' || form[key] == null ? null
        : Number(form[key]) / (key.endsWith('fee_rate') ? 100 : 1),
    ]))
    try {
      const response = await calculateShow({ project_id: project.id, ...payload })
      if (current !== request.current) return
      const result = response.data.data
      if (result.status === 'pending_input') {
        setNotice(`待补齐：${result.missing_fields.map((key) => labels[key] || key).join('、')}`)
      } else {
        setNotice('测算已保存，结果按本次真实参数计算。')
      }
      await onSaved(result)
    } catch (failure) {
      if (current !== request.current) return
      setError(failure.response?.status === 422
        ? '参数不符合要求：请检查人数与容量、非负金额、扣率合计小于 100%，以及情景上座率顺序。'
        : '测算或刷新失败，请检查服务后重试；已填写内容保留。')
    } finally {
      if (current === request.current) setBusy(false)
    }
  }

  const occupancy = Number(form.venue_capacity) > 0 && form.expected_attendance !== ''
    ? Math.min(100, Math.max(0, Math.round(Number(form.expected_attendance) / Number(form.venue_capacity) * 100)))
    : 0

  return (
    <section className="panel project-finance" id="project-finance">
      <div className="panel-heading">
        <div><h3>演出决策测算</h3><p>金额单位为元，扣率按毛票房分别扣除；无费用请明确填 0。</p></div>
        <span className="section-count">{version?.version_no ? `V${version.version_no}` : '尚无测算版本'}</span>
      </div>
      {finance?.status === 'pending_input' && !notice && (
        <p className="inline-message" role="status">待补齐：{(finance.missing_fields || []).map((key) => labels[key] || key).join('、')}</p>
      )}
      {finance?.status === 'calculated' && (
        <>
          <dl className="finance-results" aria-label="已保存测算结果">
            {[
              ['预计上座率', percent(finance.expected_occupancy_rate)],
              ['毛票房', money(finance.gross_ticket_revenue)],
              ['税费扣除', money(finance.tax_amount)],
              ['服务费扣除', money(finance.ticketing_fee_amount)],
              ['净票房', money(finance.net_ticket_revenue)],
              ['预计净利润', money(finance.net_profit)],
              ['项目成本回报率', percent(finance.roi)],
              ['资金缺口', money(finance.funding_gap)],
            ].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
          </dl>
          {finance.breakeven_capacity_feasible === false && (
            <p className="inline-message error">保本人数超过场馆容量，请调整成本、票价或收入方案。</p>
          )}
          {finance.funding_gap == null && <p>资金余额待补齐，暂不能计算资金缺口。</p>}
          <p className="finance-note">回报率 = 项目净利润 / 总成本，不代表资方合同收益率。资金安全需另行核验。</p>
        </>
      )}
      <form onSubmit={save}>
        <fieldset disabled={busy} className="finance-fields">
          {groups.map((group) => (
            <fieldset className="finance-group" key={group.title}>
              <legend>{group.title}</legend>
              <div className="finance-input-grid">
                {group.fields.map(([key, label, unit]) => (
                  <label className="field" key={key}>
                    <span>{label} / {unit}</span>
                    <input type="number" min={['venue_capacity', 'avg_ticket_price'].includes(key) ? 1 : 0}
                      max={unit === '%' ? (key.endsWith('fee_rate') ? 99.9999 : 100) : undefined}
                      step={key.endsWith('fee_rate') ? 'any' : 1}
                      value={form[key] ?? ''} placeholder="待填写"
                      onChange={(event) => setForm((value) => ({ ...value, [key]: event.target.value }))} />
                  </label>
                ))}
              </div>
              {group.title === '场馆与票房' && (
                <label className="finance-slider">
                  <span>上座率调节 / % <b>{occupancy}%</b></span>
                  <input type="range" min="0" max="100" value={occupancy}
                    aria-label="上座率调节 / %"
                    disabled={!Number(form.venue_capacity)}
                    onChange={(event) => setForm((value) => ({
                      ...value, expected_attendance: Math.round(Number(value.venue_capacity) * Number(event.target.value) / 100),
                    }))} />
                </label>
              )}
            </fieldset>
          ))}
        </fieldset>
        <div className="finance-actions">
          <small>滑动或修改参数后保存，以后端测算结果为准。情景上座率是可调整假设。</small>
          <button className="button button-primary" type="submit" disabled={busy}>{busy ? '计算中…' : '保存并计算'}</button>
        </div>
      </form>
      {notice && <p className="inline-message" role="status">{notice}</p>}
      {error && <p className="inline-message error" role="alert">{error}</p>}
    </section>
  )
}
