import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getCollaborationHistory } from '../collaborationApi'
import { actionText, ended, focusScore, formValues, kinds, PayloadFields, payloadFor, roleKinds, statusText, StructuredValues, targets, titles, useCollaboration } from './collaborationSupport'
import { roleMeta } from '../roleConfig'
import { money } from './workspaceSupport'

function History({ path }) {
  const [rows, setRows] = useState(null), [error, setError] = useState('')
  async function load() {
    try { setRows((await getCollaborationHistory(path)).data.data); setError('') }
    catch { setError('历史加载失败，请重试') }
  }
  return <details className="collab-history" onToggle={e => { if (e.currentTarget.open && rows === null) load() }}>
    <summary>操作历史与修改对照</summary>
    {error && <p role="alert">{error} <button onClick={load}>重试历史</button></p>}
    {rows?.map(h => <article key={h.id}><p>{h.created_at} · 操作人 #{h.actor_id} · {actionText[h.action] || h.action}</p>
      <div className="collab-history-columns"><div><strong>修改前</strong><StructuredValues value={h.before} /></div><div><strong>修改后</strong><StructuredValues value={h.after} /></div></div></article>)}
    {rows?.length === 0 && <p>暂无历史记录</p>}
  </details>
}

function ItemRow({ item, controller, data }) {
  const [note, setNote] = useState(''), [proof, setProof] = useState(''), [editing, setEditing] = useState(false), [values, setValues] = useState({})
  const { mutate, busy, setError } = controller
  const actions = item.actions || []
  const project = data.projects.find(p => p.id === item.project_id)
  const next = data.members.find(m => m.id === item.next_user_id)
  const nextNames = item.next_user_ids?.map(id => data.members.find(m => m.id === id)?.name).filter(Boolean).join('、')
  async function action(name) {
    if (['return', 'dispute', 'decline', 'reply', 'submit', 'deliver'].includes(name) && !note.trim()) {
      setError('请填写处理说明，退回时说明待补材料'); return
    }
    try {
      const payload = proof.trim() && ['reply', 'submit', 'deliver', 'approve'].includes(name) ? payloadFor('task', { evidence_ids: proof }) : null
      if (await mutate(`items/${item.id}/actions`, { action: name, revision: item.revision, note, ...(payload ? { payload } : {}) })) { setNote(current => current === note ? '' : current); setProof(current => current === proof ? '' : current) }
    } catch (e) { setError(e.message) }
  }
  async function edit(e) {
    e.preventDefault()
    try {
      if (await mutate(`items/${item.id}/actions`, { action: 'edit', revision: item.revision, payload: payloadFor(item.kind, values) })) setEditing(false)
    } catch (e) { setError(e.message) }
  }
  return <article className="collab-item">
    <div className="workspace-compact-row"><div><strong>{item.title}</strong><small>{kinds[item.kind]} · {project?.name || '个人资料'} · {item.version_id ? `引用版本 #${item.version_id}` : '未引用测算版本'}</small></div><span className="status-badge">{statusText[item.status] || '待确认'}</span></div>
    <p className="agenda-next">发起人：{item.owner_name || '待确认'} · 处理人：{item.recipient_name || '待确认'} · 下一处理人：{ended(item) ? '流程已结束' : nextNames || next?.name || '暂无待执行动作'}</p>
    <p className="role-muted">截止：{item.payload?.due_date || '未设置'} · 修订 {item.revision}</p>
    {item.version_changed && <p className="agenda-return">项目版本已变化，请比较当前版本后复核原意见。</p>}
    {item.availability_conflict && <p className="agenda-return">邀请时间与艺人已登记档期冲突，请重新协商。</p>}
    {(item.rejection_reason || item.payload?.rejection_reason) && <p className="agenda-return">退回原因：{item.rejection_reason || item.payload.rejection_reason}</p>}
    <details className="agenda-material"><summary>事项要求、材料与结果</summary><StructuredValues value={item.payload} />{item.result && <p>处理结果：{item.result}</p>}</details>
    {editing ? <form onSubmit={edit} className="collab-editor">
      <p className="role-muted">修改后重新保存为私有草稿；权益修改须重新发送并由双方确认。</p>
      <PayloadFields kind={item.kind} values={values} prefix={`${item.title} · `} onChange={(k, v) => setValues(old => ({ ...old, [k]: v }))} />
      <div className="collab-actions"><button className="button button-primary" disabled={busy}>保存修改</button><button type="button" className="button button-secondary" onClick={() => setEditing(false)}>取消修改</button></div>
    </form> : !!actions.length && <div className="collab-editor">
      {actions.some(a => ['reply', 'decline', 'deliver', 'approve', 'return', 'dispute', 'submit'].includes(a)) && <label><span>处理说明 / 结果 / 待补材料</span><textarea disabled={busy} aria-label={`处理说明 · ${item.title}`} rows={2} value={note} onChange={e => setNote(e.target.value)} /></label>}
      {item.project_id && actions.some(a => ['reply', 'submit', 'deliver', 'approve'].includes(a)) && <label><span>补交证明材料编号（权益验收必填，须属于当前项目）</span><input disabled={busy} aria-label={`补交证明材料编号 · ${item.title}`} value={proof} onChange={e => setProof(e.target.value)} /></label>}
      <div className="collab-actions">{actions.map(a => <button key={a} className={`button ${['share', 'approve', 'confirm', 'submit'].includes(a) ? 'button-primary' : 'button-secondary'}`} disabled={busy} onClick={() => a === 'edit' ? (setValues(formValues(item.kind, item.payload)), setEditing(true)) : action(a)}>{actionText[a]}</button>)}</div>
    </div>}
    <History path={`items/${item.id}`} />
  </article>
}

