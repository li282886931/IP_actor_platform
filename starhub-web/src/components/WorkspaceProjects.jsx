import { Link } from 'react-router-dom'
import { projectStatus } from '../pages/workspaceSupport'

export default function WorkspaceProjects({ projects = [], review = false, editable = false }) {
  if (!projects.length) return <div className="state-panel">当前条件下暂无项目</div>
  return <div className="role-review-list">{projects.map(p =>
    <details className="role-project-review" key={p.id}>
      <summary><div className="role-project-main"><strong>{p.name}</strong><small>{p.city || '城市待补齐'} · {p.artist_name || '艺人待补齐'} · {p.schedule || '档期待补齐'}</small></div>
        <span className="role-project-status">{projectStatus(p.status)}</span><span className="role-project-side">{p.evidence?.pending ?? 0} 份待核验</span><span className="role-review-toggle">展开材料</span></summary>
      <div className="role-review-content"><p>{p.venue || '场馆待补齐'}</p>
        <div className="role-review-columns"><section><h4>{review ? '安全与审批核验' : '项目关卡'}</h4>
          {(p.gates || []).length ? p.gates.map(g => <div className="role-check-item" key={g.id}><strong>{g.name}</strong><span>{g.status === 'passed' ? '系统关卡通过' : '待核验'}</span><p>{g.required_evidence || '核验材料待补齐'}</p></div>) : <p className="role-muted">尚无关卡记录，请补齐核验清单。</p>}</section>
          <section><h4>开放风险</h4>{(p.risks || []).filter(r => !['resolved', 'closed'].includes(r.status)).map(r => <div className="role-check-item" key={r.id}><strong>{r.title}</strong><p>{r.mitigation || '缓解措施待补齐'}</p></div>)}
            {!(p.risks || []).some(r => !['resolved', 'closed'].includes(r.status)) && <p className="role-muted">尚无开放风险记录，仍需人工核验。</p>}</section></div>
        <h4>资料与来源</h4>{(p.facts || []).length ? p.facts.map(f => <div className="workspace-compact-row" key={f.id}><div><strong>{f.title}</strong><small>{f.source || '来源待补齐'}</small></div><span>{f.status === 'verified' ? '已核验' : '待核验'}</span></div>) : <p className="role-muted">暂无事实材料</p>}
        {editable && <Link className="button button-secondary" to={`/projects/${p.id}`}>进入项目决策</Link>}
      </div>
    </details>)}</div>
}
