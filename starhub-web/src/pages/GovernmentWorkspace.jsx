import { useState } from 'react'
import { getGovernmentWorkspace } from '../api'
import PersonalInbox from '../components/PersonalInbox'
import WorkspaceProjects from '../components/WorkspaceProjects'
import { useWorkspace, WorkspaceState } from './workspaceSupport'

export default function GovernmentWorkspace({ mode = 'overview' }) {
  const workspace = useWorkspace(getGovernmentWorkspace)
  const [city, setCity] = useState('')
  if (workspace.status !== 'success') return <WorkspaceState {...workspace} />
  const { projects = [], venues = [], personal } = workspace.data || {}
  const cities = [...new Set([...projects, ...venues].map(p => p.city).filter(Boolean))].sort()
  const visible = projects.filter(p => !city || p.city === city)
  const localVenues = venues.filter(v => !city || v.city === city)
  return <div className="page-stack role-workspace">
    <section className="page-lead"><div><h2>{({ overview: '城市文旅工作台', projects: '城市项目', review: '审批与安全', impact: '文旅成效' })[mode]}</h2><p>当前空间的城市项目与材料核验。系统关卡状态不代替法定审批。</p></div>
      <label className="field"><span>选择城市</span><select aria-label="选择城市" value={city} onChange={e => setCity(e.target.value)}><option value="">全部城市</option>{cities.map(c => <option key={c}>{c}</option>)}</select></label></section>
    {mode === 'overview' && <PersonalInbox personal={personal} role="G" data={{ projects: visible }} />}
    <dl className="workspace-summary-strip"><div><dt>范围内项目</dt><dd>{visible.length} 个</dd></div><div><dt>资料库场馆</dt><dd>{localVenues.length} 个</dd></div><div><dt>未通过关卡</dt><dd>{visible.reduce((n, p) => n + (p.gates || []).filter(g => g.status !== 'passed').length, 0)} 项</dd></div></dl>
    {(mode === 'impact' || mode === 'overview') && <section className="panel city-impact-panel"><h3>成效数据核验</h3><p>项目覆盖来自当前空间记录。实际观众、跨城客流、消费金额及城市热度均待接入，不由预计人数推算。</p><p className="role-disclosure">统计需明确周期、地区、来源及人工核验结果。</p></section>}
    <section className="panel"><div className="panel-heading"><h3>{mode === 'review' ? '项目审批与安全材料' : '城市项目清单'}</h3><span className="section-count">{visible.length} 个</span></div><WorkspaceProjects projects={visible} review /></section>
    {(mode === 'review' || mode === 'overview') && <section className="panel"><h3>场馆安全资料</h3>{localVenues.length ? localVenues.map(v => <article className="workspace-compact-row" key={v.id}><div><strong>{v.name}</strong><small>{v.city} · {v.capacity == null ? '容量待补齐' : `${v.capacity} 人`} · {v.source || '来源待核验'}</small></div><span>{v.fire_safety_status === 'verified' ? '资料已核验' : '消防材料待核验'}</span></article>) : <p className="role-muted">暂无场馆资料</p>}<p className="role-disclosure">大型演出适用条件与审批要求应逐项目核验；平台不作审批或安全合规承诺。</p></section>}
  </div>
}
