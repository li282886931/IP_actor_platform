import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import {
  agentChat,
  createAssumption,
  createEvidence,
  createExternalDataJob,
  createFact,
  createGate,
  createRisk,
  generateFeasibilityReport,
  getProject,
  listAssumptions,
  listEvidences,
  listExternalDataJobs,
  listFacts,
  listGates,
  listProjectVersions,
  listRisks,
  listTasks,
  searchCases,
  shareReport,
  submitTask,
  verifyFact,
} from '../api'
import { zhaoYazhiMarketDossier } from '../data/marketDossier'

const emptyFactForm = { title: '', content: '', source: '' }
const emptyEvidenceForm = { name: '', file_url: '', source: '', evidence_type: 'document' }
const emptyAssumptionForm = { title: '', content: '', confidence: 70 }
const emptyGateForm = { name: '', required_evidence: '', owner_group: 'B' }
const emptyRiskForm = { title: '', mitigation: '', level: 'medium' }
const emptyMarketFactForm = { title: '', content: '', source: '' }

function formatNumber(value) {
  return new Intl.NumberFormat('zh-CN').format(value || 0)
}

function statusLabel(value) {
  const labels = {
    active: '有效',
    calculated: '已测算',
    draft: '草稿',
    high: '高',
    low: '低',
    medium: '中',
    open: '开放',
    pending: '待处理',
    rejected: '已驳回',
    submitted: '已提交',
    verified: '已核验',
  }
  return labels[value] || value || '未设置'
}

function DataList({ emptyText, items, renderItem }) {
  if (!items.length) {
    return <div className="state-panel compact">{emptyText}</div>
  }
  return <div className="summary-list">{items.map(renderItem)}</div>
}

