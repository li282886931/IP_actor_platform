import { Link } from 'react-router-dom'
import { ended, statusText, useCollaboration } from '../pages/collaborationSupport'

export default function CollaborationInbox() {
  const { data, error, reload } = useCollaboration()
  const items = data?.items?.filter(i => i.actions?.length && !ended(i)) || []
  return <section className="panel collab-home-inbox">
    <div className="panel-heading"><h3>需要我处理的协作</h3><Link className="button button-secondary" to="/collaboration">处理协作事项</Link></div>
    {error ? <p className="role-muted">协作待办暂时不可用 <button className="agenda-expand" onClick={reload}>重试协作</button></p> : !data ? <p className="role-muted">正在加载协作待办…</p>
      : items.length ? items.slice(0, 4).map(i => <div className="workspace-compact-row" key={i.id}><div><strong>{i.title}</strong><small>{i.owner_name} → {i.recipient_name} · 截止 {i.payload?.due_date || '未设置'}{i.payload?.rejection_reason ? ` · 退回原因：${i.payload.rejection_reason}` : ''}</small></div><span className="status-badge">{statusText[i.status]}</span></div>)
        : <p className="role-muted">暂无待处理协作，可进入协作页面发起或查看历史记录。</p>}
  </section>
}