function CreateItem({ role, data, currentUser, controller }) {
  const allowed = roleKinds[role] || []
  const [kind, setKind] = useState(allowed[0]), [title, setTitle] = useState(''), [projectId, setProjectId] = useState(''), [recipient, setRecipient] = useState(''), [versionId, setVersionId] = useState(''), [values, setValues] = useState({}), [saved, setSaved] = useState(false)
  if (!allowed.length) return null
  const projects = [...data.projects].sort((a, b) => focusScore(b, data.focus) - focusScore(a, data.focus))
  const project = projects.find(p => p.id === Number(projectId))
  const members = data.members.filter(m => m.id !== currentUser?.id && targets[kind].includes(m.group_code) && (kind !== 'rights' || m.group_code !== (role === 'Admin' ? 'root' : role)))
  async function submit(e) {
    e.preventDefault(); setSaved(false)
    try {
      const body = { kind, title, recipient_id: Number(recipient), payload: payloadFor(kind, values) }
      if (kind !== 'profile_change') body.project_id = Number(projectId)
      if (kind === 'invitation') body.version_id = project.current_version_id
      if (kind === 'investment') body.version_id = Number(versionId)
      if (await controller.mutate('items', body)) { setTitle(''); setValues({}); setSaved(true) }
    } catch (error) { controller.setError(error.message) }
  }
  return <section className="panel">
    <div className="panel-heading"><h3>发起协作</h3><span className="section-count">草稿仅自己可见</span></div>
    <form onSubmit={submit}>
      <div className="collab-form-grid">
        <label><span>事项类型</span><select aria-label="事项类型" value={kind} onChange={e => { setKind(e.target.value); setValues({}); setRecipient(''); setSaved(false) }}>{allowed.map(k => <option key={k} value={k}>{kinds[k]}</option>)}</select></label>
        <label><span>事项标题</span><input aria-label="事项标题" required maxLength={255} value={title} onChange={e => setTitle(e.target.value)} /></label>
        {kind !== 'profile_change' && <label><span>授权项目</span><select aria-label="授权项目" required value={projectId} onChange={e => { setProjectId(e.target.value); setVersionId('') }}><option value="">请选择项目</option>{projects.map(p => <option key={p.id} value={p.id}>{p.name} · {p.city}</option>)}</select></label>}
        <label><span>处理人</span><select aria-label="处理人" required value={recipient} onChange={e => setRecipient(e.target.value)}><option value="">请选择处理人</option>{members.map(m => <option key={m.id} value={m.id}>{m.name} · {roleMeta[m.group_code === 'root' ? 'Admin' : m.group_code]?.label}</option>)}</select></label>
        {kind === 'investment' && <label><span>引用测算版本</span><select aria-label="引用测算版本" required value={versionId} onChange={e => setVersionId(e.target.value)}><option value="">请选择版本</option>{project?.versions?.map(v => <option key={v.id} value={v.id}>V{v.version_no}{v.id === project.current_version_id ? ' · 当前版本' : ' · 历史版本'}</option>)}</select></label>}
      </div>
      {kind === 'invitation' && <p className="role-muted">邀请引用当前已保存版本：{project?.current_version_id ? `#${project.current_version_id}` : '请先保存测算版本'}。选填邀请时间可检查档期冲突。</p>}
      {kind === 'incident' && <p className="role-muted">可分派来源：{data.incidents?.length ? data.incidents.map(i => `${i.source_type === 'job' ? '采集失败' : '质量问题'} #${i.source_id}`).join('、') : '暂无失败或开放异常来源'}</p>}
      <PayloadFields kind={kind} values={values} onChange={(k, v) => setValues(old => ({ ...old, [k]: v }))} />
      <p className="role-disclosure">选择的双方均须具备项目职责授权。保存后请在事项列表发送；来源登记、意见与权益确认仍需人工核验。</p>
      <button className="button button-primary" disabled={controller.busy || (kind !== 'profile_change' && !projects.length) || (kind === 'invitation' && !project?.current_version_id)}>保存草稿</button>
      {saved && <p role="status">草稿已保存，请在事项列表确认并发送。</p>}
    </form>
  </section>
}

