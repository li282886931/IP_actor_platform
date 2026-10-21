import { Link } from 'react-router-dom'

import Avatar from './Avatar'

const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

// 宽松解析 due_date（YYYY-MM-DD / YYYY/MM/DD / 带时间），无法解析返回 null
export function parseDueDate(value) {
  if (!value) return null
  const text = String(value).trim()
  const match = text.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})/)
  if (!match) return null
  const year = Number(match[1])
  const month = Number(match[2]) - 1
  const day = Number(match[3])
  if (!month || month > 11 || day < 1 || day > 31) return null
  return new Date(year, month, day)
}

function startOfToday() {
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth(), now.getDate())
}

const dayDiff = (date, today) => Math.round((date.getTime() - today.getTime()) / 86400000)

// 参考图「今日日程」：日期块 + 状态色点 + 任务标题 + 项目 + 截止日期
export function buildSchedule(tasks) {
  const today = startOfToday()
  const groups = { overdue: [], today: [], tomorrow: [], week: [], unscheduled: [] }
  for (const task of tasks) {
    if (task.status === 'completed') continue
    const due = parseDueDate(task.due_date)
    if (!due) {
      groups.unscheduled.push({ task, due: null })
      continue
    }
    const diff = dayDiff(due, today)
    if (diff < 0) groups.overdue.push({ task, due, diff })
    else if (diff === 0) groups.today.push({ task, due, diff })
    else if (diff === 1) groups.tomorrow.push({ task, due, diff })
    else if (diff <= 7) groups.week.push({ task, due, diff })
    else groups.unscheduled.push({ task, due, diff })
  }
  const order = [
    { key: 'overdue', label: '已逾期', tone: 'danger' },
    { key: 'today', label: '今日日程', tone: 'gold' },
    { key: 'tomorrow', label: '明日', tone: 'amber' },
    { key: 'week', label: '本周内', tone: 'muted' },
  ]
  return order
    .map((group) => ({ ...group, items: groups[group.key] }))
    .filter((group) => group.items.length > 0)
}

function ScheduleRow({ entry, projectName }) {
  const { task, due, diff } = entry
  const tone = diff < 0 ? 'dot-danger' : diff === 0 ? 'dot-gold' : diff === 1 ? 'dot-amber' : 'dot-muted'
  return (
    <div className="schedule-row">
      {due ? (
        <div className="schedule-date">
          <span className="schedule-date-day">{due.getDate()}</span>
          <span className="schedule-date-week">{WEEKDAYS[due.getDay()]}</span>
        </div>
      ) : (
        <div className="schedule-date schedule-date-empty">
          <span className="schedule-date-day">--</span>
          <span className="schedule-date-week">待定</span>
        </div>
      )}
      <span className={`schedule-dot ${tone}`} />
      <div className="schedule-main">
        <Link className="summary-title-link" to={`/projects/${task.project_id}`}>{task.title}</Link>
        <small>{projectName || `项目 #${task.project_id}`}{due ? ` · 截止 ${due.getMonth() + 1}/${due.getDate()}` : ' · 截止时间待设置'}</small>
      </div>
    </div>
  )
}

export function SchedulePanel({ tasks, projectsById }) {
  const groups = buildSchedule(tasks)
  if (!groups.length) {
    return (
      <div className="schedule-empty">
        <strong>近期无日程</strong>
        <small>新任务设置截止日期后会自动出现在这里</small>
      </div>
    )
  }
  return (
    <div className="schedule-groups">
      {groups.map((group) => (
        <section className="schedule-group" key={group.key}>
          <div className="task-group-head">
            <span>{group.label}</span>
            <small>{group.items.length} 项</small>
          </div>
          <div className="schedule-list">
            {group.items.map((entry) => (
              <ScheduleRow
                key={entry.task.id}
                entry={entry}
                projectName={entry.task.project_name || projectsById[entry.task.project_id]?.name}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}

// 参考图「团队动态」：真实任务状态派生，负责人首字母头像
function activityCopy(task) {
  if (task.status === 'submitted') return '提交任务结果，等待负责人核验'
  if (task.status === 'completed') return '完成了任务'
  if (task.status === 'rejected') return '任务被驳回，需要补充材料'
  return '有一项待处理任务'
}

export function TeamActivityPanel({ tasks, projectsById }) {
  const activities = tasks
    .filter((task) => task.status !== 'completed' || task.result)
    .slice(0, 6)
    .map((task) => ({
      task,
      name: task.assignee_name || '',
      projectName: task.project_name || projectsById[task.project_id]?.name || `项目 #${task.project_id}`,
      copy: activityCopy(task),
      tone: task.status === 'submitted'
        ? 'success'
        : task.status === 'rejected'
          ? 'danger'
          : task.status === 'completed'
            ? 'muted'
            : 'warning',
    }))

  if (!activities.length) {
    return (
      <div className="schedule-empty">
        <strong>暂无团队动态</strong>
        <small>任务派发与提交后会在这里显示</small>
      </div>
    )
  }

  return (
    <ul className="activity-feed">
      {activities.map(({ task, name, projectName, copy, tone }) => (
        <li className="activity-feed-item" key={task.id}>
          <Avatar name={name} size={34} />
          <div className="activity-feed-main">
            <p><strong>{name || '待分配'}</strong> {copy}</p>
            <small>{task.title} · {projectName}</small>
          </div>
          <span className={`activity-feed-mark mark-${tone}`} />
        </li>
      ))}
    </ul>
  )
}
