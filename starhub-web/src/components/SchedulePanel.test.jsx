import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { buildSchedule, parseDueDate, SchedulePanel, TeamActivityPanel } from './SchedulePanel'

const isoOffset = (days) => {
  const date = new Date()
  date.setDate(date.getDate() + days)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

const task = (id, overrides = {}) => ({
  id,
  project_id: 1,
  project_name: '南京站',
  title: `任务 ${id}`,
  description: '',
  status: 'pending',
  assignee_name: '张三',
  evidence_count: 0,
  ...overrides,
})

describe('parseDueDate', () => {
  it('parses loose date strings and rejects invalid values', () => {
    expect(parseDueDate('2026-08-01')).toBeInstanceOf(Date)
    expect(parseDueDate('2026/8/1 10:00')).toBeInstanceOf(Date)
    expect(parseDueDate('')).toBeNull()
    expect(parseDueDate('待沟通')).toBeNull()
    expect(parseDueDate('2026-13-40')).toBeNull()
  })
})

describe('buildSchedule', () => {
  it('groups tasks by due distance and skips completed tasks', () => {
    const groups = buildSchedule([
      task(1, { due_date: isoOffset(0) }),
      task(2, { due_date: isoOffset(1) }),
      task(3, { due_date: isoOffset(5) }),
      task(4, { due_date: isoOffset(-2) }),
      task(5, { due_date: '' }),
      task(6, { due_date: isoOffset(0), status: 'completed' }),
    ])
    const byKey = Object.fromEntries(groups.map((group) => [group.key, group.items.length]))
    expect(byKey.overdue).toBe(1)
    expect(byKey.today).toBe(1)
    expect(byKey.tomorrow).toBe(1)
    expect(byKey.week).toBe(1)
    expect(groups.flatMap((group) => group.items).some((entry) => entry.task.id === 5)).toBe(false)
    expect(groups.flatMap((group) => group.items).some((entry) => entry.task.id === 6)).toBe(false)
  })
})

describe('SchedulePanel', () => {
  const renderPanel = (tasks) => render(
    <MemoryRouter>
      <SchedulePanel tasks={tasks} projectsById={{ 1: { name: '南京站项目' } }} />
    </MemoryRouter>,
  )

  it('renders grouped schedule rows with date blocks', () => {
    renderPanel([task(1, { title: '确认场地安全', due_date: isoOffset(0) })])
    expect(screen.getByText('今日日程')).toBeInTheDocument()
    expect(screen.getByText('确认场地安全')).toBeInTheDocument()
    expect(screen.getByText(/截止/)).toBeInTheDocument()
  })

  it('renders an empty hint without schedulable tasks', () => {
    renderPanel([task(1, { status: 'completed', due_date: isoOffset(0) })])
    expect(screen.getByText('近期无日程')).toBeInTheDocument()
  })
})

describe('TeamActivityPanel', () => {
  const renderFeed = (tasks) => render(
    <MemoryRouter>
      <TeamActivityPanel tasks={tasks} projectsById={{}} />
    </MemoryRouter>,
  )

  it('renders assignee avatars and status-derived copy', () => {
    renderFeed([
      task(1, { assignee_name: '张三', status: 'submitted', result: '已完成' }),
      task(2, { assignee_name: '李四', status: 'pending' }),
    ])
    expect(screen.getByTitle('张三')).toBeInTheDocument()
    expect(screen.getByTitle('李四')).toBeInTheDocument()
    expect(screen.getByText(/提交任务结果/)).toBeInTheDocument()
    expect(screen.getByText(/有一项待处理任务/)).toBeInTheDocument()
  })

  it('renders an empty hint without activities', () => {
    renderFeed([])
    expect(screen.getByText('暂无团队动态')).toBeInTheDocument()
  })
})
