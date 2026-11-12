import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import LiveAnalysis from './LiveAnalysis'
import { agentChat, listAgentSources } from '../api'

vi.mock('../api', () => ({ agentChat: vi.fn(), listAgentSources: vi.fn() }))
afterEach(() => { cleanup(); vi.clearAllMocks() })

it('reads selected MCP webpage and API sources and displays traceable pending evidence', async () => {
  listAgentSources.mockResolvedValue({ data: { data: [
    { id: 1, name: '公开资料', kind: 'mcp_web', status: 'ready', requires_url: true },
    { id: 2, name: '场馆查询', kind: 'agent_api', status: 'ready' },
  ] } })
  agentChat.mockResolvedValue({ data: { data: { answer: '依据 [1]，容量待核验。', readings: [{
    source_id: 2, source_name: '场馆查询', status: 'completed', source_uri: 'https://api.example.org/venues',
    captured_at: '2026-11-12T08:00:00Z', evidence_id: 10, excerpt: '容量：1800 人',
    content: '{"capacity":1800,"unit":"人"}',
  }] } } })
  const refresh = vi.fn()
  const user = userEvent.setup()
  render(<LiveAnalysis projectId={3} onEvidenceChanged={refresh} />)
  await user.click(await screen.findByLabelText('公开资料'))
  await user.type(screen.getByLabelText('网页地址 · 公开资料'), 'https://news.example.org/show')
  await user.click(screen.getByLabelText('场馆查询'))
  await user.type(screen.getByLabelText('向智能体提问'), '查阅来源')
  await user.click(screen.getByRole('button', { name: '询问智能体' }))
  await waitFor(() => expect(agentChat).toHaveBeenCalledWith({
    project_id: 3, message: '查阅来源', reads: [
      { source_id: 1, url: 'https://news.example.org/show' }, { source_id: 2 },
    ], use_ai: false,
  }))
  expect(await screen.findByText('容量：1800 人')).toBeInTheDocument()
  expect(screen.getByText('证据 #10 · 待人工核验')).toBeInTheDocument()
  expect(refresh).toHaveBeenCalled()
  expect(screen.queryByText('[object Object]')).not.toBeInTheDocument()
})

it('shows configuration gaps and handles request errors without getting stuck', async () => {
  listAgentSources.mockResolvedValue({ data: { data: [
    { id: 1, name: '未授权接口', kind: 'agent_api', status: 'unconfigured' },
  ] } })
  agentChat.mockRejectedValue(new Error('network'))
  const user = userEvent.setup()
  render(<LiveAnalysis projectId={3} />)
  expect(await screen.findByLabelText('未授权接口')).toBeDisabled()
  await user.type(screen.getByLabelText('向智能体提问'), '分析风险')
  await user.click(screen.getByRole('button', { name: '询问智能体' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('研判请求失败')
  expect(screen.getByRole('button', { name: '询问智能体' })).toBeEnabled()
  expect(screen.getByLabelText('向智能体提问')).toHaveValue('分析风险')
})

it('validates selected webpage addresses before sending a request', async () => {
  listAgentSources.mockResolvedValue({ data: { data: [
    { id: 1, name: '网页工具', kind: 'mcp_web', status: 'ready', requires_url: true },
  ] } })
  const user = userEvent.setup()
  render(<LiveAnalysis projectId={3} />)
  await user.click(await screen.findByLabelText('网页工具'))
  await user.type(screen.getByLabelText('向智能体提问'), '读取网页')
  await user.click(screen.getByRole('button', { name: '询问智能体' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('请填写')
  expect(agentChat).not.toHaveBeenCalled()
})