function AdminControls({ data, controller }) {
  const [project, setProject] = useState(''), [user, setUser] = useState(''), [duties, setDuties] = useState(['collaborate']), [artistUser, setArtistUser] = useState(''), [artist, setArtist] = useState(''), [show, setShow] = useState('')
  const grant = data.grants?.find(g => g.project_id === Number(project) && g.user_id === Number(user))
  useEffect(() => { setDuties(grant?.duties || ['collaborate']) }, [project, user, grant?.revision])
  const internal = data.members.filter(m => m.group_code !== 'C')
  return <section className="panel">
    <h3>项目授权与身份绑定</h3>
    <form onSubmit={e => { e.preventDefault(); controller.mutate('grants', { project_id: Number(project), user_id: Number(user), duties, ...(grant ? { revision: grant.revision } : {}) }) }}>
      <div className="collab-form-grid"><label><span>管理项目</span><select required aria-label="管理项目" value={project} onChange={e => setProject(e.target.value)}><option value="">请选择</option>{data.projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
        <label><span>授权账号</span><select required aria-label="授权账号" value={user} onChange={e => setUser(e.target.value)}><option value="">请选择</option>{internal.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}</select></label></div>
      <fieldset className="collab-checks"><legend>项目职责</legend>{[['collaborate', '参与协作'], ['finance', '财务与版本'], ['manage', '管理演出']].map(([key, text]) => <label key={key}><input type="checkbox" checked={duties.includes(key)} onChange={e => setDuties(d => e.target.checked ? [...d, key] : d.filter(v => v !== key))} />{text}</label>)}</fieldset>
      <button className="button button-primary" disabled={controller.busy || !duties.length}>保存项目授权</button>
    </form>
    {data.grants?.map(g => <div className="workspace-compact-row" key={g.id}><div><strong>{data.projects.find(p => p.id === g.project_id)?.name} · {data.members.find(m => m.id === g.user_id)?.name}</strong><small>{g.duties.map(d => ({ collaborate: '协作', finance: '财务', manage: '管理' })[d]).join('、')} · {g.status === 'active' ? '有效' : '已撤销'}</small></div>{g.status === 'active' && <button className="button button-secondary" disabled={controller.busy} onClick={() => controller.mutate(`grants/${g.id}/revoke`, { revision: g.revision })}>撤销授权</button>}</div>)}
    <form className="collab-editor" onSubmit={e => { e.preventDefault(); controller.mutate('artist-binding', { user_id: Number(artistUser), artist_id: Number(artist) }) }}>
      <h4>艺人身份绑定</h4><div className="collab-form-grid">
        <label><span>艺人账号</span><select required aria-label="艺人账号" value={artistUser} onChange={e => setArtistUser(e.target.value)}><option value="">请选择</option>{data.members.filter(m => m.group_code === 'Artist').map(m => <option key={m.id} value={m.id}>{m.name}{m.artist_id ? ` · 已绑定 #${m.artist_id}` : ' · 未绑定'}</option>)}</select></label>
        <label><span>艺人资料</span><select required aria-label="艺人资料" value={artist} onChange={e => setArtist(e.target.value)}><option value="">请选择</option>{data.artists?.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}</select></label></div>
      <button className="button button-secondary" disabled={controller.busy}>保存身份绑定</button>
    </form>
    <form className="collab-editor" onSubmit={e => { e.preventDefault(); controller.mutate('show-binding', { project_id: Number(project), show_id: Number(show), confirmed: true, changes: {} }) }}>
      <h4>公开演出与管理项目绑定</h4><p className="role-muted">使用上方管理项目；项目艺人和城市须与公开演出一致。</p>
      <label><span>公开演出</span><select required aria-label="公开演出" value={show} onChange={e => setShow(e.target.value)}><option value="">请选择</option>{data.shows?.map(s => <option key={s.id} value={s.id}>{s.title}</option>)}</select></label>
      <button className="button button-secondary" disabled={controller.busy || !project}>绑定公开演出</button>
    </form>
    <details className="collab-history"><summary>授权与绑定审计</summary>{data.audit?.map(h => <p key={h.id}>{h.created_at} · 账号 #{h.actor_id} · {h.action} · 记录 #{h.subject_id}</p>)}</details>
  </section>
}

function VersionCompare({ projects }) {
  const [projectId, setProjectId] = useState(''), [left, setLeft] = useState(''), [right, setRight] = useState('')
  const project = projects.find(p => p.id === Number(projectId))
  const versions = project?.versions || []
  return <section className="panel"><h3>真实测算版本对照</h3><div className="collab-form-grid">
    <label><span>对照项目</span><select aria-label="对照项目" value={projectId} onChange={e => { setProjectId(e.target.value); setLeft(''); setRight('') }}><option value="">请选择</option>{projects.filter(p => p.versions).map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
    {[['版本一', left, setLeft], ['版本二', right, setRight]].map(([label, value, setter]) => <label key={label}><span>{label}</span><select aria-label={label} value={value} onChange={e => setter(e.target.value)}><option value="">请选择</option>{versions.map(v => <option key={v.id} value={v.id}>V{v.version_no}</option>)}</select></label>)}
  </div><div className="collab-history-columns">{[left, right].map((id, index) => {
    const version = versions.find(v => v.id === Number(id)), result = version?.finance_result
    return <div key={index}>{version && <><h4>V{version.version_no} · #{version.id}</h4>{result?.status === 'calculated' ? <dl className="collab-values">{[['total_cost', '总成本'], ['total_revenue', '总收入'], ['net_profit', '净利润'], ['funding_gap', '资金缺口']].map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{money(result[key])}</dd></div>)}<div><dt>回报率</dt><dd>{typeof result.roi === 'number' ? `${(result.roi * 100).toFixed(2)}%` : '待补齐'}</dd></div></dl> : <p className="role-muted">当前版本未完成测算，无法评估回报。</p>}<details><summary>原始参数与结果</summary><StructuredValues value={version.input_snapshot} /><StructuredValues value={result} /></details></>}</div>
  })}</div></section>
}

function AudienceRecords({ data, controller }) {
  const [type, setType] = useState('show'), [target, setTarget] = useState('')
  const favorites = data.personal.filter(r => r.type === 'favorite')
  const options = type === 'show' ? data.shows?.map(s => [String(s.id), s.title]) : type === 'artist' ? data.artists?.map(a => [String(a.id), a.name]) : [...new Set(data.shows?.map(s => s.city).filter(Boolean))].map(city => [city, city])
  const label = r => r.payload.target_type === 'city' ? r.payload.target_id : r.payload.target_type === 'show' ? data.shows?.find(s => String(s.id) === r.payload.target_id)?.title : data.artists?.find(a => String(a.id) === r.payload.target_id)?.name
  return <section className="panel"><h3>我的收藏与预约登记</h3>
    <form onSubmit={e => { e.preventDefault(); const key = `${type}:${target}`, row = favorites.find(r => r.record_key === key); controller.mutate('personal', { type: 'favorite', record_key: key, payload: { target_type: type, target_id: target }, ...(row ? { revision: row.revision } : {}) }) }}><div className="collab-form-grid">
      <label><span>收藏类型</span><select value={type} aria-label="收藏类型" onChange={e => { setType(e.target.value); setTarget('') }}><option value="show">演出</option><option value="artist">艺人</option><option value="city">城市</option></select></label>
      <label><span>收藏对象</span><select value={target} required aria-label="收藏对象" onChange={e => setTarget(e.target.value)}><option value="">请选择</option>{options?.map(([id, title]) => <option key={id} value={id}>{title}</option>)}</select></label></div><button className="button button-primary" disabled={controller.busy}>添加收藏</button></form>
    {favorites.map(r => <div className="workspace-compact-row" key={r.id}><strong>{label(r) || '对象信息待确认'}</strong><button className="button button-secondary" disabled={controller.busy} onClick={() => controller.mutate('personal', { type: 'favorite', record_key: r.record_key, revision: r.revision, remove: true })}>取消收藏</button></div>)}
    {!favorites.length && <p className="role-muted">暂无收藏</p>}
    <h4>预约登记</h4>{data.reservations.map(r => <article className="collab-item" key={r.id}><div className="workspace-compact-row"><div><strong>{data.shows?.find(s => s.id === r.show_id)?.title || `演出 #${r.show_id}`}</strong><small>{r.status === 'cancelled' ? '已取消登记' : '已登记'} · 预约 #{r.id}</small></div><button className="button button-secondary" disabled={controller.busy} onClick={() => controller.mutate('reservations', { order_id: r.id, action: r.status === 'cancelled' ? 'restore' : 'cancel' })}>{r.status === 'cancelled' ? '恢复登记' : '取消登记'}</button></div><History path={`reservations/${r.id}`} /></article>)}
    {!data.reservations.length && <p className="role-muted">暂无预约，请前往演出发现登记。</p>}
    <Link className="button button-secondary" to="/audience/discover">发现演出</Link><p className="role-disclosure">预约登记不代表已购票。购票、支付与核销待接入。</p>
  </section>
}

function ShowChanges({ data, controller }) {
  const [showId, setShowId] = useState(''), [key, setKey] = useState('date'), [value, setValue] = useState(''), [confirmed, setConfirmed] = useState(false)
  const show = data.managed_shows?.find(s => s.id === Number(showId))
  return <section className="panel"><h3>发布已确认的演出变化</h3><form onSubmit={e => { e.preventDefault(); controller.mutate('shows/update', { show_id: show.id, project_id: show.project_id, confirmed, changes: { [key]: value } }) }}>
    <div className="collab-form-grid"><label><span>已绑定演出</span><select aria-label="已绑定演出" required value={showId} onChange={e => setShowId(e.target.value)}><option value="">请选择</option>{data.managed_shows?.map(s => <option key={s.id} value={s.id}>{s.title}</option>)}</select></label>
      <label><span>变更字段</span><select value={key} aria-label="变更字段" onChange={e => { setKey(e.target.value); setValue('') }}>{[['date', '演出时间'], ['venue', '场馆'], ['price', '票价说明'], ['status', '演出状态'], ['description', '演出说明']].map(([key, text]) => <option key={key} value={key}>{text}</option>)}</select></label>
      <label><span>确认后的新内容</span>{key === 'status' ? <select aria-label="确认后的新内容" required value={value} onChange={e => setValue(e.target.value)}><option value="">请选择</option>{[['on_sale', '售票中'], ['scheduled', '已排期'], ['cancelled', '已取消'], ['ended', '已结束']].map(([v, text]) => <option key={v} value={v}>{text}</option>)}</select> : <input aria-label="确认后的新内容" required value={value} onChange={e => setValue(e.target.value)} />}</label></div>
    <label className="collab-checks"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />我已核验此变化，可以通知已登记观众</label>
    <button className="button button-primary" disabled={controller.busy || !show || !confirmed}>发布变化并通知</button></form>
    {!data.managed_shows?.length && <p className="role-muted">暂无具备管理权限的绑定演出，请先完成项目授权与演出绑定。</p>}
  </section>
}

export default function CollaborationWorkspace({ role, currentUser }) {
  const controller = useCollaboration(), [filter, setFilter] = useState('mine'), [search, setSearch] = useState('')
  const { data, error, busy, reload } = controller
  const items = (data?.items || []).filter(row => (filter === 'all' || (filter === 'ended' ? ended(row) : filter === 'draft' ? row.status === 'draft' : row.actions?.length && !ended(row))) && (!search || row.title.includes(search)))
    .sort((a, b) => focusScore({ ...data.projects.find(p => p.id === b.project_id), goal: b.payload?.goal }, data.focus) - focusScore({ ...data.projects.find(p => p.id === a.project_id), goal: a.payload?.goal }, data.focus))
  return <div className="role-workspace collaboration-workspace">
    <div className="page-lead"><div><h1>{titles[role]}</h1><p>按当前账号、空间与项目授权协作；关注设置影响排序。</p></div><Link className="button button-secondary" to="/preferences">个人关注与档期</Link></div>
    {error && <div className="state-panel error" role="alert">{String(error)} <button className="button button-secondary" disabled={busy} onClick={reload}>刷新记录</button></div>}
    {!data ? <p role="status">正在加载协作记录…</p> : <>
      {role === 'C' ? <AudienceRecords data={data} controller={controller} /> : <>
        <section className="panel"><div className="panel-heading"><h3>协作待办与当前流程</h3><button className="button button-secondary" disabled={busy} onClick={reload}>刷新</button></div>
          <div className="collab-toolbar"><div className="agenda-filters">{[['mine', '待我处理'], ['draft', '我的草稿'], ['ended', '已结束'], ['all', '全部事项']].map(([key, text]) => <button key={key} aria-pressed={filter === key} onClick={() => setFilter(key)}>{text}</button>)}</div><input aria-label="搜索协作事项" placeholder="搜索事项标题" value={search} onChange={e => setSearch(e.target.value)} /></div>
          <p className="role-disclosure">发起 → 发送 → 处理或补充 → 提交 → 验收。权益须双方确认；来源结果须人工核验。</p>
          {items.map(item => <ItemRow key={item.id} item={item} data={data} controller={controller} />)}
          {!items.length && <p className="role-muted">当前筛选下暂无协作事项；可发起草稿或联系管理员补齐授权。</p>}
        </section>
        <CreateItem role={role} data={data} currentUser={currentUser} controller={controller} />
        {role === 'Admin' && <AdminControls data={data} controller={controller} />}
        {['B', 'Investor'].includes(role) && <VersionCompare projects={data.projects} />}
        {['B', 'Admin'].includes(role) && <ShowChanges data={data} controller={controller} />}
      </>}
      <section className="panel"><h3>我的变化消息</h3>{data.notifications.map(n => <article className="workspace-compact-row" key={n.id}><div><strong>{n.title}</strong><small>{n.content}</small></div>{n.status === 'unread' ? <button className="button button-secondary" disabled={busy} onClick={() => controller.mutate(`notifications/${n.id}/read`, {})}>标记已读</button> : <span className="status-badge">已读</span>}</article>)}{!data.notifications.length && <p className="role-muted">暂无变化消息</p>}</section>
      <p className="role-disclosure">本页记录平台内部协作。外部审批自动查询、合同签署、支付与结算尚未接入，内部确认不构成法定许可、合同或到账证明。</p>
    </>}
  </div>
}
