import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { calculateFinance, createDecision, createProject, listProjects, listShows, listTasks } from '../api'
import ShowCard from '../components/ShowCard'

const dashboardByRole = {
  B: {
    eyebrow: 'BUSINESS OPERATIONS',
    title: '项目经营总览',
    description: '集中查看票房、销售与宣发效率，优先处理异常项目。',
    action: '新建项目',
    metrics: [
      { label: '预估票房', value: '¥12.5M', delta: '较上周 +8.4%' },
      { label: '已售票数', value: '18,342', delta: '整体售票率 73.8%' },
      { label: '宣发消耗', value: '¥432K', delta: '预算执行 62%' },
      { label: '风险告警', value: '2', delta: '1 项需今日处理', tone: 'danger' },
    ],
    modules: [
      { title: '艺人智策', copy: '热度、风险与城市匹配建议', to: '/artist' },
      { title: 'AI 宣发', copy: '快速生成海报文案与短视频脚本', to: '/generate' },
      { title: '项目进度', copy: '8 个项目进行中，3 个临近开售' },
    ],
  },
  Brand: {
    eyebrow: 'BRAND PARTNERSHIP',
    title: '品牌合作概览',
    description: '评估合作人群质量、活动转化与品牌曝光表现。',
    action: '创建合作方案',
    metrics: [
      { label: '覆盖用户', value: '12.3K', delta: '核心人群占比 68%' },
      { label: '合作收入', value: '¥1.2M', delta: '较上月 +12.6%' },
      { label: '平均 ROI', value: '3.8', delta: '高于行业均值 0.7' },
      { label: '进行中合作', value: '8', delta: '本周新增 2 个' },
    ],
    modules: [
      { title: '受众洞察', copy: '查看兴趣、地域与消费能力分布', to: '/artist' },
      { title: 'AI 品宣', copy: '根据艺人与城市生成合作文案', to: '/generate' },
      { title: '投放表现', copy: '短视频渠道贡献 46% 的新增触达' },
    ],
  },
  G: {
    eyebrow: 'CITY CULTURE & TOURISM',
    title: '城市文旅概览',
    description: '洞察大型演出对跨城客流和本地消费的带动效果。',
    action: '导出城市报告',
    metrics: [
      { label: '跨城观演', value: '28.6K', delta: '外地观众占比 41%' },
      { label: '消费拉动', value: '¥86M', delta: '餐饮住宿贡献 57%' },
      { label: '城市热度', value: '92', delta: '全国排名第 4' },
      { label: '舆情风险', value: '低', delta: '暂无高风险事件' },
    ],
    modules: [
      { title: '艺人洞察', copy: '评估艺人与城市客群的匹配度', to: '/artist' },
      { title: 'AI 宣发', copy: '生成城市文旅联合传播内容', to: '/generate' },
      { title: '客流分析', copy: '核心商圈演出日客流提升 23%' },
    ],
  },
}

function MetricGrid({ metrics }) {
  return (
    <section className="metric-grid" aria-label="关键指标">
      {metrics.map((metric) => (
        <article className={`metric-card${metric.tone ? ` ${metric.tone}` : ''}`} key={metric.label}>
          <span>{metric.label}</span>
          <strong>{metric.value}</strong>
          <small>{metric.delta}</small>
        </article>
      ))}
    </section>
  )
}

