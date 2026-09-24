import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import Generate from './Generate'
import { generateAIStream } from '../api'

vi.mock('../api', () => ({
  generateAIStream: vi.fn(),
}))

describe('Generate', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('renders the generated copy from the API response payload', async () => {
    generateAIStream.mockImplementation(async (_payload, handlers) => {
      handlers.onFinal('Generated copy')
      return 'Generated copy'
    })

    render(<Generate />)

    await userEvent.click(screen.getByRole('button', { name: /一键生成/ }))

    await waitFor(() => {
      expect(screen.getByText('Generated copy')).toBeInTheDocument()
    })
    expect(screen.queryByText(/"code":0/)).not.toBeInTheDocument()
  })

  it('renders markdown result as structured HTML without exposing raw markup', async () => {
    generateAIStream.mockImplementation(async (_payload, handlers) => {
      const result = [
        '# 演出宣发方案',
        '',
        '## 传播定位',
        '',
        '**主题策略：** 强调城市相遇。',
        '',
        '- 本地乐迷转化',
        '- 社交平台扩散',
      ].join('\n')
      handlers.onFinal(result)
      return result
    })

    render(<Generate />)

    await userEvent.click(screen.getByRole('button', { name: /一键生成/ }))

    expect(await screen.findByRole('heading', { name: '演出宣发方案' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '传播定位' })).toBeInTheDocument()
    expect(screen.getByText('主题策略：')).toBeInTheDocument()
    expect(screen.getByText('本地乐迷转化')).toBeInTheDocument()
    expect(screen.queryByText('# 演出宣发方案')).not.toBeInTheDocument()
  })

  it('disables generation while the request is pending', async () => {
    let resolveRequest
    generateAIStream.mockReturnValue(new Promise((resolve) => {
      resolveRequest = resolve
    }))

    render(<Generate />)

    const button = screen.getByRole('button', { name: /一键生成/ })
    await userEvent.click(button)

    expect(screen.getByRole('button', { name: /AI 生成中/ })).toBeDisabled()

    resolveRequest('Done')
    await waitFor(() => expect(screen.getByText('Done')).toBeInTheDocument())
  })

  it('requests new AI content on every click and renders the latest result automatically', async () => {
    generateAIStream
      .mockImplementationOnce(async (_payload, handlers) => {
        handlers.onFinal('First generated copy')
        return 'First generated copy'
      })
      .mockImplementationOnce(async (_payload, handlers) => {
        handlers.onFinal('Second generated copy')
        return 'Second generated copy'
      })

    render(<Generate />)

    const user = userEvent.setup()
    const button = screen.getByRole('button', { name: /一键生成/ })

    await user.click(button)
    expect(await screen.findByText('First generated copy')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /一键生成/ }))
    expect(await screen.findByText('Second generated copy')).toBeInTheDocument()
    expect(screen.queryByText('First generated copy')).not.toBeInTheDocument()

    expect(generateAIStream).toHaveBeenCalledTimes(2)
    expect(generateAIStream.mock.calls[0][0].generation_nonce).toBeTruthy()
    expect(generateAIStream.mock.calls[1][0].generation_nonce).toBeTruthy()
    expect(generateAIStream.mock.calls[0][0].generation_nonce).not.toBe(generateAIStream.mock.calls[1][0].generation_nonce)
  })

  it('shows generation progress and keeps think content out of the final copy', async () => {
    let finishStream
    generateAIStream.mockImplementation(async (_payload, handlers) => {
      handlers.onProgress('模型正在生成内容')
      handlers.onThought('先定位目标客群')
      await new Promise((resolve) => {
        finishStream = resolve
      })
      handlers.onFinal('<think>hidden reasoning</think>\n传播定位\n最终文案')
      return '传播定位\n最终文案'
    })

    render(<Generate />)

    await userEvent.click(screen.getByRole('button', { name: /一键生成/ }))

    expect(await screen.findByText('模型正在生成内容')).toBeInTheDocument()
    expect(await screen.findByText('先定位目标客群')).toBeInTheDocument()
    expect(screen.getByText('生成过程')).toBeInTheDocument()
    finishStream()
    await waitFor(() => {
      expect(screen.getByText(/传播定位/)).toBeInTheDocument()
      expect(screen.getByText('先定位目标客群')).toBeInTheDocument()
      expect(screen.queryByText(/hidden reasoning/)).not.toBeInTheDocument()
      expect(screen.queryByText(/<think>/)).not.toBeInTheDocument()
    })
  })

  it('restores completed generated content from local storage when returning to the page', async () => {
    localStorage.setItem('starhub-ai-generation-state', JSON.stringify({
      form: {
        type: 'poster',
        show_name: '周杰伦·北京演唱会',
        artist: '周杰伦',
        city: '北京',
      },
      result: '## 已完成文案\n\n最终内容',
      status: 'success',
      progressMessages: ['内容已整理完成'],
      thoughts: '已完成分析',
    }))

    render(<Generate />)

    expect(screen.getByDisplayValue('周杰伦·北京演唱会')).toBeInTheDocument()
    expect(screen.getByDisplayValue('周杰伦')).toBeInTheDocument()
    expect(screen.getByDisplayValue('北京')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '已完成文案' })).toBeInTheDocument()
    expect(screen.getByText('已完成分析')).toBeInTheDocument()
  })

  it('restores in-progress generation state when returning to the page', async () => {
    let finishStream
    generateAIStream.mockImplementation(async (_payload, handlers) => {
      handlers.onProgress('模型正在生成内容')
      handlers.onThought('正在分析城市受众')
      await new Promise((resolve) => {
        finishStream = resolve
      })
      handlers.onFinal('最终生成内容')
      return '最终生成内容'
    })

    const { unmount } = render(<Generate />)
    const user = userEvent.setup()

    await user.type(screen.getByPlaceholderText('例如：周杰伦嘉年华世界巡回演唱会'), '周杰伦·北京演唱会')
    await user.type(screen.getByPlaceholderText('输入艺人名称'), '周杰伦')
    await user.type(screen.getByPlaceholderText('输入演出城市'), '北京')
    await user.click(screen.getByRole('button', { name: /一键生成/ }))

    expect(await screen.findByText('模型正在生成内容')).toBeInTheDocument()
    unmount()

    render(<Generate />)

    expect(screen.getByDisplayValue('周杰伦·北京演唱会')).toBeInTheDocument()
    expect(screen.getByText('模型正在生成内容')).toBeInTheDocument()
    expect(screen.getByText('正在分析城市受众')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /AI 生成中/ })).toBeDisabled()

    finishStream()
  })
})
