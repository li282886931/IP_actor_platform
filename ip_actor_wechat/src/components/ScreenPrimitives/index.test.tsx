import React from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { DisplayItem } from '@/types/domain'
import {
  Avatar,
  BusinessList,
  CandidateField,
  DecisionCockpit,
  FormField,
  KeyValueGrid,
  LifecycleTimeline,
  MetricGrid,
  ProgressRing,
  ScenarioBars,
  ScreenHeader,
  ScreenHero,
  ScreenState,
  ScenarioStrip,
  TaskBatchList,
  ValueEvidencePanel,
  VariancePanel,
  WorkBriefing,
  formatWan,
} from './index'

vi.mock('@tarojs/components', () => ({
  Button: ({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) => <button {...props}>{children}</button>,
  Input: ({
    onInput,
    ...props
  }: Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onInput'> & {
    onInput?: (event: { detail: { value: string } }) => void
  }) => <input {...props} onInput={(event) => onInput?.({ detail: { value: event.currentTarget.value } })} />,
  Text: ({ children, ...props }: React.HTMLAttributes<HTMLSpanElement>) => <span {...props}>{children}</span>,
  View: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => <div {...props}>{children}</div>,
}))

vi.mock('@/components/SearchSelect', () => ({
  default: ({ onSelect }: { onSelect: (option: unknown) => void }) => (
    <button onClick={() => onSelect({ label: '南京奥体中心' })}>选择候选</button>
  ),
}))

const items: DisplayItem[] = [{
  id: 'show-3',
  title: '真实演出',
  description: '真实描述',
  status: '售票中',
  context: {},
  detailRef: { entity_type: 'show', entity_id: 3 },
}, {
  id: 'metric-profit',
  title: '预计利润',
  description: '派生指标',
  status: '已测算',
  context: {},
}]

