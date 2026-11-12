import { useState } from 'react'
import { Link } from 'react-router-dom'
import WorkspaceFlow from './WorkspaceFlow'
import CollaborationInbox from './CollaborationInbox'

const states = { pending: '待处理', in_progress: '执行中', submitted: '待验收', accepted: '已验收', completed: '已完成', rejected: '需补充', cancelled: '已取消' }
const ended = t => ['accepted', 'completed', 'cancelled'].includes(t.status)
const categories = [
  ['open', '未结束', t => !ended(t)],
  ['mine', '待我处理', t => ['pending', 'in_progress', 'rejected'].includes(t.status)],
  ['review', '待验收', t => t.status === 'submitted'],
  ['done', '已结束', ended],
  ['all', '全部', () => true],
]
const nextStep = task => task.status === 'submitted' && task.reviewer_name ? `等待${task.reviewer_name}验收` : ({
  pending: '确认任务要求并开始处理',
  in_progress: '完成执行并提交结果',
  rejected: '按退回原因补充材料',
  submitted: '等待验收，验收负责人待指定',
  accepted: '保留验收结果与凭证',
  completed: '保留完成记录与凭证',
  cancelled: '任务已取消，无需继续执行',
}[task.status] || '联系项目负责人确认任务状态')

export default function PersonalInbox({ personal = {}, tasksOnly = false, role, data = {} }) {
  const [filter, setFilter] = useState('open')
  const [expanded, setExpanded] = useState(false)
  const { tasks = [], notifications = [] } = personal
  const filtered = tasks.filter(categories.find(c => c[0] === filter)[2])
  const shown = expanded ? filtered : filtered.slice(0, 5)
  return <>
    <section className="panel personal-inbox">
      <div className="panel-heading"><h3>{tasksOnly ? '我的执行待办' : '我的待办与消息'}</h3><span className="section-count">当前账号 · 当前空间</span></div>
      <div className="agenda-filters" role="group" aria-label="筛选个人待办">{categories.map(([key, label, match]) =>
        <button key={key} aria-pressed={filter === key} onClick={() => { setFilter(key); setExpanded(false) }}>{label} · {tasks.filter(match).length}</button>)}</div>
      <div className={tasksOnly ? '' : 'agenda-inbox-columns'}>
        <div><h4>个人待办 · {filtered.length}</h4>{shown.map(t =>
          <article className="agenda-task" key={t.id}>
            <div className="workspace-compact-row"><div><strong>{t.title}</strong><small>{t.project_name || '关联项目待确认'} · {t.due_date ? `截止 ${t.due_date}` : '未设置截止日期'}</small></div>
              <span className="status-badge">{states[t.status] || '状态待确认'}</span></div>
            <p className="agenda-next">下一步：{nextStep(t)}</p>
            <p className="role-muted">负责人：{t.assignee_name || '当前账号'}{t.next_user_name ? ` · 下一处理人：${t.next_user_name}` : t.status === 'submitted' ? ' · 下一处理人：验收负责人待指定' : ''}</p>
            {t.collaboration_item_id && <div className="collab-actions"><Link className="button button-secondary" to="/collaboration">处理事项与查看历史</Link></div>}
            {t.rejection_reason && <p className="agenda-return">退回原因：{t.rejection_reason}</p>}
            {!!(t.description || t.result || t.evidence_count) && <details className="agenda-material"><summary>展开任务材料</summary>
              {t.description && <p>任务要求：{t.description}</p>}{t.result && <p>{t.result}</p>}
              {!!t.evidence_count && <p>关联证据：{t.evidence_count} 份</p>}</details>}
          </article>)}
          {!filtered.length && <p className="role-muted">{tasks.length ? '当前筛选下暂无待办' : '暂无分配给您的待办'}</p>}
          {filtered.length > 5 && <button className="agenda-expand" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>{expanded ? '收起待办' : `展开全部 ${filtered.length} 项待办`}</button>}
          <p className="role-disclosure">协作任务可进入事项页执行、提交与验收；未关联协作流程的历史任务请联系项目负责人。</p>
        </div>
      {!tasksOnly && <div className="agenda-notices"><h4>个人消息 · {notifications.length}</h4>{notifications.length ? notifications.map(n =>
        <article className="workspace-compact-row" key={n.id}><div><strong>{n.title}</strong>{n.content && <small>{n.content}</small>}</div>
          <span className="status-badge">{n.status === 'unread' ? '未读' : '已读'}</span></article>) : <p className="role-muted">暂无个人消息</p>}</div>}
      </div>
    </section>
    <CollaborationInbox />
    <WorkspaceFlow role={role} data={data} />
  </>
}
