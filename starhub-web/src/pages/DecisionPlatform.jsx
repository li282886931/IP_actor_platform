import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getDecisionWorkspace, decisionMutation } from '../decisionApi'
import DecisionRules from '../components/DecisionRules'
import OperatingRecords from '../components/OperatingRecords'
import DecisionScenarios from '../components/DecisionScenarios'
import ScoreBreakdown from '../components/ScoreBreakdown'
import { budgetFields, Fields, parseFields, percent, stageLabels, statusLabels, Values, vetoLabels } from './decisionFields'
import './decisionPlatform.css'

const headings = { decision: '决策风控', review: '经营复盘与增量价值', valuation: '品牌权益与效果', returns: '回报与止损', assets: '城市资产与文旅成效', community: '艺人动态与成长', plan: '年度观演计划', calendar: '全年日历与风险监测' }
function useDecision() {
  const [data, setData] = useState(null), [error, setError] = useState(''), [busy, setBusy] = useState(false)
  const mounted = useRef(false), sequence = useRef(0), lock = useRef(false), request = useRef(null)
  async function reload() {
    const id = ++sequence.current
    try { const result = await getDecisionWorkspace(); if (mounted.current && sequence.current === id) { setData(result.data.data); setError('') } }
    catch { if (mounted.current && sequence.current === id) setError('工作台加载失败，请检查登录状态后重试') }
  }
  useEffect(() => { mounted.current = true; reload(); return () => { mounted.current = false; sequence.current++ } }, [])
  async function mutate(path, body) {
    if (lock.current) return false
    lock.current = true; setBusy(true); setError('')
    const signature = JSON.stringify([path, body])
    if (request.current?.signature !== signature) request.current = { signature, key: crypto.randomUUID() }
    try {
      await decisionMutation(path, body, request.current.key)
      request.current = null; await reload(); return true
    } catch (e) {
      if (mounted.current) setError(typeof e.response?.data?.detail === 'string' ? e.response.data.detail : e.message || '保存失败，请重试')
      if (e.response) request.current = null
      return false
    } finally { lock.current = false; if (mounted.current) setBusy(false) }
  }
  return { data, error, busy, reload, mutate, setError }
}
function Report({ report }) {
  if (!report) return <p className="role-muted">暂无决策报告；先选择规则版本并补齐真实参数。</p>
  const result = report.result
  return <div className="decision-report"><div className="panel-heading"><h3>决策报告 #{report.id}</h3><span>{statusLabels[result.status]} · {statusLabels[report.verification_status]} · 规则 #{report.rule_version_id}</span></div>
    <dl className="decision-report-summary"><div><dt>纯票房保本</dt><dd>{percent(result.finance.pure_breakeven)}</dd></div><div><dt>综合保本</dt><dd>{percent(result.finance.comprehensive_breakeven)}</dd></div><div><dt>风险评分</dt><dd>{result.score.value == null ? result.score.status === 'pending_configuration' ? '评分卡待配置' : '评分参数待补齐' : `${result.score.value} / 120`}</dd></div></dl>
    <Values values={{ predicted_profit: result.finance.predicted_profit }} />
    {(result.vetoes || []).map(key => <p className="decision-alert" key={key}>{vetoLabels[key] || key}</p>)}
    {(result.plan_triggers || []).map(key => <p className="decision-alert warning" key={key}>{vetoLabels[key] || key}</p>)}
    {(result.warnings || []).map(w => <p key={w.key}>{w.title} · 当前 {percent(w.value)} / 阈值 {percent(w.threshold)}</p>)}
    {result.configuration_gaps?.length > 0 && <p className="role-disclosure">评分维度或32条规则配置不完整，不能作完整风控结论。</p>}
    {result.missing_fields?.length > 0 && <p className="role-disclosure">缺少参数：{result.missing_fields.map(k => budgetFields.find(f => f.key === k)?.label || k).join('、')}</p>}
    <details><summary>规则命中与评分依据</summary>
      {(result.rule_checks || result.rule_hits)?.map(h => <p key={h.key}>{h.key} · {h.message} · {({ hit: '命中', clear: '未命中', skipped: '不适用', unresolved: '待补齐' })[h.status] || '命中'} · 实际值 {h.observed_value == null ? '待补齐' : String(h.observed_value)} / 阈值 {h.resolved_threshold ?? h.value}
        {h.missing_fields?.length > 0 && ` · 缺少 ${h.missing_fields.join('、')}`}{h.source && ` · ${h.source}`}</p>)}
      {result.scoring_mode === 'auto' ? <ScoreBreakdown result={result.score} /> : result.score.dimensions?.map(d => <p key={d.key}>{d.label} · {d.score}/{d.max_score} · 加权 {d.contribution.toFixed(2)} 分</p>)}
      <Values values={report.inputs} />
    </details>
  </div>
}
function SocialStream({ data, mutate, busy }) {
  const [comments, setComments] = useState({})
  const commentKeys = useRef({})
  return <section className="panel"><h3>艺人动态与作品</h3>{!data.stream.length && <p className="role-muted">暂无已发布动态。</p>}
    {data.stream.map(post => <article className="decision-record" key={post.id}><div className="panel-heading"><strong>{post.artist_name} · {post.title}</strong><span>{statusLabels[post.payload.post_type]}</span></div>
      <p className="decision-post-content">{post.payload.content}</p>{post.payload.scheduled_at && <p>活动日期：{post.payload.scheduled_at}</p>}
      {post.payload.link?.startsWith('https://') && <a href={post.payload.link} target="_blank" rel="noreferrer">查看官方作品或活动</a>}
      {post.comments?.map(c => <p key={c.id} className="decision-comment">{c.payload.content}</p>)}
      <form className="decision-comment-form" onSubmit={async e => { e.preventDefault(); commentKeys.current[post.id] ||= crypto.randomUUID(); if (await mutate('records', {
        kind: 'comment', title: '作品评论', record_key: commentKeys.current[post.id], payload: { post_id: post.id, content: comments[post.id] },
      })) { setComments(old => ({ ...old, [post.id]: '' })); delete commentKeys.current[post.id] } }}>
        <input required aria-label={`评论${post.title}`} maxLength={2000} placeholder="写下你的评论" value={comments[post.id] || ''} onChange={e => setComments(old => ({ ...old, [post.id]: e.target.value }))} />
        <button className="button button-secondary" disabled={busy}>发布评论</button>
      </form>
    </article>)}
  </section>
}
export default function DecisionPlatform({ role, mode = 'decision' }) {
  const controller = useDecision(), { data, error, busy, reload, mutate, setError } = controller
  const [params] = useSearchParams()
  const [selected, setSelected] = useState(params.get('project') || ''), [values, setValues] = useState({})
  const [ruleId, setRuleId] = useState(''), [config, setConfig] = useState(null), [scores, setScores] = useState({})
  const [evidence, setEvidence] = useState(''), [note, setNote] = useState(''), [stopPlan, setStopPlan] = useState('')
  const [actuals, setActuals] = useState({}), [verified, setVerified] = useState(false)
  const [city, setCity] = useState({})
  useEffect(() => { if (data) { if (!config) setConfig(structuredClone(data.rules?.[0]?.config || data.default_config)); if (!selected && data.projects.length) setSelected(String(data.projects[0].id)); if (!ruleId && data.rules?.length) setRuleId(String(data.rules[0].id)) } }, [data, config, selected, ruleId])
  const project = data?.projects.find(p => p.id === Number(selected)), report = project?.reports?.[0]
  const activeRule = data?.rules?.find(r => r.id === Number(ruleId))
  const autoAvailable = Boolean(activeRule?.config.dimensions?.length && activeRule.config.dimensions.every(d => d.method && d.method !== 'manual'))
  const scoreMode = values.scoring_mode || (autoAvailable ? 'auto' : 'manual')
  useEffect(() => {
    const inputs = report?.inputs || {}
    setValues(Object.fromEntries(Object.entries(inputs).map(([k, v]) => [k,
      Array.isArray(v) ? v.join(',') : typeof v === 'boolean' ? String(v) : v ?? ''])))
    setScores(inputs.scores || {})
    const actual = project?.actuals || {}
    setActuals({ ...actual, evidence_ids: '' })
    setVerified(false)
    setEvidence(''); setNote(''); setStopPlan('')
  }, [project?.id, report?.id, project?.actuals?.actual_revenue, project?.actuals?.actual_cost])
  const nextStage = project ? Object.keys(stageLabels)[Object.keys(stageLabels).indexOf(project.stage) + 1] : null
  async function act(fn) { try { await fn() } catch (e) { setError(e.message) } }
  if (!data) return <div className="state-panel" role="status">{error ? <><p>{error}</p><button className="button button-secondary" onClick={reload}>重试</button></> : '正在加载决策工作台…'}</div>
  const idList = () => parseFields([{ key: 'evidence_ids', type: 'ids' }], { evidence_ids: evidence }).evidence_ids || []
  return <div className="page-stack decision-platform">
    <div className="page-lead"><div><h2>{headings[mode]}</h2><p>规则可追溯，参数有来源，经营结果由人工核验。</p></div>{role === 'B' && <Link to="/operations/projects" className="button button-secondary">项目运营</Link>}
      {role === 'C' && <Link to="/collaboration" className="button button-secondary">关注艺人与收藏演出</Link>}</div>
    {error && <div className="inline-message error" role="alert">{error} <button className="button button-secondary" onClick={reload}>刷新</button></div>}
    {!['community', 'plan'].includes(mode) && <div className="decision-toolbar"><label>当前授权项目<select aria-label="当前授权项目" value={selected} onChange={e => { setSelected(e.target.value); setValues({}); setScores({}); setActuals({}); setVerified(false) }}>{data.projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
      {!data.projects.length && <span>暂无已授权项目</span>}{project && <span>{project.city} · {project.schedule || '日期待确认'}</span>}</div>}
    {mode === 'decision' && <>
      {project && <section className="panel"><ol className="decision-stages">{Object.entries(stageLabels).map(([key, text]) => <li key={key} aria-current={key === project.stage ? 'step' : undefined}>{text}</li>)}</ol><Report report={report} /></section>}
      <section className="panel"><h3>生成决策报告</h3><form onSubmit={e => { e.preventDefault(); act(() => mutate(`report/${selected}`, { rule_version_id: Number(ruleId), inputs: { ...parseFields(budgetFields, values),
        scoring_mode: scoreMode, scores: scoreMode === 'auto' ? {} : Object.fromEntries(Object.entries(scores).filter(([, v]) => v !== '').map(([k, v]) => [k, Number(v)])) } })) }}>
        <div className="decision-form-grid"><label>使用规则版本<select required aria-label="使用规则版本" value={ruleId} onChange={e => { setRuleId(e.target.value); setScores({}); setValues(old => ({ ...old, scoring_mode: '' })) }}><option value="">先保存规则版本</option>{(data.rules || []).map(r => <option key={r.id} value={r.id}>v{r.version_no} · {r.name} · {statusLabels[r.status]}</option>)}</select></label>
          <label>评分方式<select aria-label="评分方式" value={scoreMode} onChange={e => { setValues(old => ({ ...old, scoring_mode: e.target.value })); setScores({}) }}><option value="auto" disabled={!autoAvailable}>按真实指标自动评分</option><option value="manual">人工逐维评分</option></select></label></div>
        <Fields fields={budgetFields.filter(f => !f.advanced)} values={values} setValues={setValues} />
        <details><summary>完整规则参数：需求、报价、资金与合规</summary><Fields fields={budgetFields.filter(f => f.advanced)} values={values} setValues={setValues} /></details>
        {scoreMode === 'auto' ? <p className="role-muted">12维由绑定指标归一计算，缺项不出完整总分；请填写真实来源和项目证明，分数不覆盖否决规则。</p> : <div className="decision-form-grid">{(activeRule?.config.dimensions || []).map(d => <label key={d.key}>{d.label}（0–{d.max_score}）<input type="number" min="0" max={d.max_score} step="any" aria-label={`评分${d.label}`} value={scores[d.key] ?? ''} onChange={e => setScores(old => ({ ...old, [d.key]: e.target.value }))} /></label>)}</div>}
        <div className="collab-actions"><button className="button button-primary" disabled={busy || !selected || !ruleId}>生成并保存报告</button></div></form></section>
      {config && <DecisionRules config={config} setConfig={setConfig} catalog={data.catalog} rules={data.rules || []} mutate={mutate} busy={busy} />}
      {project && <section className="panel"><h3>核验与阶段推进</h3><div className="decision-form-grid"><label>已核验材料编号<input aria-label="阶段材料编号" value={evidence} onChange={e => setEvidence(e.target.value)} /></label>
        <label>核验说明<input aria-label="报告核验说明" value={note} onChange={e => setNote(e.target.value)} /></label><label>止损预案<textarea aria-label="止损预案" value={stopPlan} onChange={e => setStopPlan(e.target.value)} /></label></div>
        <div className="collab-actions"><button className="button button-secondary" disabled={busy || !report || !evidence || !note} onClick={() => act(() => mutate(`reports/${report.id}/verify`, { evidence_ids: idList(), note }))}>人工核验报告</button>
          <button className="button button-primary" disabled={busy || !nextStage || report?.verification_status !== 'verified' || Boolean(report?.result.vetoes.length) || !evidence} onClick={() => act(() => mutate(`projects/${selected}/stage`, { stage: nextStage, report_id: report.id, evidence_ids: idList(), stop_loss_plan: stopPlan }))}>推进下一阶段</button></div>
        <p className="role-muted">当前：{stageLabels[project.stage]}。材料、规则和报告均核验后才可推进；每次操作写入审计。</p>
        {project.evidences?.map(e => <p key={e.id}>材料 #{e.id} · {e.name} · {statusLabels[e.status] || '待核验'}</p>)}</section>}
    </>}
    {['decision', 'returns'].includes(mode) && project && <DecisionScenarios projectId={project.id} />}
    {mode === 'review' && <>
      {project && <section className="panel"><h3>实际结算与偏差归因</h3><Values values={{ predicted_profit: report?.result.finance.predicted_profit }} />
        {project.actuals && <p>实际利润：{project.actuals.actual_profit == null ? '待补齐' : `${project.actuals.actual_profit.toLocaleString('zh-CN')} 元`} · {statusLabels[project.actuals.status]}</p>}
        <form onSubmit={e => { e.preventDefault(); act(() => mutate(`actuals/${selected}`, { ...parseFields([
          { key: 'actual_attendance', type: 'number' }, { key: 'actual_revenue', type: 'number' }, { key: 'actual_cost', type: 'number' }, { key: 'notes', type: 'text' }, { key: 'evidence_ids', type: 'ids' },
        ], actuals), verified })) }}>
          <Fields fields={[{ key: 'actual_attendance', label: '实际观众（人）', type: 'number' }, { key: 'actual_revenue', label: '实际净收入（元）', type: 'number' },
            { key: 'actual_cost', label: '实际总成本（元）', type: 'number' }, { key: 'notes', label: '实际结算来源与归因', type: 'textarea' }, { key: 'evidence_ids', label: '结算材料编号（逗号分隔）', type: 'ids' }]} values={actuals} setValues={setActuals} />
          <label className="decision-checkbox"><input type="checkbox" checked={verified} onChange={e => setVerified(e.target.checked)} />已核验实际结算凭证</label><div className="collab-actions"><button className="button button-primary" disabled={busy}>保存实际结算</button></div></form>
        <label>校准归因<textarea aria-label="校准归因" value={note} onChange={e => setNote(e.target.value)} /></label>
        <button className="button button-secondary" disabled={busy || !report || !config || !note} onClick={() => mutate(`calibrate/${report.id}`, { attribution: note, config })}>生成待核验校准版本</button>
        <p className="role-muted">校准生成新版本，需重新核验；不修改历史报告。</p></section>}
      {config && <DecisionRules config={config} setConfig={setConfig} catalog={data.catalog} rules={data.rules || []} mutate={mutate} busy={busy} />}
    </>}
    {mode === 'community' && <label>成长凭证关联项目<select aria-label="成长凭证关联项目" value={selected} onChange={e => setSelected(e.target.value)}>
      <option value="">选择已授权项目</option>{data.projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>}
    {['review', 'valuation', 'returns', 'assets', 'community', 'plan'].includes(mode) && <OperatingRecords role={role} data={data} selectedProject={selected} mutate={mutate} busy={busy} onError={setError} />}
    {mode === 'returns' && <section className="panel"><h3>项目风险与回本口径</h3><Report report={report} /><p>现金流日期由真实约定输入。IRR不唯一时不展示单一收益率；监管凭证用于核验。</p></section>}
    {mode === 'assets' && <section className="panel"><h3>城市市场资料</h3><form onSubmit={e => { e.preventDefault(); act(() => mutate('cities', { ...parseFields([
      { key: 'name', type: 'text' }, { key: 'population', type: 'number' }, { key: 'annual_shows', type: 'number' }, { key: 'market_revenue', type: 'number' }, { key: 'genres', type: 'list' }, { key: 'source', type: 'text' },
    ], city), ...(city.revision ? { revision: city.revision } : {}) })) }}><Fields fields={[{ key: 'name', label: '城市名称', type: 'text' }, { key: 'population', label: '城市人口（人）', type: 'number' }, { key: 'annual_shows', label: '年度演出（场）', type: 'number' },
      { key: 'market_revenue', label: '市场收入（元）', type: 'number' }, { key: 'genres', label: '适合演出品类', type: 'list' }, { key: 'source', label: '市场资料来源', type: 'text' }]} values={city} setValues={setCity} /><div className="collab-actions"><button disabled={busy} className="button button-primary">保存城市资料</button></div></form>
      {data.cities.map(c => <div className="workspace-compact-row" key={c.id}><p>{c.name} · 年度演出 {c.profile.annual_shows ?? '待补齐'} 场 · 来源 {c.profile.source}</p>
        <button className="button button-secondary" onClick={() => setCity({ name: c.name, ...c.profile, genres: c.profile.genres.join(','), revision: c.revision })}>修改资料</button></div>)}
      {data.asset_matches?.map(m => <p key={m.record_id}>{m.title} · 同城授权项目：{m.projects.map(p => p.name).join('、') || '暂无'}。{m.basis}</p>)}</section>}
    {['community', 'plan'].includes(mode) && <SocialStream data={data} mutate={mutate} busy={busy} />}
    {mode === 'community' && <section className="panel"><h3>已核验成长与城市趋势</h3>
      {!data.growth?.length && <p className="role-muted">录入并核验成长数据后展示，缺少收入分项时不计算变现总额。</p>}
      {data.growth?.map(g => <article key={g.city}><p>{g.city} · {g.date} · 粉丝 {g.fan_count ?? '待补齐'} 人 · 增长 {g.fan_growth ?? '待补齐'} 人 · 变现收入 {g.monetization == null ? '待补齐' : `${g.monetization} 元`}</p>
        <details><summary>城市历史趋势</summary>{g.points.map(p => <p key={p.date}>{p.date} · 粉丝 {p.fan_count ?? '待补齐'} 人 · 热度 {p.heat ?? '待补齐'}</p>)}</details></article>)}</section>}
    {mode === 'plan' && <section className="panel"><h3>近期观演提醒与公开足迹</h3>
      {data.reminders?.map((r, i) => <p key={`${r.show_id}-${i}`}>{r.title} · {r.date} · 距演出 {r.days_remaining} 天</p>)}
      {!data.reminders?.length && <p className="role-muted">年度计划暂无30天内演出。</p>}
      {data.checkins?.map(c => <p key={c.id}>{c.title} · {c.payload.attended_at} · {c.payload.content}</p>)}</section>}
    {mode === 'plan' && <section className="panel"><h3>真实演出目录</h3>{data.shows.map(s => <div className="workspace-compact-row" key={s.id}><div><strong>#{s.id} · {s.title}</strong><small>{s.city} · {s.date || '日期待确认'}</small></div><Link to={`/show/${s.id}`} className="button button-secondary">官方购票路径</Link></div>)}</section>}
    {mode === 'calendar' && <>
      <section className="panel"><h3>项目日历与批文倒排</h3><div className="decision-calendar">{data.calendar.map(c => <article key={c.project_id}><time>{c.date}</time><strong>{c.title}</strong><span>{stageLabels[c.stage]}</span><small>报批截止 {c.application_due} · 批文最晚 {c.permit_due}</small></article>)}</div>{!data.calendar.length && <p className="role-muted">没有已确认日期的授权项目。</p>}</section>
      <section className="panel"><h3>风险监测与来源状态</h3>{Object.values(data.source_status || {}).map(text => <p key={text}>{text}</p>)}
        {data.projects.flatMap(p => (p.risks || []).map(r => <div className="workspace-compact-row" key={r.id}><div><strong>{p.name} · {r.title}</strong><small>{r.mitigation || '预案待补齐'}</small></div><span>{statusLabels[r.status] || '待处理'}</span></div>))}</section>
    </>}
  </div>
}