function RoleDashboard({ role }) {
  const dashboard = dashboardByRole[role]

  return (
    <div className="page-stack">
      <section className="page-lead">
        <div>
          <span className="eyebrow">{dashboard.eyebrow}</span>
          <h2>{dashboard.title}</h2>
          <p>{dashboard.description}</p>
        </div>
        <button className="button button-primary" type="button">{dashboard.action}</button>
      </section>

      <MetricGrid metrics={dashboard.metrics} />

      <section className="content-grid content-grid-wide">
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">PERFORMANCE</span>
              <h3>近 7 日业务趋势</h3>
            </div>
            <span className="status-badge positive">稳定增长</span>
          </div>
          <div className="trend-chart" aria-label="业务趋势示意图">
            {[34, 48, 41, 63, 58, 76, 84].map((height, index) => (
              <span key={index} style={{ '--bar-height': `${height}%` }} />
            ))}
          </div>
          <div className="chart-axis"><span>周一</span><span>周三</span><span>周五</span><span>今日</span></div>
        </article>

        <article className="panel activity-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">PRIORITIES</span>
              <h3>今日重点</h3>
            </div>
          </div>
          <div className="activity-list">
            <div><span className="activity-mark danger" /><p><strong>风险事件待确认</strong><small>艺人舆情异常需复核</small></p></div>
            <div><span className="activity-mark warning" /><p><strong>项目即将开售</strong><small>上海站距开售还有 2 天</small></p></div>
            <div><span className="activity-mark success" /><p><strong>宣发任务已完成</strong><small>北京站素材已进入投放</small></p></div>
          </div>
        </article>
      </section>

      <section className="module-grid">
        {dashboard.modules.map((module) => {
          const content = (
            <>
              <span className="module-index" aria-hidden="true">0{dashboard.modules.indexOf(module) + 1}</span>
              <h3>{module.title}</h3>
              <p>{module.copy}</p>
              {module.to && <span className="module-link">进入模块 →</span>}
            </>
          )
          return module.to
            ? <Link className="module-card" key={module.title} to={module.to}>{content}</Link>
            : <article className="module-card" key={module.title}>{content}</article>
        })}
      </section>
    </div>
  )
}

