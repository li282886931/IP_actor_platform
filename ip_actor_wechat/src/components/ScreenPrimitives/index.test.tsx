import React from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { DisplayItem } from '@/types/domain'
import {
  BusinessList,
  CandidateField,
  FormField,
  KeyValueGrid,
  ScreenHeader,
  ScreenHero,
  ScreenState,
  TaskBatchList,
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
})
