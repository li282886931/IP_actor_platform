import React from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { DisplayItem } from '@/types/domain'
import {
  BusinessList,
  CandidateField,
  DecisionCockpit,
  FormField,
  KeyValueGrid,
  LifecycleTimeline,
  ScreenHeader,
  ScreenHero,
  ScreenState,
  ScenarioStrip,
  TaskBatchList,
  ValueEvidencePanel,
  VariancePanel,
  WorkBriefing,
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
})
