import { useState } from 'react'
import { Link } from 'react-router-dom'
import { getInvestorWorkspace } from '../api'
import { WalletIcon, CheckSquareIcon, ClapperIcon } from '../components/icons'
import { money, projectStatus, useWorkspace, WorkspaceState } from './workspaceSupport'

const titles = { overview: '投资评估概览', projects: '项目评估', safeguards: '资金与风险' }
const isCalculated = project => project.version?.finance_result?.status === 'calculated'

function ProjectReview({ project, safeguards }) {
  const finance = isCalculated(project) ? project.version.finance_result : null
  const risks = (project.risks || []).filter(r => r.status !== 'resolved' && r.status !== 'closed')
  const gates = (project.gates || []).filter(g => g.status !== 'passed')
  return <details className="role-project-review">
    <summary>
      <div className="role-project-main"><strong>{project.name}</strong>
        <small>{project.city || '城市待补齐'} · {project.artist_name || '艺人待补齐'} · {project.schedule || '档期待补齐'}</small></div>
      <span className="role-project-status">{projectStatus(project.status)}</span>
      <span className="role-project-side">{finance ? `资金缺口 ${money(finance.funding_gap)}` : '测算待补齐'}</span>
      <span className="role-review-toggle">查看详情</span>
    </summary>
    <div className="role-review-content">
      {!safeguards && <><h4>{project.version ? `当前版本 V${project.version.version_no}` : '尚未保存测算版本'}</h4>
        {finance ? <dl className="role-value-grid">
          <div><dt>项目总成本</dt><dd>{money(finance.total_cost)}</dd></div>
          <div><dt>预计总收入</dt><dd>{money(finance.total_revenue)}</dd></div>
          <div><dt>项目净利润</dt><dd>{money(finance.net_profit)}</dd></div>
          <div><dt>项目成本回报率</dt><dd>{typeof finance.roi === 'number' ? `${(finance.roi * 100).toFixed(2)}%` : '待补齐'}</dd></div>
        </dl> : <p className="role-muted">请由主办方补齐参数并保存完整测算。当前无法评估项目回报。</p>}</>}
      <dl className="role-value-grid">
        <div><dt>可用资金</dt><dd>{money(finance?.available_funds)}</dd></div>
        <div><dt>资金缺口</dt><dd>{money(finance?.funding_gap)}</dd></div>
        <div><dt>待核验证据</dt><dd>{project.evidence?.pending ?? 0} / {project.evidence?.total ?? 0} 份</dd></div>
      </dl>
      <div className="role-review-columns">
        <section><h4>开放风险 · {risks.length}</h4>{risks.length ? risks.map(risk =>
          <div className="role-check-item" key={risk.id}><strong>{risk.title}</strong>
            <span>{({ high: '高风险', medium: '中风险', low: '低风险' })[risk.level] || '级别待确认'}</span>
            <p>{risk.mitigation || '缓解措施待补齐'}</p></div>) : <p className="role-muted">尚无开放风险记录，仍需人工核验。</p>}</section>
        <section><h4>未通过关卡 · {gates.length}</h4>{gates.length ? gates.map(gate =>
          <div className="role-check-item" key={gate.id}><strong>{gate.name}</strong>
            <p>{gate.required_evidence || '核验材料待补齐'}</p></div>) : <p className="role-muted">尚无未通过关卡记录。</p>}</section>
      </div>
    </div>
  </details>
}

export default function InvestorWorkspace({ mode = 'overview' }) {
  const workspace = useWorkspace(getInvestorWorkspace)
  const [query, setQuery] = useState('')
  if (workspace.status !== 'success') return <WorkspaceState {...workspace} />
  const projects = workspace.data?.projects || []
  const calculated = projects.filter(isCalculated)
  const openRisks = projects.reduce((n, p) => n + (p.risks || []).filter(r => !['resolved', 'closed'].includes(r.status)).length, 0)
  const visible = projects.filter(p => `${p.name} ${p.city} ${p.artist_name}`.toLowerCase().includes(query.trim().toLowerCase()))
  return <div className="page-stack role-workspace">
    <section className="page-lead"><div><h2>{titles[mode]}</h2>
      <p>围绕项目当前版本核验成本、资金与风险，支持投资前评估。</p></div>
      {mode === 'overview' && <Link className="button button-secondary" to="/investment/projects">查看全部项目</Link>}
    </section>
    {mode === 'overview' && <div className="role-stat-strip">
      <div><ClapperIcon /><span>空间项目<strong>{projects.length} 个</strong></span></div>
      <div><WalletIcon /><span>已保存完整测算<strong>{calculated.length} 个</strong></span></div>
      <div><CheckSquareIcon /><span>开放风险<strong>{openRisks} 项</strong></span></div>
    </div>}
    <section className="panel">
      <div className="panel-heading"><h3>{mode === 'safeguards' ? '资金与材料核验' : '项目清单'}</h3><span className="section-count">{visible.length} 个项目</span></div>
      <label className="field role-search"><span>搜索项目或城市</span><input value={query} onChange={e => setQuery(e.target.value)} placeholder="项目名称、城市或艺人" /></label>
      {!projects.length ? <div className="state-panel">当前空间暂无项目</div> : !visible.length ? <div className="state-panel">没有匹配的项目</div> :
        <div className="role-review-list">{visible.map(project => <ProjectReview key={project.id} project={project} safeguards={mode === 'safeguards'} />)}</div>}
    </section>
    <p className="role-disclosure">项目成本回报率来自已保存测算，不代表合同投资收益。资金缺口为零仍需核验资金监管、合同保障与付款节点。</p>
  </div>
}
