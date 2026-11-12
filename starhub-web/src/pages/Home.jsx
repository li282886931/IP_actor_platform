import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  calculateFinance,
  createDecision,
  createProject,
  createTask,
  getDashboardAnalytics,
  getTicketingSummary,
  listProjects,
  listTasks,
  shareReport,
  submitTask,
} from '../api'
import Avatar from '../components/Avatar'
import CardMenu from '../components/CardMenu'
import { ProgressRing, SegmentedBar } from '../components/Charts'
import { SchedulePanel, TeamActivityPanel } from '../components/SchedulePanel'
import { MetricIcon } from '../components/icons'

function MetricGrid({ metrics }) {
  return (
    <section className="metric-grid" aria-label="关键指标">
      {metrics.map((metric) => (
        <article className={`metric-card${metric.tone ? ` ${metric.tone}` : ''}`} key={metric.label}>
          <div className="metric-head">
            <span className="metric-icon" aria-hidden="true"><MetricIcon label={metric.label} size={20} /></span>
            <span className="metric-label">{metric.label}</span>
          </div>
          <strong>{metric.value}</strong>
          <small>{metric.delta}</small>
        </article>
      ))}
    </section>
  )
}

function BusinessWorkbench() {
  const [projects, setProjects] = useState([])
  const [tasks, setTasks] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [ticketing, setTicketing] = useState(null)
  const [financeResults, setFinanceResults] = useState({})
  const [financeInputs, setFinanceInputs] = useState({})
  const [decisionResults, setDecisionResults] = useState({})
  const [status, setStatus] = useState('loading')
  const [submitStatus, setSubmitStatus] = useState('idle')
  const [projectActionStatus, setProjectActionStatus] = useState({})
  const [message, setMessage] = useState('')
  const [messageTone, setMessageTone] = useState('success')
  const [completingTaskId, setCompletingTaskId] = useState(null)
  const [quickTaskResult, setQuickTaskResult] = useState('')
  const createNameInputRef = useRef(null)
  const [form, setForm] = useState({
    name: '',
    artist_name: '',
    city: '',
    venue: '',
  })

  useEffect(() => {
    let active = true
    setStatus('loading')

    Promise.all([
      listProjects(),
      listTasks(),
      getDashboardAnalytics().catch(() => ({ data: { data: null } })),
      getTicketingSummary().catch(() => ({ data: { data: null } })),
    ])
      .then(([projectResponse, taskResponse, analyticsResponse, ticketingResponse]) => {
        if (!active) return
        setProjects(projectResponse.data.data || [])
        setTasks(taskResponse.data.data || [])
        setAnalytics(analyticsResponse.data.data || null)
        setTicketing(ticketingResponse.data.data || null)
        setStatus('success')
      })
      .catch(() => {
        if (active) setStatus('error')
      })

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    const focusCreateForm = () => {
      createNameInputRef.current?.focus()
      createNameInputRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
    }
    window.addEventListener('starhub:focus-project-create', focusCreateForm)
    return () => window.removeEventListener('starhub:focus-project-create', focusCreateForm)
  }, [])

  const handleFieldChange = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }))
  }

  const handleCreateProject = async (event) => {
    event.preventDefault()
    if (!form.name.trim()) {
      setMessageTone('error')
      setMessage('请填写项目名称')
      return
    }

    setSubmitStatus('loading')
    setMessageTone('success')
    setMessage('')
    try {
      const response = await createProject({
        ...form,
        name: form.name.trim(),
        artist_name: form.artist_name.trim(),
        city: form.city.trim(),
        venue: form.venue.trim(),
      })
      setProjects((current) => [response.data.data, ...current])
      setForm({ name: '', artist_name: '', city: '', venue: '' })
      setSubmitStatus('success')
      setMessageTone('success')
      setMessage('项目已创建，可继续补充财务测算参数。')
    } catch {
      setSubmitStatus('error')
      setMessageTone('error')
      setMessage('项目创建失败，请稍后重试。')
    }
  }

  const formatNumber = (value) => new Intl.NumberFormat('zh-CN').format(value || 0)
  const formatCurrency = (value) => `¥${formatNumber(value)}`
  const missingFieldLabels = {
    expected_attendance: '预计人数',
    avg_ticket_price: '平均票价',
    artist_fee: '艺人费',
    venue_cost: '场地成本',
    marketing_cost: '宣发成本',
    production_cost: '制作成本',
  }

  const financeFields = [
    { key: 'expected_attendance', label: '预计人数' },
    { key: 'avg_ticket_price', label: '平均票价' },
    { key: 'artist_fee', label: '艺人费' },
    { key: 'venue_cost', label: '场地成本' },
    { key: 'marketing_cost', label: '宣发成本' },
    { key: 'production_cost', label: '制作成本' },
  ]

  const nextStepActions = [
    { title: '发起政策审批', description: '确认政策审批材料、申报路径和责任人。' },
    { title: '确认场地安全', description: '确认场地安全方案、安保容量、消防与应急预案。' },
    { title: '确认艺人授权', description: '确认艺人授权范围、档期锁定、肖像与宣发素材使用边界。' },
    { title: '确认资金合同', description: '确认资金预算、付款节点、合同主体和风控条款。' },
  ]

  const financeValue = (project, field) => (
    financeInputs[project.id]?.[field] ?? project[field] ?? ''
  )

  const parseOptionalNumber = (value) => {
    if (value === '' || value === null || value === undefined) return undefined
    const numberValue = Number(value)
    return Number.isFinite(numberValue) ? numberValue : undefined
  }

  const handleFinanceInputChange = (projectId, field, value) => {
    setFinanceInputs((current) => ({
      ...current,
      [projectId]: {
        ...(current[projectId] || {}),
        [field]: value,
      },
    }))
  }

  const formatStatus = (value) => {
    const statusMap = {
      calculated: '已测算',
      pending_confirmation: '待确认',
      draft: '草稿',
      archived: '已归档',
    }
    return statusMap[value] || value || '待处理'
  }

  const formatTaskStatus = (value) => {
    const statusMap = {
      pending: '待处理',
      submitted: '已提交',
      completed: '已完成',
    }
    return statusMap[value] || value || '待处理'
  }

  const taskTone = (value) => {
    if (value === 'completed' || value === 'submitted') return 'success'
    return 'warning'
  }

  const handleCalculateFinance = async (project) => {
    setProjectActionStatus((current) => ({ ...current, [`finance-${project.id}`]: 'loading' }))
    setMessage('')
    try {
      const response = await calculateFinance({
        project_id: project.id,
        expected_attendance: parseOptionalNumber(financeValue(project, 'expected_attendance')),
        avg_ticket_price: parseOptionalNumber(financeValue(project, 'avg_ticket_price')),
        artist_fee: parseOptionalNumber(financeValue(project, 'artist_fee')),
        venue_cost: parseOptionalNumber(financeValue(project, 'venue_cost')),
        marketing_cost: parseOptionalNumber(financeValue(project, 'marketing_cost')),
        production_cost: parseOptionalNumber(financeValue(project, 'production_cost')),
      })
      const result = response.data.data
      setFinanceResults((current) => ({ ...current, [project.id]: result }))
      setProjects((current) => current.map((item) => (
        item.id === project.id
          ? { ...item, status: result.project_status || 'calculated', current_version_id: result.version_id || item.current_version_id }
          : item
      )))
      setProjectActionStatus((current) => ({ ...current, [`finance-${project.id}`]: 'success' }))
    } catch {
      setProjectActionStatus((current) => ({ ...current, [`finance-${project.id}`]: 'error' }))
      setMessageTone('error')
      setMessage('财务测算失败，请补齐项目参数后重试。')
    }
  }

  const handleAdvanceDecision = async (project) => {
    const versionId = financeResults[project.id]?.version_id || project.current_version_id
    setProjectActionStatus((current) => ({ ...current, [`decision-${project.id}`]: 'loading' }))
    setMessage('')
    try {
      const response = await createDecision({
        project_id: project.id,
        version_id: versionId,
        decision_type: 'advance',
        conditions: '完成政策审批、场地安全、艺人授权与资金合同确认后推进。',
      })
      const result = response.data.data
      setDecisionResults((current) => ({ ...current, [project.id]: result }))
      setProjects((current) => current.map((item) => (
        item.id === project.id ? { ...item, status: result.project_status || 'pending_confirmation' } : item
      )))
      setProjectActionStatus((current) => ({ ...current, [`decision-${project.id}`]: 'success' }))
      setMessageTone('success')
      setMessage('已提交推进决策')
    } catch {
      setProjectActionStatus((current) => ({ ...current, [`decision-${project.id}`]: 'error' }))
      setMessageTone('error')
      setMessage('决策提交失败，请确认已有可用版本。')
    }
  }

  const hasNextStepTask = (projectId, title) => (
    tasks.some((task) => task.project_id === projectId && task.title === title)
  )

  const handleCreateNextStepTask = async (project, decisionResult, action) => {
    if (hasNextStepTask(project.id, action.title)) return

    setProjectActionStatus((current) => ({ ...current, [`task-${project.id}-${action.title}`]: 'loading' }))
    setMessage('')
    try {
      const versionLabel = decisionResult?.version_id ? `V${decisionResult.version_id}` : '当前版本'
      const response = await createTask({
        project_id: project.id,
        title: action.title,
        description: `基于推进决策 ${versionLabel}，${action.description}`,
      })
      setTasks((current) => [response.data.data, ...current])
      setProjectActionStatus((current) => ({ ...current, [`task-${project.id}-${action.title}`]: 'success' }))
      setMessageTone('success')
      setMessage('下一步任务已安排')
    } catch {
      setProjectActionStatus((current) => ({ ...current, [`task-${project.id}-${action.title}`]: 'error' }))
      setMessageTone('error')
      setMessage('下一步任务创建失败，请稍后重试。')
    }
  }

  const focusCreateForm = () => {
    createNameInputRef.current?.focus()
    createNameInputRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
  }

  const handleQuickCompleteTask = async (task) => {
    const result = quickTaskResult.trim()
    if (!result) {
      setMessageTone('error')
      setMessage('请填写任务结果后再标记完成。')
      return
    }
    try {
      const response = await submitTask(task.id, { result, evidence_ids: [] })
      setTasks((current) => current.map((item) => (item.id === task.id ? response.data.data : item)))
      setCompletingTaskId(null)
      setQuickTaskResult('')
      setMessageTone('success')
      setMessage(`任务「${task.title}」已提交，等待负责人核验。`)
    } catch {
      setMessageTone('error')
      setMessage('任务提交失败，请刷新后重试。')
    }
  }

  const handleShareProject = async (projectId, close) => {
    try {
      const response = await shareReport(projectId, { expires_in_days: 7 })
      setMessageTone('success')
      setMessage(`报告分享链接已生成：${response.data.data.share_url}`)
      close()
    } catch {
      setMessageTone('error')
      setMessage('分享链接生成失败，请稍后重试。')
    }
  }

  const activeProjects = projects.filter((project) => project.status !== 'archived').length
  const pendingTasks = tasks.filter((task) => task.status === 'pending').length
  const analyticsSummary = analytics?.summary || {}
  const ticketingSummary = ticketing?.summary || {}
  const projectsById = Object.fromEntries(projects.map((project) => [project.id, project]))

  const metrics = [
    { label: '项目总数', value: String(projects.length), delta: `${analyticsSummary.active_projects ?? activeProjects} 个仍在推进` },
    { label: '中性利润合计', value: formatCurrency(analyticsSummary.neutral_profit_total || 0), delta: '来自当前版本测算' },
    { label: '预约人数', value: `${formatNumber(ticketingSummary.reservation_count ?? analyticsSummary.reservations ?? 0)} 人`, delta: `${ticketingSummary.on_sale_shows ?? analyticsSummary.on_sale_shows ?? 0} 场售票中` },
    { label: '待办任务', value: String(analyticsSummary.pending_tasks ?? pendingTasks), delta: 'Agent / 人工任务池', tone: (analyticsSummary.pending_tasks ?? pendingTasks) ? 'danger' : undefined },
  ]

  const doneTasks = tasks.filter((task) => task.status === 'submitted' || task.status === 'completed').length
  const taskCompletion = tasks.length ? (doneTasks / tasks.length) * 100 : 0
  const calculatedProjects = analyticsSummary.calculated_projects
    ?? projects.filter((project) => project.status === 'calculated').length
  const pendingConfirmationProjects = analyticsSummary.pending_confirmation_projects
    ?? projects.filter((project) => project.status === 'pending_confirmation').length
  const archivedProjects = projects.filter((project) => project.status === 'archived').length
  const draftProjects = Math.max(
    projects.length - calculatedProjects - pendingConfirmationProjects - archivedProjects,
    0,
  )
  const calculationRate = projects.length ? (calculatedProjects / projects.length) * 100 : 0

  return (
    <div className="page-stack">
      <section className="page-lead">
        <div>
          <span className="eyebrow">PHASE 1 PROJECT FLOW</span>
          <h2>项目决策工作台</h2>
          <p>围绕项目创建、财务测算、版本留痕和人工确认，打通最小决策闭环。</p>
        </div>
        <Link className="button button-primary" to="/generate">生成宣发内容</Link>
      </section>

      <MetricGrid metrics={metrics} />

      <section className="module-grid" aria-label="快捷操作">
        <Link className="module-card" to="/artist">
          <span className="module-index">01</span>
          <h3>艺人智策</h3>
          <p>查询艺人热度、粉丝画像与风险信号，辅助选择合作对象。</p>
          <span className="module-link">进入模块 →</span>
        </Link>
        <Link className="module-card" to="/generate">
          <span className="module-index">02</span>
          <h3>AI 宣发</h3>
          <p>基于项目资料生成宣发文案与投放内容，流式输出可核验。</p>
          <span className="module-link">进入模块 →</span>
        </Link>
        <button type="button" className="module-card module-card-button" onClick={focusCreateForm}>
          <span className="module-index">03</span>
          <h3>创建项目</h3>
          <p>录入项目名称、艺人、城市与场馆，开始第一轮财务测算。</p>
          <span className="module-link">填写项目信息 →</span>
        </button>
      </section>

      <section className="content-grid content-grid-wide">
        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">PROGRESS</span>
              <h3>项目推进</h3>
            </div>
            <span className="status-badge positive">实时汇总</span>
          </div>
          <div className="ring-grid">
            <ProgressRing
              percent={taskCompletion}
              label="任务完成率"
              caption={`已完成 ${doneTasks} / 共 ${tasks.length} 项任务`}
              tone="green"
            />
            <ProgressRing
              percent={calculationRate}
              label="测算覆盖率"
              caption={`已测算 ${calculatedProjects} / ${projects.length} 个项目`}
            />
          </div>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">PORTFOLIO</span>
              <h3>项目状态分布</h3>
            </div>
            <span className="section-count">{projects.length} 个项目</span>
          </div>
          <SegmentedBar segments={[
            { label: '已测算', value: calculatedProjects, tone: 'gold' },
            { label: '待确认', value: pendingConfirmationProjects, tone: 'amber' },
            { label: '推进中 / 草稿', value: draftProjects, tone: 'muted' },
            { label: '已归档', value: archivedProjects, tone: 'muted2' },
          ]} />
        </article>
      </section>

      <section className="content-grid content-grid-wide">
        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">SCHEDULE</span>
              <h3>日程与待办</h3>
            </div>
            <span className="section-count">{pendingTasks} 项待处理</span>
          </div>
          <SchedulePanel tasks={tasks} projectsById={projectsById} />
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">ACTIVITY</span>
              <h3>团队动态</h3>
            </div>
          </div>
          <TeamActivityPanel tasks={tasks} projectsById={projectsById} />
        </article>
      </section>

      <section className="content-grid content-grid-wide">
        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">PROJECTS</span>
              <h3>项目列表</h3>
            </div>
            <span className="section-count">{projects.length} 个项目</span>
          </div>

          {status === 'loading' && <div className="state-panel">正在加载项目数据...</div>}
          {status === 'error' && (
            <div className="state-panel error">
              <strong>项目数据暂时不可用</strong>
              <span>请确认后端服务已启动并连接到 MySQL。</span>
            </div>
          )}
          {status === 'success' && projects.length === 0 && <div className="state-panel">暂无项目，先创建一个项目。</div>}
          {status === 'success' && projects.length > 0 && (
            <div className="summary-list">
              {projects.map((project) => {
                const financeResult = financeResults[project.id]
                const neutralScenario = financeResult?.scenarios?.neutral
                const hasCalculatedFinance = financeResult?.status !== 'pending_input' && neutralScenario
                const missingFields = (financeResult?.missing_fields || []).map((field) => missingFieldLabels[field] || field)
                const decisionResult = decisionResults[project.id]

                return (
                  <article className="project-list-row" key={project.id}>
                    <div className="project-list-main">
                      <div className="project-row-title">
                        <Link className="summary-title-link" to={`/projects/${project.id}`}>{project.name}</Link>
                        <CardMenu ariaLabel={`${project.name}更多操作`}>
                          {({ close }) => (
                            <>
                              <Link role="menuitem" to={`/projects/${project.id}`} onClick={close}>查看详情</Link>
                              <button
                                type="button"
                                role="menuitem"
                                onClick={() => handleShareProject(project.id, close)}
                              >
                                分享报告
                              </button>
                            </>
                          )}
                        </CardMenu>
                      </div>
                      <small>{[project.artist_name, project.city, project.venue].filter(Boolean).join(' · ') || '基础信息待补充'}</small>
                      {(neutralScenario || financeResult?.breakeven_attendance) && (
                        <div className="project-list-metrics">
                          {neutralScenario && (
                            <small>
                              中性利润 ¥{formatNumber(neutralScenario.profit)}
                            </small>
                          )}
                          {financeResult?.breakeven_attendance && (
                            <small>保本人数 {formatNumber(financeResult.breakeven_attendance)}</small>
                          )}
                        </div>
                      )}
                    </div>
                    <strong className="project-status">{formatStatus(project.status)}</strong>
                    <div className="inline-actions project-row-actions">
                      <button
                        className="button button-secondary"
                        disabled={projectActionStatus[`finance-${project.id}`] === 'loading'}
                        onClick={() => handleCalculateFinance(project)}
                        type="button"
                      >
                        {projectActionStatus[`finance-${project.id}`] === 'loading' ? '测算中...' : '计算盈亏'}
                      </button>
                      <button
                        className="button button-primary"
                        disabled={projectActionStatus[`decision-${project.id}`] === 'loading'}
                        onClick={() => handleAdvanceDecision(project)}
                        type="button"
                      >
                        {projectActionStatus[`decision-${project.id}`] === 'loading' ? '提交中...' : '提交推进决策'}
                      </button>
                    </div>

                    <div className="project-finance-inputs" aria-label={`${project.name}真实测算参数`}>
                      {financeFields.map((field) => (
                        <label className="field" key={field.key}>
                          <span>{field.label}</span>
                          <input
                            inputMode="numeric"
                            type="number"
                            value={financeValue(project, field.key)}
                            onChange={(event) => handleFinanceInputChange(project.id, field.key, event.target.value)}
                          />
                        </label>
                      ))}
                    </div>

                    {financeResult && !hasCalculatedFinance && (
                      <section className="project-action-result pending" aria-label={`${project.name}测算参数待补齐`}>
                        <div className="project-action-result-heading">
                          <strong>待补齐真实测算参数</strong>
                          {financeResult.version_id && <em>V{financeResult.version_id}</em>}
                        </div>
                        <p className="project-result-note">
                          {missingFields.length ? missingFields.join('、') : '请补齐真实人数、票价与成本后重新测算'}
                        </p>
                      </section>
                    )}

                    {financeResult && hasCalculatedFinance && (
                      <section className="project-action-result" aria-label={`${project.name}测算结果`}>
                        <div className="project-action-result-heading">
                          <strong>测算结果</strong>
                          {financeResult.version_id && <em>V{financeResult.version_id}</em>}
                        </div>
                        <dl className="project-result-grid">
                          <div>
                            <dt>中性收入</dt>
                            <dd>{formatCurrency(neutralScenario?.revenue)}</dd>
                          </div>
                          <div>
                            <dt>中性利润</dt>
                            <dd>{formatCurrency(neutralScenario?.profit)}</dd>
                          </div>
                          <div>
                            <dt>保本人数</dt>
                            <dd>{formatNumber(financeResult.breakeven_attendance)}</dd>
                          </div>
                          <div>
                            <dt>测算版本</dt>
                            <dd>{financeResult.version_id ? `V${financeResult.version_id}` : '待生成'}</dd>
                          </div>
                        </dl>
                      </section>
                    )}

                    {decisionResult && (
                      <section className="project-action-result decision" aria-label={`${project.name}推进结果`}>
                        <div className="project-action-result-heading">
                          <strong>推进结果</strong>
                          {decisionResult.version_id && <em>V{decisionResult.version_id}</em>}
                        </div>
                        <dl className="project-result-grid">
                          <div>
                            <dt>决策类型</dt>
                            <dd>{decisionResult.decision_type === 'advance' ? '推进' : decisionResult.decision_type}</dd>
                          </div>
                          <div>
                            <dt>决策状态</dt>
                            <dd>{formatStatus(decisionResult.project_status)}</dd>
                          </div>
                          <div className="project-result-wide">
                            <dt>推进条件</dt>
                            <dd>{decisionResult.conditions || '待补充推进条件'}</dd>
                          </div>
                        </dl>
                        <div className="next-step-actions">
                          <strong>下一步操作</strong>
                          <div>
                            {nextStepActions.map((action) => {
                              const scheduled = hasNextStepTask(project.id, action.title)
                              const loading = projectActionStatus[`task-${project.id}-${action.title}`] === 'loading'
                              return (
                                <button
                                  className={`button ${scheduled ? 'button-secondary' : 'button-primary'}`}
                                  disabled={scheduled || loading}
                                  key={action.title}
                                  onClick={() => handleCreateNextStepTask(project, decisionResult, action)}
                                  type="button"
                                >
                                  {scheduled ? '已安排' : loading ? '安排中...' : action.title}
                                </button>
                              )
                            })}
                          </div>
                        </div>
                      </section>
                    )}
                  </article>
                )
              })}
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div className="task-panel-title">
              <div>
                <span className="eyebrow">TASKS</span>
                <h3>待办任务</h3>
              </div>
            </div>
          </div>

          {tasks.length === 0 ? (
            <div className="state-panel">暂无待办任务</div>
          ) : (
            <div className="task-groups">
              <div className="task-group">
                <div className="task-group-head">
                  <span>待处理</span>
                  <small>{tasks.filter((task) => task.status === 'pending').length} 项</small>
                </div>
                <div className="activity-list">
                  {tasks.filter((task) => task.status === 'pending').map((task) => {
                    const project = projectsById[task.project_id]
                    const projectName = task.project_name || project?.name || `项目 #${task.project_id}`
                    const taskSummary = task.result || task.description || '待补充执行说明'
                    const evidenceCount = task.evidence_count ?? (Array.isArray(task.evidence_ids) ? task.evidence_ids.length : 0)
                    const completing = completingTaskId === task.id
                    return (
                      <div className="task-card" key={task.id}>
                        <button
                          type="button"
                          className={`task-check${completing ? ' active' : ''}`}
                          aria-label={`标记「${task.title}」完成`}
                          aria-pressed={completing}
                          onClick={() => {
                            setCompletingTaskId(completing ? null : task.id)
                            setQuickTaskResult('')
                          }}
                        />
                        <div className="task-card-body">
                          <div className="task-card-head">
                            <strong>{task.title}</strong>
                            <span className={`status-badge ${taskTone(task.status)}`}>{formatTaskStatus(task.status)}</span>
                          </div>
                          <small>{`${projectName} · 截止 ${task.due_date || '待设置'}`}</small>
                          <p>{taskSummary}</p>
                          {completing && (
                            <div className="task-quick-complete">
                              <input
                                value={quickTaskResult}
                                onChange={(event) => setQuickTaskResult(event.target.value)}
                                placeholder="填写完成结果，提交后等待负责人核验"
                                aria-label={`${task.title}完成结果`}
                              />
                              <button type="button" className="button button-primary" onClick={() => handleQuickCompleteTask(task)}>
                                提交完成
                              </button>
                            </div>
                          )}
                          <div className="task-card-foot">
                            <span className="task-assignee">
                              <Avatar name={task.assignee_name || ''} size={22} />
                              <small>{task.assignee_name || '待分配'}</small>
                            </span>
                            <small>{`证据 ${evidenceCount} 份`}</small>
                            <Link className="summary-title-link" to={`/projects/${task.project_id}`}>查看项目</Link>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              <div className="task-group">
                <div className="task-group-head">
                  <span>已完成</span>
                  <small>{tasks.filter((task) => task.status !== 'pending').length} 项</small>
                </div>
                <div className="activity-list">
                  {tasks.filter((task) => task.status !== 'pending').map((task) => {
                    const project = projectsById[task.project_id]
                    const projectName = task.project_name || project?.name || `项目 #${task.project_id}`
                    const taskSummary = task.result || task.description || '待补充执行说明'
                    const evidenceCount = task.evidence_count ?? (Array.isArray(task.evidence_ids) ? task.evidence_ids.length : 0)
                    return (
                      <div className="task-card task-card-done" key={task.id}>
                        <span className="task-check checked" aria-hidden="true">✓</span>
                        <div className="task-card-body">
                          <div className="task-card-head">
                            <strong>{task.title}</strong>
                            <span className={`status-badge ${taskTone(task.status)}`}>{formatTaskStatus(task.status)}</span>
                          </div>
                          <small>{`${projectName} · 截止 ${task.due_date || '待设置'}`}</small>
                          <p>{taskSummary}</p>
                          <div className="task-card-foot">
                            <span className="task-assignee">
                              <Avatar name={task.assignee_name || ''} size={22} />
                              <small>{task.assignee_name || '待分配'}</small>
                            </span>
                            <small>{`证据 ${evidenceCount} 份`}</small>
                            <Link className="summary-title-link" to={`/projects/${task.project_id}`}>查看项目</Link>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">TICKETING</span>
              <h3>票务预约汇总</h3>
            </div>
            <span className="section-count">{formatNumber(ticketingSummary.reservation_count || 0)} 人预约</span>
          </div>
          <div className="summary-list compact-list">
            <span>售票中场次<strong>{formatNumber(ticketingSummary.on_sale_shows || 0)} 场</strong></span>
            <span>演出总数<strong>{formatNumber(ticketingSummary.total_shows || 0)} 场</strong></span>
          </div>
          {(ticketing?.shows || []).length > 0 && (
            <div className="activity-list">
              {(ticketing.shows || []).slice(0, 3).map((show) => (
                <div key={show.id}>
                  <span className="activity-mark success" />
                  <p>
                    <strong>{show.title}</strong>
                    <small>{formatNumber(show.reservation_count || 0)} 人预约 · {show.status === 'on_sale' ? '售票中' : show.status}</small>
                  </p>
                </div>
              ))}
            </div>
          )}
        </article>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">CREATE PROJECT</span>
            <h3>创建项目</h3>
          </div>
        </div>
        <form className="project-create-form" onSubmit={handleCreateProject}>
          <div className="form-grid">
            <label className="field">
              <span>项目名称</span>
              <input ref={createNameInputRef} value={form.name} onChange={(event) => handleFieldChange('name', event.target.value)} />
            </label>
            <label className="field">
              <span>艺人</span>
              <input value={form.artist_name} onChange={(event) => handleFieldChange('artist_name', event.target.value)} />
            </label>
            <label className="field">
              <span>城市</span>
              <input value={form.city} onChange={(event) => handleFieldChange('city', event.target.value)} />
            </label>
            <label className="field">
              <span>场馆</span>
              <input value={form.venue} onChange={(event) => handleFieldChange('venue', event.target.value)} />
            </label>
          </div>
          <button className="button button-primary" disabled={submitStatus === 'loading'} type="submit">
            {submitStatus === 'loading' ? '创建中...' : '创建项目'}
          </button>
        </form>
        {message && <div className={`inline-message ${messageTone}`}>{message}</div>}
      </section>

    </div>
  )
}

export default function Home() {
  return <BusinessWorkbench />
}
