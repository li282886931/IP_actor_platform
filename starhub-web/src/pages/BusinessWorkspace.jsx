import { Link } from 'react-router-dom'
import { getBusinessWorkspace } from '../api'
import PersonalInbox from '../components/PersonalInbox'
import WorkspaceProjects from '../components/WorkspaceProjects'
import { useWorkspace, WorkspaceState } from './workspaceSupport'

export default function BusinessWorkspace({ mode = 'overview' }) {
  const workspace = useWorkspace(getBusinessWorkspace)
  if (workspace.status !== 'success') return <WorkspaceState {...workspace} />
  const { projects = [], personal } = workspace.data || {}
  const unresolved = projects.reduce((n, p) => n + (p.gates || []).filter(g => g.status !== 'passed').length, 0)
  return <div className="page-stack role-workspace">
    <section className="page-lead"><div><h2>{mode === 'tasks' ? '执行待办' : '主办方经营工作台'}</h2><p>先核验落地条件，再推进项目、测算和执行。</p></div><Link className="button button-primary" to="/operations/projects">进入项目运营</Link></section>
    <PersonalInbox personal={personal} tasksOnly={mode === 'tasks'} role="B" data={workspace.data} />
    {mode === 'overview' && <><dl className="workspace-summary-strip"><div><dt>空间项目</dt><dd>{projects.length} 个</dd></div><div><dt>未通过关卡</dt><dd>{unresolved} 项</dd></div><div><dt>我的待办</dt><dd>{personal?.pending_tasks ?? 0} 项</dd></div></dl>
      <section className="panel"><div className="panel-heading"><h3>项目执行关注</h3><span className="section-count">当前空间共享项目</span></div><WorkspaceProjects projects={projects} editable /></section></>}
  </div>
}