export default function ProjectDetail() {
  const { id } = useParams()
  const projectId = Number(id)
  const [project, setProject] = useState(null)
  const [versions, setVersions] = useState([])
  const [facts, setFacts] = useState([])
  const [evidences, setEvidences] = useState([])
  const [assumptions, setAssumptions] = useState([])
  const [gates, setGates] = useState([])
  const [risks, setRisks] = useState([])
  const [tasks, setTasks] = useState([])
  const [externalJobs, setExternalJobs] = useState([])
  const [cases, setCases] = useState([])
  const [status, setStatus] = useState('loading')
  const [message, setMessage] = useState('')
  const [shareUrl, setShareUrl] = useState('')
  const [feasibilityReport, setFeasibilityReport] = useState(null)
  const [agentAnswer, setAgentAnswer] = useState('')
  const [taskResultById, setTaskResultById] = useState({})
  const [agentQuestion, setAgentQuestion] = useState('')
  const [caseKeyword, setCaseKeyword] = useState('')
  const [factForm, setFactForm] = useState(emptyFactForm)
  const [evidenceForm, setEvidenceForm] = useState(emptyEvidenceForm)
  const [assumptionForm, setAssumptionForm] = useState(emptyAssumptionForm)
  const [gateForm, setGateForm] = useState(emptyGateForm)
  const [riskForm, setRiskForm] = useState(emptyRiskForm)
  const [marketFactForm, setMarketFactForm] = useState(emptyMarketFactForm)

  useEffect(() => {
    let active = true
    setStatus('loading')
    setMessage('')

    Promise.all([
      getProject(projectId),
      listProjectVersions(projectId),
      listFacts(projectId),
      listEvidences(projectId),
      listAssumptions(projectId),
      listGates(projectId),
      listRisks(projectId),
      listTasks(projectId),
      listExternalDataJobs(projectId),
    ])
      .then(([projectResponse, versionsResponse, factsResponse, evidencesResponse, assumptionsResponse, gatesResponse, risksResponse, tasksResponse, externalJobsResponse]) => {
        if (!active) return
        setProject(projectResponse.data.data)
        setVersions(versionsResponse.data.data || [])
        setFacts(factsResponse.data.data || [])
        setEvidences(evidencesResponse.data.data || [])
        setAssumptions(assumptionsResponse.data.data || [])
        setGates(gatesResponse.data.data || [])
        setRisks(risksResponse.data.data || [])
        setTasks(tasksResponse.data.data || [])
        setExternalJobs(externalJobsResponse.data.data || [])
        setStatus('success')
      })
      .catch(() => {
        if (active) setStatus('error')
      })

    return () => {
      active = false
    }
  }, [projectId])

  const finance = project?.current_version?.finance_result
  const neutral = finance?.scenarios?.neutral
  const metrics = useMemo(() => [
    { label: '当前版本', value: project?.current_version?.version_no ? `V${project.current_version.version_no}` : '-', delta: statusLabel(project?.current_version?.status) },
    { label: '中性利润', value: neutral ? `¥${formatNumber(neutral.profit)}` : '-', delta: neutral ? `收入 ¥${formatNumber(neutral.revenue)}` : '等待测算' },
    { label: '保本人数', value: finance?.breakeven_attendance ? formatNumber(finance.breakeven_attendance) : '-', delta: finance?.total_cost ? `总成本 ¥${formatNumber(finance.total_cost)}` : '成本待补齐' },
    { label: '开放风险', value: String(risks.filter((risk) => risk.status === 'open').length), delta: `${gates.length} 个关卡待跟进`, tone: risks.some((risk) => risk.level === 'high') ? 'danger' : undefined },
  ], [finance, gates.length, neutral, project, risks])

  const setField = (setter, field, value) => setter((current) => ({ ...current, [field]: value }))

  const handleCreateFact = async (event) => {
    event.preventDefault()
    if (!factForm.title.trim()) return
    const payload = {
      project_id: projectId,
      title: factForm.title.trim(),
      content: factForm.content.trim(),
      source: factForm.source.trim(),
    }
    const response = await createFact(payload)
    setFacts((current) => [response.data.data, ...current])
    setFactForm(emptyFactForm)
  }

  const handleVerifyFact = async (fact) => {
    const response = await verifyFact(fact.id, { status: 'verified', comment: 'Web 端核验通过' })
    setFacts((current) => current.map((item) => (item.id === fact.id ? response.data.data : item)))
  }

  const handleCreateEvidence = async (event) => {
    event.preventDefault()
    if (!evidenceForm.name.trim() || !evidenceForm.file_url.trim()) return
    const response = await createEvidence({
      project_id: projectId,
      name: evidenceForm.name.trim(),
      file_url: evidenceForm.file_url.trim(),
      evidence_type: evidenceForm.evidence_type,
      source: evidenceForm.source.trim(),
    })
    setEvidences((current) => [response.data.data, ...current])
    setEvidenceForm(emptyEvidenceForm)
  }

  const handleCreateMarketFact = async (event) => {
    event.preventDefault()
    if (!marketFactForm.title.trim() || !marketFactForm.content.trim()) return
    const response = await createFact({
      project_id: projectId,
      title: marketFactForm.title.trim(),
      content: marketFactForm.content.trim(),
      source: marketFactForm.source.trim(),
    })
    setFacts((current) => [response.data.data, ...current])
    setMarketFactForm(emptyMarketFactForm)
  }

  const handleScheduleCapture = async (row) => {
    const response = await createExternalDataJob({
      project_id: projectId,
      ...row.capturePlan,
      parameters: {
        dossier_row_id: row.id,
        system_target: row.systemTarget,
        requires_human_verification: true,
      },
    })
    setExternalJobs((current) => [response.data.data, ...current])
  }

  const handleCreateAssumption = async (event) => {
    event.preventDefault()
    if (!assumptionForm.title.trim()) return
    const response = await createAssumption({
      project_id: projectId,
      title: assumptionForm.title.trim(),
      content: assumptionForm.content.trim(),
      confidence: Number(assumptionForm.confidence) || 50,
    })
    setAssumptions((current) => [response.data.data, ...current])
    setAssumptionForm(emptyAssumptionForm)
  }

  const handleCreateGate = async (event) => {
    event.preventDefault()
    if (!gateForm.name.trim()) return
    const response = await createGate({
      project_id: projectId,
      name: gateForm.name.trim(),
      required_evidence: gateForm.required_evidence.trim(),
      owner_group: gateForm.owner_group,
      status: 'pending',
    })
    setGates((current) => [response.data.data, ...current])
    setGateForm(emptyGateForm)
  }

  const handleCreateRisk = async (event) => {
    event.preventDefault()
    if (!riskForm.title.trim()) return
    const response = await createRisk({
      project_id: projectId,
      title: riskForm.title.trim(),
      level: riskForm.level,
      mitigation: riskForm.mitigation.trim(),
      status: 'open',
    })
    setRisks((current) => [response.data.data, ...current])
    setRiskForm(emptyRiskForm)
  }

  const handleSubmitTask = async (task) => {
    const result = (taskResultById[task.id] || '').trim()
    if (!result) return
    const response = await submitTask(task.id, { result, evidence_ids: [] })
    setTasks((current) => current.map((item) => (item.id === task.id ? response.data.data : item)))
    setTaskResultById((current) => ({ ...current, [task.id]: '' }))
  }

  const handleAskAgent = async (event) => {
    event.preventDefault()
    if (!agentQuestion.trim()) return
    const response = await agentChat({ project_id: projectId, message: agentQuestion.trim() })
    setAgentAnswer(response.data.data.answer)
  }

  const handleSearchCases = async (event) => {
    event.preventDefault()
    const response = await searchCases(caseKeyword.trim())
    setCases(response.data.data || [])
  }

  const handleShareReport = async () => {
    const response = await shareReport(projectId, {
      version_id: project?.current_version_id,
      expires_in_days: 7,
    })
    setShareUrl(response.data.data.share_url)
    setMessage('报告分享链接已生成')
  }

  const handleGenerateFeasibilityReport = async () => {
    const response = await generateFeasibilityReport(projectId, {
      version_id: project?.current_version_id,
      tax_fee_rate: 0.15,
      use_ai_copy: true,
    })
    const report = response.data.data
    const downloadUrl = report.download_url?.startsWith('/')
      ? `http://localhost:8000${report.download_url}`
      : report.download_url
    const normalized = { ...report, download_url: downloadUrl }
    setFeasibilityReport(normalized)
    if (report.evidence) {
      setEvidences((current) => [report.evidence, ...current])
    }
    setMessage('报告已生成，可下载核验')
  }

  if (status === 'loading') {
    return <div className="state-panel">正在加载项目详情...</div>
  }

  if (status === 'error' || !project) {
    return (
      <div className="state-panel error">
        <strong>未能加载项目详情</strong>
        <span>请确认后端服务可用后重试。</span>
        <Link className="button button-secondary" to="/">返回工作台</Link>
      </div>
    )
  }

  return (
    <div className="page-stack project-detail-page">
      <Link className="back-link" to="/">← 返回工作台</Link>

      <section className="page-lead">
        <div>
          <span className="eyebrow">{[project.artist_name, project.city, project.venue].filter(Boolean).join(' · ') || 'PROJECT'}</span>
          <h2>{project.name}</h2>
          <p>集中管理项目版本、事实证据、假设、关卡、风险、任务与报告分享。</p>
        </div>
        <div className="button-row">
          <button className="button button-secondary" type="button" onClick={handleGenerateFeasibilityReport}>生成可行性报告</button>
          <button className="button button-primary" type="button" onClick={handleShareReport}>生成分享链接</button>
        </div>
      </section>

      <section className="metric-grid" aria-label="项目关键指标">
        {metrics.map((metric) => (
          <article className={`metric-card${metric.tone ? ` ${metric.tone}` : ''}`} key={metric.label}>
            <span className="sr-only">{metric.label} {metric.value}</span>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <small>{metric.delta}</small>
          </article>
        ))}
      </section>

      {(shareUrl || message) && (
        <section className="panel">
          {message && <div className="inline-message success">{message}</div>}
          {shareUrl && <div className="inline-message success">{shareUrl}</div>}
          {feasibilityReport?.download_url && (
            <a className="button button-secondary" href={feasibilityReport.download_url} target="_blank" rel="noreferrer" download>
              {feasibilityReport.file_name || '下载可行性研究报告'}
            </a>
          )}
        </section>
      )}

      <section className="content-grid content-grid-wide">
        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">VERSIONS</span>
              <h3>版本留痕</h3>
            </div>
            <span className="section-count">{versions.length} 个版本</span>
          </div>
          <DataList
            emptyText="暂无版本记录"
            items={versions}
            renderItem={(version) => (
              <span key={version.id}>
                V{version.version_no}
                <strong>{statusLabel(version.status)}</strong>
                <small>{version.finance_result?.total_cost ? `总成本 ¥${formatNumber(version.finance_result.total_cost)}` : '输入快照已留存'}</small>
              </span>
            )}
          />
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">AGENT</span>
              <h3>智能体建议</h3>
            </div>
          </div>
          <form className="compact-form" onSubmit={handleAskAgent}>
            <label className="field">
              <span>向智能体提问</span>
              <input value={agentQuestion} onChange={(event) => setAgentQuestion(event.target.value)} placeholder="询问下一步处理建议" />
            </label>
            <button className="button button-primary" type="submit">询问智能体</button>
          </form>
          {agentAnswer && <div className="agent-answer">{agentAnswer}</div>}
        </article>
      </section>

      <section className="project-detail-grid">
        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">FACTS</span>
              <h3>事实核查</h3>
            </div>
          </div>
          <DataList
            emptyText="暂无事实记录"
            items={facts}
            renderItem={(fact) => (
              <span key={fact.id}>
                {fact.title}
                <strong>{statusLabel(fact.status)}</strong>
                <small>{fact.content || '暂无说明'}{fact.source ? ` · ${fact.source}` : ''}</small>
                {fact.status !== 'verified' && (
                  <button className="button button-secondary" type="button" onClick={() => handleVerifyFact(fact)}>核验通过</button>
                )}
              </span>
            )}
          />
          <form className="compact-form" onSubmit={handleCreateFact}>
            <label className="field">
              <span>事实标题</span>
              <input value={factForm.title} onChange={(event) => setField(setFactForm, 'title', event.target.value)} />
            </label>
            <label className="field">
              <span>事实内容</span>
              <input value={factForm.content} onChange={(event) => setField(setFactForm, 'content', event.target.value)} />
            </label>
            <label className="field">
              <span>事实来源</span>
              <input value={factForm.source} onChange={(event) => setField(setFactForm, 'source', event.target.value)} />
            </label>
            <button className="button button-primary" type="submit">添加事实</button>
          </form>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">EVIDENCES</span>
              <h3>证据材料</h3>
            </div>
          </div>
          <DataList
            emptyText="暂无证据材料"
            items={evidences}
            renderItem={(evidence) => (
              <span key={evidence.id}>
                {evidence.name}
                <strong>{statusLabel(evidence.status)}</strong>
                <small>{evidence.source || evidence.evidence_type || '未标注来源'}</small>
              </span>
            )}
          />
          <form className="compact-form" onSubmit={handleCreateEvidence}>
            <label className="field">
              <span>证据名称</span>
              <input value={evidenceForm.name} onChange={(event) => setField(setEvidenceForm, 'name', event.target.value)} />
            </label>
            <label className="field">
              <span>证据链接</span>
              <input value={evidenceForm.file_url} onChange={(event) => setField(setEvidenceForm, 'file_url', event.target.value)} />
            </label>
            <label className="field">
              <span>证据来源</span>
              <input value={evidenceForm.source} onChange={(event) => setField(setEvidenceForm, 'source', event.target.value)} />
            </label>
            <button className="button button-primary" type="submit">上传证据</button>
          </form>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">ASSUMPTIONS</span>
              <h3>关键假设</h3>
            </div>
          </div>
          <DataList
            emptyText="暂无假设"
            items={assumptions}
            renderItem={(assumption) => (
              <span key={assumption.id}>
                {assumption.title}
                <strong>{assumption.confidence}%</strong>
                <small>{assumption.content || statusLabel(assumption.status)}</small>
              </span>
            )}
          />
          <form className="compact-form" onSubmit={handleCreateAssumption}>
            <label className="field">
              <span>假设标题</span>
              <input value={assumptionForm.title} onChange={(event) => setField(setAssumptionForm, 'title', event.target.value)} />
            </label>
            <label className="field">
              <span>假设说明</span>
              <input value={assumptionForm.content} onChange={(event) => setField(setAssumptionForm, 'content', event.target.value)} />
            </label>
            <button className="button button-primary" type="submit">添加假设</button>
          </form>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">GATES</span>
              <h3>推进关卡</h3>
            </div>
          </div>
          <DataList
            emptyText="暂无关卡"
            items={gates}
            renderItem={(gate) => (
              <span key={gate.id}>
                {gate.name}
                <strong>{statusLabel(gate.status)}</strong>
                <small>{gate.required_evidence || '未设置证据'}{gate.owner_group ? ` · ${gate.owner_group}` : ''}</small>
              </span>
            )}
          />
          <form className="compact-form" onSubmit={handleCreateGate}>
            <label className="field">
              <span>关卡名称</span>
              <input value={gateForm.name} onChange={(event) => setField(setGateForm, 'name', event.target.value)} />
            </label>
            <label className="field">
              <span>所需证据</span>
              <input value={gateForm.required_evidence} onChange={(event) => setField(setGateForm, 'required_evidence', event.target.value)} />
            </label>
            <button className="button button-primary" type="submit">添加关卡</button>
          </form>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">RISKS</span>
              <h3>风险评估</h3>
            </div>
          </div>
          <DataList
            emptyText="暂无风险"
            items={risks}
            renderItem={(risk) => (
              <span key={risk.id}>
                {risk.title}
                <strong>{statusLabel(risk.level)}</strong>
                <small>{risk.mitigation || statusLabel(risk.status)}</small>
              </span>
            )}
          />
          <form className="compact-form" onSubmit={handleCreateRisk}>
            <label className="field">
              <span>风险标题</span>
              <input value={riskForm.title} onChange={(event) => setField(setRiskForm, 'title', event.target.value)} />
            </label>
            <label className="field">
              <span>缓释方案</span>
              <input value={riskForm.mitigation} onChange={(event) => setField(setRiskForm, 'mitigation', event.target.value)} />
            </label>
            <button className="button button-primary" type="submit">添加风险</button>
          </form>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">TASKS</span>
              <h3>任务提交</h3>
            </div>
          </div>
          <DataList
            emptyText="暂无任务"
            items={tasks}
            renderItem={(task) => (
              <span key={task.id}>
                {task.title}
                <strong>{statusLabel(task.status)}</strong>
                <small>{task.result || task.description || task.due_date || '暂无说明'}</small>
                {task.status !== 'submitted' && (
                  <div className="inline-edit-form">
                    <label className="field">
                      <span>任务提交结果</span>
                      <input value={taskResultById[task.id] || ''} onChange={(event) => setTaskResultById((current) => ({ ...current, [task.id]: event.target.value }))} />
                    </label>
                    <button className="button button-primary" type="button" onClick={() => handleSubmitTask(task)}>提交任务</button>
                  </div>
                )}
              </span>
            )}
          />
        </article>
      </section>

      <section className="panel market-dossier-panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">MARKET DOSSIER</span>
            <h3>市场资料对照</h3>
          </div>
          <span className="section-count">{zhaoYazhiMarketDossier.length} 个 Sheet</span>
        </div>

        <form className="market-fact-form" onSubmit={handleCreateMarketFact}>
          <label className="field">
            <span>资料条目</span>
            <input value={marketFactForm.title} onChange={(event) => setField(setMarketFactForm, 'title', event.target.value)} />
          </label>
          <label className="field field-wide">
            <span>人工资料内容</span>
            <input value={marketFactForm.content} onChange={(event) => setField(setMarketFactForm, 'content', event.target.value)} />
          </label>
          <label className="field">
            <span>人工资料来源</span>
            <input value={marketFactForm.source} onChange={(event) => setField(setMarketFactForm, 'source', event.target.value)} />
          </label>
          <button className="button button-primary" type="submit">写入人工事实</button>
        </form>

        <div className="dossier-grid">
          {zhaoYazhiMarketDossier.map((sheet) => (
            <article className="dossier-sheet" key={sheet.sheet}>
              <div className="dossier-sheet-heading">
                <strong>{sheet.sheet}</strong>
                <small>{sheet.rows.length} 条数据</small>
              </div>
              <div className="dossier-row-list">
                {sheet.rows.map((row) => {
                  const primary = row.cells[sheet.headers[0]]
                  const secondary = sheet.headers.slice(1, 3).map((header) => row.cells[header]).filter(Boolean).join(' · ')

                  return (
                    <div className="dossier-row" key={row.id}>
                      <div className="dossier-row-main">
                        <b>{primary}</b>
                        <small>{secondary}</small>
                      </div>
                      <div className="dossier-row-meta">
                        <span>系统落点</span>
                        <strong>{row.systemTarget}</strong>
                      </div>
                      <div className="dossier-row-meta">
                        <span>处理方式</span>
                        <strong>{row.handling}</strong>
                      </div>
                      {row.capture && (
                        <button className="button button-secondary" type="button" onClick={() => handleScheduleCapture(row)}>
                          安排抓取
                        </button>
                      )}
                    </div>
                  )
                })}
              </div>
            </article>
          ))}
        </div>

        <div className="external-job-list">
          <strong>抓取任务</strong>
          {externalJobs.length === 0 ? (
            <small>暂无外部抓取任务</small>
          ) : (
            externalJobs.map((job) => (
              <span key={job.id}>
                {job.query}
                <em>{statusLabel(job.status)} · {job.provider}</em>
              </span>
            ))
          )}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">CASES</span>
            <h3>历史案例检索</h3>
          </div>
        </div>
        <form className="compact-form inline-form" onSubmit={handleSearchCases}>
          <label className="field">
            <span>案例搜索</span>
            <input value={caseKeyword} onChange={(event) => setCaseKeyword(event.target.value)} placeholder="按项目、艺人、城市或场馆搜索" />
          </label>
          <button className="button button-primary" type="submit">搜索案例</button>
        </form>
        <DataList
          emptyText="暂无匹配案例"
          items={cases}
          renderItem={(item) => (
            <span key={item.project_id}>
              {item.name}
              <strong>{statusLabel(item.status)}</strong>
              <small>{[item.artist_name, item.city, item.venue].filter(Boolean).join(' · ')}</small>
            </span>
          )}
        />
      </section>
    </div>
  )
}
