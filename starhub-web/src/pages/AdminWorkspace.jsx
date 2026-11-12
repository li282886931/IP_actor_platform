import { Link } from 'react-router-dom'
import { getAdminWorkspace } from '../api'
import PersonalInbox from '../components/PersonalInbox'
import { useWorkspace, WorkspaceState } from './workspaceSupport'

export default function AdminWorkspace({ mode = 'overview' }) {
  const workspace = useWorkspace(getAdminWorkspace)
  if (workspace.status !== 'success') return <WorkspaceState {...workspace} />
  const { summary = {}, sources = [], jobs = [], personal } = workspace.data || {}
  const recentJobs = mode === 'overview' ? jobs.slice(0, 5) : jobs.slice(0, 20)
  const states = { configured: '已配置', healthy: '连接正常', active: '启用', failed: '失败', queued: '排队中', running: '执行中', completed: '已完成', disabled: '停用', error: '异常' }
  return <div className="page-stack role-workspace">
    <section className="page-lead"><div><h2>{mode === 'data' ? '数据接入与质量' : '平台管理工作台'}</h2><p>查看当前空间的账号权限、接入状态和数据质量。</p></div><Link className="button button-secondary" to="/users">管理用户</Link></section>
    {mode === 'overview' && <PersonalInbox personal={personal} role="Admin" data={workspace.data} />}
    <dl className="workspace-summary-strip">
      <div><dt>空间成员</dt><dd>{summary.users ?? 0} 人</dd></div><div><dt>空间项目</dt><dd>{summary.projects ?? 0} 个</dd></div>
      <div><dt>已配置数据源</dt><dd>{summary.sources ?? 0} 个</dd></div><div><dt>开放质量问题</dt><dd>{summary.quality_issues ?? 0} 项</dd></div>
    </dl>
    <section className="panel"><div className="panel-heading"><h3>数据源状态</h3><span className="section-count">{sources.length} 个</span></div>
      {sources.length ? sources.map(s => <article className="workspace-compact-row" key={s.id}><div><strong>{s.name}</strong><small>{s.source_kind || '类型待确认'}</small></div><span className="status-badge">{states[s.status] || '状态待确认'}</span></article>) : <div className="state-panel">当前空间尚未配置数据源</div>}
      <p className="role-disclosure">配置记录不等于接入成功，数据可用性需结合任务结果与质量核验。</p></section>
    <section className="panel"><div className="panel-heading"><h3>近期采集任务</h3><span className="section-count">共 {jobs.length} 项 · 展示最近 {recentJobs.length} 项</span></div>
      {recentJobs.length ? recentJobs.map(j => <article className="workspace-compact-row" key={j.id}><div><strong>{j.purpose || `采集任务 ${j.id}`}</strong><small>{j.provider}</small></div><span>{states[j.status] || '状态待确认'}</span></article>) : <p className="role-muted">暂无采集任务</p>}
      {mode === 'overview' && <Link className="button button-secondary" to="/admin/data">查看接入详情</Link>}</section>
  </div>
}