describe('ScreenPrimitives', () => {
  it('renders the screen header and delegates home navigation', () => {
    const onHome = vi.fn()
    render(<ScreenHeader screenCode='S14' showHome onHome={onHome} />)

    expect(screen.getByText('锐音场')).toBeInTheDocument()
    expect(screen.getByText('S14')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '主页' }))
    expect(onHome).toHaveBeenCalledOnce()
  })

  it('renders a screen hero with optional summary information', () => {
    render(<ScreenHero group='项目' title='服务端标题' subtitle='服务端副标题' highlight='7 项待办' context='产品蓝图 · S10' />)

    expect(screen.getByText('项目')).toBeInTheDocument()
    expect(screen.getByText('服务端标题')).toBeInTheDocument()
    expect(screen.getByText('7 项待办')).toBeInTheDocument()
  })

  it('renders loading, empty and error states with supplied actions', () => {
    const onRetry = vi.fn()
    const onEmptyAction = vi.fn()
    const view = render(<ScreenState state='loading' />)
    expect(screen.getByText('正在连接决策服务...')).toBeInTheDocument()

    view.rerender(<ScreenState state='empty' emptyState={{ title: '暂无项目', description: '请创建项目', actionLabel: '创建项目' }} onEmptyAction={onEmptyAction} />)
    fireEvent.click(screen.getByRole('button', { name: '创建项目' }))
    expect(onEmptyAction).toHaveBeenCalledOnce()

    view.rerender(<ScreenState state='error' message='请求失败' onRetry={onRetry} />)
    expect(screen.getByText('请求失败')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '重新加载' }))
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('renders compact key value fields and form input changes', () => {
    const onChange = vi.fn()
    render(
      <>
        <KeyValueGrid items={[{ label: '场馆', value: '南京奥体中心' }]} />
        <FormField label='项目名称' value='' placeholder='输入名称' onChange={onChange} />
      </>,
    )

    expect(screen.getByText('南京奥体中心')).toBeInTheDocument()
    fireEvent.input(screen.getByPlaceholderText('输入名称'), { target: { value: '南京站' } })
    expect(onChange).toHaveBeenCalledWith('南京站')
  })

  it('passes the selected candidate to the field consumer', () => {
    const onSelect = vi.fn()
    render(<CandidateField value='' placeholder='搜索场馆' initialSections={[]} onInput={vi.fn()} onSearch={vi.fn()} onSelect={onSelect} />)

    fireEvent.click(screen.getByRole('button', { name: '选择候选' }))
    expect(onSelect).toHaveBeenCalledWith({ label: '南京奥体中心' })
  })

  it('opens only persisted business entities', () => {
    const onOpenDetail = vi.fn()
    render(<BusinessList items={items} onOpenDetail={onOpenDetail} />)

    fireEvent.click(screen.getByText('真实演出'))
    fireEvent.click(screen.getByText('预计利润'))
    expect(onOpenDetail).toHaveBeenCalledWith(items[0])
    expect(onOpenDetail).toHaveBeenCalledTimes(1)
  })

  it('shows real task actionability and evidence requirements', () => {
    render(
      <BusinessList
        items={[{
          ...items[0],
          context: {
            task_id: 3,
            actionability: ['accept', 'reject', 'block'],
            evidence_required: true,
          },
        }]}
        onOpenDetail={vi.fn()}
      />,
    )

    expect(screen.getByText('可接受 · 可拒绝 · 可阻塞')).toBeInTheDocument()
    expect(screen.getByText('需补证据')).toBeInTheDocument()
  })

  it('delegates task selection, expansion and detail navigation', () => {
    const onToggleSelection = vi.fn()
    const onToggleDetails = vi.fn()
    const onOpenDetail = vi.fn()
    render(
      <TaskBatchList
        items={[items[0]]}
        selectedTaskIds={[]}
        expandedTaskIds={[]}
        onToggleSelection={onToggleSelection}
        onToggleDetails={onToggleDetails}
        onOpenDetail={onOpenDetail}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: '选择真实演出' }))
    fireEvent.click(screen.getByText('真实演出'))
    fireEvent.click(screen.getByRole('button', { name: '查看真实演出详情' }))
    expect(onToggleSelection).toHaveBeenCalledWith(3)
    expect(onToggleDetails).toHaveBeenCalledWith(3)
    expect(onOpenDetail).toHaveBeenCalledWith(items[0])
  })

  it('renders value evidence only with its real source label', () => {
    render(<ValueEvidencePanel evidence={[{
      title: '杭州现场演出',
      metric: '480-1280',
      source_label: '当前机会',
    }]} />)

    expect(screen.getByText('杭州现场演出')).toBeInTheDocument()
    expect(screen.getByText('当前机会')).toBeInTheDocument()
    expect(screen.getByText('480-1280')).toBeInTheDocument()
  })

  it('renders a decision cockpit and calculated scenario strip', () => {
    render(
      <>
        <DecisionCockpit
          cockpit={{
            neutral_profit: 2860000,
            breakeven_attendance: 8040,
            maximum_funding_gap: 480000,
            status: 'calculated',
            combination: { artist: '艺人组合 B', city: '南京', venue: '奥体中心' },
            missing_fields: [],
          }}
        />
        <ScenarioStrip scenarios={{
          conservative: { profit: 1200000, attendance: 8000 },
          neutral: { profit: 2860000, attendance: 10000 },
          optimistic: { profit: 3600000, attendance: 12000 },
        }} />
      </>,
    )

    expect(screen.getByText('中性利润')).toBeInTheDocument()
    expect(screen.getAllByText('2860000').length).toBeGreaterThan(0)
    expect(screen.getByText('保守')).toBeInTheDocument()
    expect(screen.getByText('乐观')).toBeInTheDocument()
  })

  it('renders a work briefing and lifecycle variance without fabricated values', () => {
    render(
      <>
        <WorkBriefing briefing={{
          today_change_count: 3,
          top_task: { title: '确认场馆报价', status: 'pending', project_name: '南京站' },
          active_project_count: 2,
        }} />
        <LifecycleTimeline currentStage='售票' />
        <VariancePanel loop={{
          forecast_profit: 1800000,
          actual_profit: 1400000,
          profit_variance: -400000,
          notes: '已完成结算',
        }} />
      </>,
    )

    expect(screen.getByText('今日变化 3 项')).toBeInTheDocument()
    expect(screen.getByText('确认场馆报价')).toBeInTheDocument()
    expect(screen.getByText('售票')).toBeInTheDocument()
    expect(screen.getByText('预测利润')).toBeInTheDocument()
    expect(screen.getByText('-400000')).toBeInTheDocument()
  })

  it('renders KPI metric cards and hides an empty grid', () => {
    const view = render(
      <MetricGrid items={[
        { label: '项目总数', value: '12', hint: '进行中 5' },
        { label: '风险告警', value: '2', tone: 'danger' },
      ]} />,
    )

    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('项目总数')).toBeInTheDocument()
    expect(screen.getByText('进行中 5')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()

    view.rerender(<MetricGrid items={[]} />)
    expect(screen.queryByText('项目总数')).not.toBeInTheDocument()
  })

  it('invokes the metric card tap handler only for actionable cards', () => {
    const onTap = vi.fn()
    render(
      <MetricGrid items={[
        { label: '待办任务', value: '3', onTap },
        { label: '全部项目', value: '8' },
      ]} />,
    )

    fireEvent.click(screen.getByText('待办任务'))
    expect(onTap).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByText('全部项目'))
    expect(onTap).toHaveBeenCalledTimes(1)
  })

  it('renders the avatar with the last Chinese character and a stable hash color', () => {
    const { getByText, rerender } = render(<Avatar name='张三' size={56} />)
    expect(getByText('三')).toBeInTheDocument()
    const avatar = getByText('三').parentElement
    expect(avatar?.getAttribute('style')).toContain('56px')
    expect(avatar?.getAttribute('style')).toMatch(/background-color/)

    rerender(<Avatar name='alice' />)
    expect(screen.getByText('A')).toBeInTheDocument()
    rerender(<Avatar name='' />)
    expect(screen.getByText('?')).toBeInTheDocument()
  })

  it('renders a progress ring with clamped arc and accessible label', () => {
    const view = render(<ProgressRing percent={72} label='项目进度' caption='已完成 72% · 剩余 28%' />)

    expect(screen.getByText('72%')).toBeInTheDocument()
    expect(screen.getByText('项目进度')).toBeInTheDocument()
    expect(screen.getByText('已完成 72% · 剩余 28%')).toBeInTheDocument()
    // jsdom 会丢弃 conic-gradient 声明，但保留 CSS 自定义属性，足以验证弧度换算
    const ringStyle = screen.getByRole('img', { name: '项目进度 72%' }).getAttribute('style') ?? ''
    expect(ringStyle).toContain('--ring-progress: 259.2deg')

    view.rerender(<ProgressRing percent={150} label='售票进度' />)
    expect(screen.getByText('150%')).toBeInTheDocument()
    const overshootStyle = screen.getByRole('img', { name: '售票进度 150%' }).getAttribute('style') ?? ''
    expect(overshootStyle).toContain('--ring-progress: 360deg')
  })

  it('renders diverging scenario bars with compact wan values and filters missing data', () => {
    render(
      <ScenarioBars
        title='三情景利润对比'
        items={[
          { label: '保守', value: -128600 },
          { label: '中性', value: 1181900 },
          { label: '乐观', value: null },
        ]}
        note='同一公式版本'
      />,
    )

    expect(screen.getByText('三情景利润对比')).toBeInTheDocument()
    expect(screen.getByText('-12.9万')).toBeInTheDocument()
    expect(screen.getByText('118.2万')).toBeInTheDocument()
    expect(screen.queryByText('乐观')).not.toBeInTheDocument()
    expect(screen.getByText('同一公式版本')).toBeInTheDocument()
  })

  it('does not render scenario bars without numeric values and formats wan compactly', () => {
    const { container } = render(
      <ScenarioBars title='空图表' items={[{ label: '中性', value: null }]} />,
    )
    expect(container).toBeEmptyDOMElement()
    expect(formatWan(2235300)).toBe('223.5万')
    expect(formatWan(9800)).toBe('9800')
    expect(formatWan(123000000)).toBe('1.2亿')
  })
})
