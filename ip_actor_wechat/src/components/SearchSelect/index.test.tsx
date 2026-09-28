import React from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import SearchSelect, { type SearchSelectSection } from './index'

vi.mock('@tarojs/components', () => ({
  Input: ({
    onInput,
    ...props
  }: Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onInput'> & {
    onInput?: (event: { detail: { value: string } }) => void
  }) => (
    <input
      {...props}
      onInput={(event) => onInput?.({ detail: { value: event.currentTarget.value } })}
    />
  ),
  Text: ({ children, ...props }: React.HTMLAttributes<HTMLSpanElement>) => <span {...props}>{children}</span>,
  View: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => <div {...props}>{children}</div>,
}))

const sections: SearchSelectSection[] = [
  {
    entityType: 'artist',
    label: '艺人 / IP',
    options: [{
      entityType: 'artist',
      entityId: 7,
      label: '周杰伦',
      description: '艺人库',
      value: { id: 7, name: '周杰伦' },
    }],
  },
  {
    entityType: 'project',
    label: '历史项目',
    options: [{
      entityType: 'project',
      entityId: 42,
      label: '嘉年华南京站',
      description: '南京 · 体育中心',
      value: { id: 42, name: '嘉年华南京站' },
    }],
  },
]

describe('SearchSelect', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('waits 300ms and cancels the previous keyword search', async () => {
    const onSearch = vi.fn().mockResolvedValue(sections)
    const onInput = vi.fn()
    render(<SearchSelect value='' onInput={onInput} onSearch={onSearch} onSelect={vi.fn()} />)
    const input = screen.getByRole('textbox')

    fireEvent.input(input, { target: { value: '周' } })
    fireEvent.input(input, { target: { value: '周杰' } })
    await vi.advanceTimersByTimeAsync(299)
    expect(onSearch).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(1)
    expect(onSearch).toHaveBeenCalledTimes(1)
    expect(onSearch).toHaveBeenCalledWith('周杰')
  })

  it('shows database candidates on focus before a keyword is entered', () => {
    const onSelect = vi.fn()
    render(
      <SearchSelect
        value=''
        initialSections={[sections[0]]}
        onInput={vi.fn()}
        onSearch={vi.fn().mockResolvedValue(sections)}
        onSelect={onSelect}
      />,
    )

    fireEvent.focus(screen.getByRole('textbox'))
    expect(screen.getByText('艺人 / IP')).toBeInTheDocument()
    fireEvent.click(screen.getByText('周杰伦'))

    expect(onSelect).toHaveBeenCalledWith(sections[0].options[0])
  })

  it('groups results by entity type', async () => {
    const onSearch = vi.fn().mockResolvedValue(sections)
    render(<SearchSelect value='' onInput={vi.fn()} onSearch={onSearch} onSelect={vi.fn()} />)

    fireEvent.input(screen.getByRole('textbox'), { target: { value: '南京' } })
    await vi.advanceTimersByTimeAsync(300)

    expect(screen.getByText('艺人 / IP')).toBeInTheDocument()
    expect(screen.getByText('历史项目')).toBeInTheDocument()
    expect(screen.getByText('周杰伦')).toBeInTheDocument()
    expect(screen.getByText('嘉年华南京站')).toBeInTheDocument()
  })

  it('returns the selected entity and closes the dropdown', async () => {
    const onSelect = vi.fn()
    render(<SearchSelect value='' onInput={vi.fn()} onSearch={vi.fn().mockResolvedValue(sections)} onSelect={onSelect} />)
    fireEvent.input(screen.getByRole('textbox'), { target: { value: '周杰伦' } })
    await vi.advanceTimersByTimeAsync(300)
    fireEvent.click(screen.getByText('周杰伦'))

    expect(onSelect).toHaveBeenCalledWith(sections[0].options[0])
    expect(screen.queryByText('艺人 / IP')).not.toBeInTheDocument()
  })

  it('shows loading, empty, and error states exclusively', async () => {
    const onSearch = vi.fn()
      .mockResolvedValueOnce([])
      .mockRejectedValueOnce(new Error('network'))
    const view = render(<SearchSelect value='' onInput={vi.fn()} onSearch={onSearch} onSelect={vi.fn()} />)

    fireEvent.input(screen.getByRole('textbox'), { target: { value: '无结果' } })
    expect(screen.getByText('正在搜索...')).toBeInTheDocument()
    await vi.advanceTimersByTimeAsync(300)
    expect(screen.getByText('未找到匹配结果')).toBeInTheDocument()
    expect(screen.queryByText('正在搜索...')).not.toBeInTheDocument()

    view.rerender(<SearchSelect value='失败' onInput={vi.fn()} onSearch={onSearch} onSelect={vi.fn()} />)
    await vi.advanceTimersByTimeAsync(300)
    expect(screen.getByText('搜索失败，请稍后重试')).toBeInTheDocument()
    expect(screen.queryByText('未找到匹配结果')).not.toBeInTheDocument()
  })

  it('closes the dropdown after the field loses focus', async () => {
    render(<SearchSelect value='' onInput={vi.fn()} onSearch={vi.fn().mockResolvedValue(sections)} onSelect={vi.fn()} />)
    const input = screen.getByRole('textbox')
    fireEvent.input(input, { target: { value: '周杰伦' } })
    await vi.advanceTimersByTimeAsync(300)
    expect(screen.getByText('艺人 / IP')).toBeInTheDocument()

    fireEvent.blur(input)
    await vi.advanceTimersByTimeAsync(150)
    expect(screen.queryByText('艺人 / IP')).not.toBeInTheDocument()
  })
})
