import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ProgressRing, ScenarioBarChart, SegmentedBar, formatCompactCurrency } from './Charts'

describe('Charts', () => {
  it('renders a progress ring with accessible percentage and clamped arc', () => {
    const { rerender } = render(<ProgressRing percent={72} label="项目进度" caption="已完成 72% · 剩余 28%" />)

    expect(screen.getByText('72%')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: '项目进度 72%' })).toBeInTheDocument()
    expect(screen.getByText('已完成 72% · 剩余 28%')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: '项目进度 72%' }).getAttribute('style')).toContain('--ring-progress: 259.2deg')

    rerender(<ProgressRing percent={150} label="售票进度" />)
    expect(screen.getByText('150%')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: '售票进度 150%' }).getAttribute('style')).toContain('--ring-progress: 360deg')
  })

  it('renders diverging scenario bars and filters missing values', () => {
    render(
      <ScenarioBarChart
        items={[
          { label: '保守', value: -128600 },
          { label: '中性', value: 1181900 },
          { label: '乐观', value: null },
        ]}
        note="同一公式版本"
      />,
    )

    expect(screen.getByText('保守')).toBeInTheDocument()
    expect(screen.getByText('-12.9万')).toBeInTheDocument()
    expect(screen.getByText('118.2万')).toBeInTheDocument()
    expect(screen.queryByText('乐观')).not.toBeInTheDocument()
    expect(screen.getByText('同一公式版本')).toBeInTheDocument()
  })

  it('renders a segmented bar only for positive status counts', () => {
    render(
      <SegmentedBar segments={[
        { label: '已测算', value: 3, tone: 'gold' },
        { label: '待确认', value: 1, tone: 'amber' },
        { label: '已归档', value: 0, tone: 'muted2' },
      ]} />,
    )

    expect(screen.getByText('已测算')).toBeInTheDocument()
    expect(screen.getByText('待确认')).toBeInTheDocument()
    expect(screen.queryByText('已归档')).not.toBeInTheDocument()
  })

  it('shows an empty hint when no segment has data', () => {
    render(<SegmentedBar segments={[{ label: '已测算', value: 0, tone: 'gold' }]} />)
    expect(screen.getByText('暂无状态数据')).toBeInTheDocument()
  })

  it('formats compact currency values', () => {
    expect(formatCompactCurrency(1181900)).toBe('118.2万')
    expect(formatCompactCurrency(-128600)).toBe('-12.9万')
    expect(formatCompactCurrency(9800)).toBe('9800')
    expect(formatCompactCurrency(123000000)).toBe('1.2亿')
    expect(formatCompactCurrency(null)).toBe('-')
  })
})