function BusinessWorkbench() {
  const [projects, setProjects] = useState([])
  const [tasks, setTasks] = useState([])
  const [financeResults, setFinanceResults] = useState({})
  const [status, setStatus] = useState('loading')
  const [submitStatus, setSubmitStatus] = useState('idle')
  const [projectActionStatus, setProjectActionStatus] = useState({})
  const [message, setMessage] = useState('')
  const [form, setForm] = useState({
    name: '',
    artist_name: '',
    city: '',
    venue: '',
  })

  useEffect(() => {
    let active = true
    setStatus('loading')

    Promise.all([listProjects(), listTasks()])
      .then(([projectResponse, taskResponse]) => {
        if (!active) return
        setProjects(projectResponse.data.data || [])
        setTasks(taskResponse.data.data || [])
        setStatus('success')
      })
      .catch(() => {
        if (active) setStatus('error')
      })

    return () => {
      active = false
    }
  }, [])

  const handleFieldChange = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }))
  }

  const handleCreateProject = async (event) => {
    event.preventDefault()
    if (!form.name.trim()) {
      setMessage('请填写项目名称')
      return
    }

    setSubmitStatus('loading')
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
      setMessage('项目已创建，可继续补充财务测算参数。')
    } catch {
      setSubmitStatus('error')
      setMessage('项目创建失败，请稍后重试。')
    }
  }

  const formatNumber = (value) => new Intl.NumberFormat('zh-CN').format(value || 0)

  const handleCalculateFinance = async (project) => {
    setProjectActionStatus((current) => ({ ...current, [`finance-${project.id}`]: 'loading' }))
    setMessage('')
    try {
      const response = await calculateFinance({
        project_id: project.id,
        expected_attendance: project.expected_attendance,
        avg_ticket_price: project.avg_ticket_price,
        artist_fee: project.artist_fee,
        venue_cost: project.venue_cost,
        marketing_cost: project.marketing_cost,
        production_cost: project.production_cost,
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
      setMessage('财务测算失败，请补齐项目参数后重试。')
    }
  }

  const handleAdvanceDecision = async (project) => {
    const versionId = financeResults[project.id]?.version_id || project.current_version_id
    setProjectActionStatus((current) => ({ ...current, [`decision-${project.id}`]: 'loading' }))
    setMessage('')
    try {
      await createDecision({
        project_id: project.id,
        version_id: versionId,
        decision_type: 'advance',
        conditions: '完成政策审批、场地安全、艺人授权与资金合同确认后推进。',
      })
      setProjects((current) => current.map((item) => (
        item.id === project.id ? { ...item, status: 'pending_confirmation' } : item
      )))
      setProjectActionStatus((current) => ({ ...current, [`decision-${project.id}`]: 'success' }))
      setMessage('已提交推进决策')
    } catch {
      setProjectActionStatus((current) => ({ ...current, [`decision-${project.id}`]: 'error' }))
      setMessage('决策提交失败，请确认已有可用版本。')
    }
  }

  const activeProjects = projects.filter((project) => project.status !== 'archived').length
  const pendingTasks = tasks.filter((task) => task.status === 'pending').length
  const calculatedProjects = projects.filter((project) => project.status === 'calculated').length
  const decisionProjects = projects.filter((project) => project.status === 'pending_confirmation').length

  const metrics = [
    { label: '项目总数', value: String(projects.length), delta: `${activeProjects} 个仍在推进` },
    { label: '已测算项目', value: String(calculatedProjects), delta: '财务结果可复算留痕' },
    { label: '待决策项目', value: String(decisionProjects), delta: '需负责人确认版本' },
    { label: '待办任务', value: String(pendingTasks), delta: 'Agent / 人工任务池', tone: pendingTasks ? 'danger' : undefined },
  ]

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
              {projects.map((project) => (
                <span key={project.id}>
                  {project.name}
                  <strong>{project.status === 'calculated' ? '已测算' : project.status}</strong>
                  <small>{[project.artist_name, project.city, project.venue].filter(Boolean).join(' · ') || '基础信息待补充'}</small>
                  {financeResults[project.id]?.scenarios?.neutral && (
                    <small>
                      中性利润 ¥{formatNumber(financeResults[project.id].scenarios.neutral.profit)}
                    </small>
                  )}
                  {financeResults[project.id]?.breakeven_attendance && (
                    <small>保本人数 {formatNumber(financeResults[project.id].breakeven_attendance)}</small>
                  )}
                  <div className="inline-actions">
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
                </span>
              ))}
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">TASKS</span>
              <h3>待办任务</h3>
            </div>
          </div>

          {tasks.length === 0 ? (
            <div className="state-panel">暂无待办任务</div>
          ) : (
            <div className="activity-list">
              {tasks.map((task) => (
                <div key={task.id}>
                  <span className={`activity-mark ${task.status === 'pending' ? 'warning' : 'success'}`} />
                  <p>
                    <strong>{task.title}</strong>
                    <small>{task.due_date || '未设置截止时间'}</small>
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
        <form className="generator-form" onSubmit={handleCreateProject}>
          <div className="form-grid">
            <label className="field">
              <span>项目名称</span>
              <input value={form.name} onChange={(event) => handleFieldChange('name', event.target.value)} />
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
        {message && <div className={`inline-message ${submitStatus === 'success' ? 'success' : 'error'}`}>{message}</div>}
      </section>
    </div>
  )
}

export default function Home({ role = 'C' }) {
  const [shows, setShows] = useState([])
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    if (role !== 'C') {
      setStatus('idle')
      return
    }

    let active = true
    setStatus('loading')

    listShows()
      .then((response) => {
        if (!active) return
        setShows(response.data.data || [])
        setStatus('success')
      })
      .catch(() => {
        if (active) setStatus('error')
      })

    return () => {
      active = false
    }
  }, [role])

  if (role === 'B') {
    return <BusinessWorkbench />
  }

  if (role !== 'C') {
    return <RoleDashboard role={role} />
  }

  return (
    <div className="page-stack">
      <section className="page-lead">
        <div>
          <span className="eyebrow">LIVE DISCOVERY</span>
          <h2>发现值得到场的演出</h2>
          <p>根据热度、城市与偏好，快速找到下一场现场体验。</p>
        </div>
        <Link className="button button-primary" to="/generate">生成专属推荐</Link>
      </section>

      <section className="discovery-toolbar">
        <label className="search-field">
          <span className="sr-only">搜索演出或艺人</span>
          <input placeholder="搜索演出、艺人或城市" />
        </label>
        <div className="filter-group" aria-label="演出分类">
          <button className="filter-chip active" type="button">全部</button>
          <button className="filter-chip" type="button">演唱会</button>
          <button className="filter-chip" type="button">音乐节</button>
          <button className="filter-chip" type="button">近期</button>
        </div>
      </section>

      <section>
        <div className="section-heading">
          <div>
            <span className="eyebrow">RECOMMENDED</span>
            <h3>热门演出</h3>
          </div>
          <span className="section-count">{shows.length} 场可选</span>
        </div>

        {status === 'loading' && <div className="state-panel">正在加载演出数据...</div>}
        {status === 'error' && (
          <div className="state-panel error">
            <strong>演出数据暂时不可用</strong>
            <span>请确认后端服务已启动后刷新页面。</span>
          </div>
        )}
        {status === 'success' && shows.length === 0 && <div className="state-panel">暂无可展示的演出</div>}
        {status === 'success' && shows.length > 0 && (
          <div className="show-grid">
            {shows.map((show) => <ShowCard key={show.id} show={show} />)}
          </div>
        )}
      </section>
    </div>
  )
}
