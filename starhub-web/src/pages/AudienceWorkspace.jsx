import { useState } from 'react'
import { Link } from 'react-router-dom'
import { getAudienceWorkspace } from '../api'
import PersonalInbox from '../components/PersonalInbox'
import ShowCard from '../components/ShowCard'
import { useWorkspace, WorkspaceState } from './workspaceSupport'

export default function AudienceWorkspace({ mode = 'overview' }) {
  const workspace = useWorkspace(getAudienceWorkspace)
  const [query, setQuery] = useState('')
  const [city, setCity] = useState('')
  if (workspace.status !== 'success') return <WorkspaceState {...workspace} />
  const { shows = [], reservations = [], personal } = workspace.data || {}
  const cities = [...new Set(shows.map(s => s.city).filter(Boolean))].sort()
  const visible = shows.filter(s => (!city || s.city === city) && `${s.title} ${s.city} ${s.artist_name}`.includes(query.trim()))
  return <div className="page-stack role-workspace audience-workspace">
    <section className="page-lead"><div><h2>{({ overview: '我的现场', discover: '演出发现', reservations: '我的预约' })[mode]}</h2><p>发现下一场演出，查看当前账号的预约登记。</p></div>
      {mode !== 'reservations' && <Link className="button button-secondary" to="/audience/reservations">查看我的预约 · {reservations.length}</Link>}</section>
    {mode === 'overview' && <PersonalInbox personal={personal} role="C" data={workspace.data} />}
    {mode !== 'reservations' && <section><div className="workspace-filters">
      <label className="field"><span>搜索演出、艺人或城市</span><input value={query} onChange={e => setQuery(e.target.value)} placeholder="输入演出、艺人或城市" /></label>
      <label className="field"><span>演出城市</span><select aria-label="演出城市" value={city} onChange={e => setCity(e.target.value)}><option value="">全部城市</option>{cities.map(c => <option key={c}>{c}</option>)}</select></label></div>
      <div className="section-heading"><h3>公开演出</h3><span className="section-count">{visible.length} 场</span></div>
      {visible.length ? <div className="show-grid">{visible.map(s => <ShowCard key={s.id} show={s} />)}</div> : <div className="state-panel">{shows.length ? '没有匹配的演出' : '暂无公开演出'}</div>}</section>}
    {mode !== 'discover' && <section className="panel"><div className="panel-heading"><h3>我的预约登记</h3><span className="section-count">{reservations.length} 条</span></div>
      {reservations.length ? reservations.map(r => <article className="workspace-compact-row" key={r.id}><div><strong>{r.show?.title || '演出信息暂不可用'}</strong><small>{r.show?.city || '城市待公布'} · {r.show?.date || '日期待公布'}</small><span className="status-badge">{r.status === 'cancelled' ? '已取消登记' : '已登记'}</span></div><div className="collab-actions">{r.show && <Link className="button button-secondary" to={`/show/${r.show.id}`}>查看演出</Link>}<Link className="button button-secondary" to="/collaboration">管理登记与查看历史</Link></div></article>) : <div className="state-panel">当前账号尚无预约登记</div>}
      <p className="role-disclosure">预约登记不代表购票、付款或入场凭证。历史未归属记录不会按手机号自动认领。</p></section>}
  </div>
}
