import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import DecisionPlatform from './DecisionPlatform'
import { getDecisionWorkspace, decisionMutation } from '../decisionApi'

vi.mock('../decisionApi', () => ({ getDecisionWorkspace: vi.fn(), decisionMutation: vi.fn(), calculateDecisionScenarios: vi.fn() }))
afterEach(() => { cleanup(); vi.clearAllMocks() })
const config = { thresholds: { comprehensive_breakeven: .5, stop_loss: .3, public_sale: .85, artist_fee: .6, presale: .5, large_spend: null, application_days: 60, permit_days: 14 }, dimensions: [], conditions: [] }
const data = (extra = {}) => ({ projects: [], records: [], stream: [], calendar: [], shows: [], cities: [], default_config: config, rules: [], ...extra })
const renderPage = (role = 'B', mode = 'decision') => render(<MemoryRouter><DecisionPlatform role={role} mode={mode} /></MemoryRouter>)

it('shows configuration gaps without invented scores and renders report redlines', async () => {
  getDecisionWorkspace.mockResolvedValue({ data: { data: data({ projects: [{ id: 3, name: '真实项目', stage: 'initiation', reports: [
    { id: 4, rule_version_id: 2, verification_status: 'pending', result: { status: 'vetoed', finance: { pure_breakeven: .7, comprehensive_breakeven: .6 }, score: { value: null, status: 'pending_configuration' }, vetoes: ['V2'], warnings: [], plan_triggers: [], configuration_gaps: ['dimensions', 'conditions'], missing_fields: [] } },
  ], evidences: [], actuals: null }] }) } })
  renderPage()
  expect(await screen.findByText('真实项目')).toBeInTheDocument()
  expect(screen.getByText('综合保本超过红线')).toBeInTheDocument()
  expect(screen.getByText('评分卡待配置')).toBeInTheDocument()
  expect(screen.getByText('60.00%')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: '推进下一阶段' })).toBeDisabled()
})

it('saves real brand valuation parameters and requires an authorized project', async () => {
  getDecisionWorkspace.mockResolvedValue({ data: { data: data({ projects: [{ id: 3, name: '合作项目', reports: [], evidences: [] }] }) } })
  decisionMutation.mockResolvedValue({ data: { data: {} } })
  renderPage('Brand', 'valuation')
  await screen.findByRole('heading', { name: '品牌权益与效果' })
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('记录名称'), '品牌合作')
  await user.type(screen.getByLabelText('赞助投入（元）'), '50000')
  await user.click(screen.getByRole('button', { name: '保存测算记录' }))
  expect(decisionMutation).toHaveBeenCalledWith('records', expect.objectContaining({
    kind: 'sponsorship', project_id: 3, payload: expect.objectContaining({ investment: 50000 }),
  }), expect.any(String))
})

it('retries failed data and shows honest empty state', async () => {
  getDecisionWorkspace.mockRejectedValueOnce(new Error('offline')).mockResolvedValue({ data: { data: data() } })
  renderPage()
  await userEvent.click(await screen.findByRole('button', { name: '重试' }))
  expect(await screen.findByText('暂无已授权项目')).toBeInTheDocument()
})

it('shows annual wishes and public artist posts without leaking raw objects', async () => {
  getDecisionWorkspace.mockResolvedValue({ data: { data: data({ stream: [{
    id: 1, title: '新作品', artist_name: '艺人甲', payload: { content: '作品正文', post_type: 'work' }, comments: [],
  }], records: [{ id: 2, kind: 'wishlist', title: '年度心愿', status: 'pending',
    payload: { year: 2026, show_ids: [], note: '期待音乐现场' }, result: {}, revision: 1 }] }) } })
  const { container } = renderPage('C', 'plan')
  expect(await screen.findByText('年度心愿')).toBeInTheDocument()
  expect(screen.getByText('作品正文')).toBeInTheDocument()
  expect(container.textContent).not.toContain('[object Object]')
  expect(screen.getByRole('link', { name: '关注艺人与收藏演出' })).toHaveAttribute('href', '/collaboration')
})

it('shows real deadline calendar with missing source status', async () => {
  getDecisionWorkspace.mockResolvedValue({ data: { data: data({ calendar: [{
    project_id: 3, title: '年度演出', date: '2026-12-31', application_due: '2026-11-01', permit_due: '2026-12-17', stage: 'approval',
  }], source_status: { weather: '待配置真实天气来源' } }) } })
  renderPage('B', 'calendar')
  expect(await screen.findByText('2026-12-31')).toBeInTheDocument()
  expect(screen.getByText('待配置真实天气来源')).toBeInTheDocument()
})

it('prefills saved actual settlement and edits city with its revision', async () => {
  getDecisionWorkspace.mockResolvedValue({ data: { data: data({ projects: [{
    id: 3, name: '结算项目', reports: [], actuals: { actual_revenue: 120000, actual_cost: 90000,
      actual_attendance: 500, status: 'pending', notes: '银行结算' },
  }] }) } })
  renderPage('B', 'review')
  expect(await screen.findByLabelText('实际净收入（元）')).toHaveValue(120000)
  expect(screen.getByLabelText('实际结算来源与归因')).toHaveValue('银行结算')
})

it('shows private upcoming reminders and verified city growth', async () => {
  getDecisionWorkspace.mockResolvedValue({ data: { data: data({ reminders: [{
    show_id: 2, title: '心愿演出', date: '2026-12-01', days_remaining: 5,
  }] }) } })
  renderPage('C', 'plan')
  expect(await screen.findByText(/心愿演出.*5 天/)).toBeInTheDocument()
})

it('keeps one record identity when retrying after a lost save response', async () => {
  getDecisionWorkspace.mockResolvedValue({ data: { data: data({ projects: [{ id: 3, name: '项目' }] }) } })
  decisionMutation.mockRejectedValueOnce(new Error('连接中断')).mockResolvedValueOnce({})
  renderPage('Brand', 'valuation')
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText('记录名称'), '幂等权益')
  await user.click(screen.getByRole('button', { name: '保存测算记录' }))
  await screen.findByRole('alert')
  await user.click(screen.getByRole('button', { name: '保存测算记录' }))
  expect(decisionMutation.mock.calls[0][1].record_key).toBe(decisionMutation.mock.calls[1][1].record_key)
  expect(decisionMutation.mock.calls[0][2]).toBe(decisionMutation.mock.calls[1][2])
})

const proposal = {
  ...config, catalog_version: 'v5-proposal-1',
  dimensions: [{ key: 'demand', label: '票房需求', metric: 'expected_occupancy', method: 'linear_high',
    category: 'income', weight: 1, max_score: 10, floor: 0, ceiling: 1, source: '平台建议' }],
  conditions: [], risk_categories: [{ key: 'demand', label: '需求票房', verification: '核验预售凭证', action: '需求预案' }],
  auxiliary_models: { brand_match: { label: '品牌匹配', max_total: 100, source: '平台建议',
    criteria: [{ key: 'target_coverage', metric: 'target_coverage', label: '目标受众覆盖', weight: 1,
      max_score: 10, method: 'linear_high', floor: 0, ceiling: 1, source: '平台建议' }] } },
}
const proposalData = () => data({ catalog: { config: proposal, name: '完整建议包', source: '平台建议',
  notice: '默认待核验', metrics: { expected_occupancy: '预计上座率' } }, rules: [{ id: 2, version_no: 1,
  name: '建议包', status: 'pending', config: proposal }], projects: [{ id: 3, name: '授权项目', reports: [], evidences: [] }] })

it('loads complete proposed catalog and saves editable normalization as pending', async () => {
  getDecisionWorkspace.mockResolvedValue({ data: { data: proposalData() } })
  decisionMutation.mockResolvedValue({})
  renderPage()
  const user = userEvent.setup()
  await user.click(await screen.findByText('规则版本与评分配置'))
  await user.click(screen.getByRole('button', { name: '载入完整建议包' }))
  expect(screen.getByText('需求票房 · 核验预售凭证 · 需求预案')).toBeInTheDocument()
  await user.clear(screen.getByLabelText('维度1上界'))
  await user.type(screen.getByLabelText('维度1上界'), '2')
  await user.click(screen.getByRole('button', { name: '保存新规则版本' }))
  expect(decisionMutation).toHaveBeenCalledWith('rules', expect.objectContaining({
    reviewed: false, config: expect.objectContaining({ dimensions: [expect.objectContaining({ ceiling: 2 })] }),
  }), expect.any(String))
})

it('generates automatic report without manual score overrides', async () => {
  getDecisionWorkspace.mockResolvedValue({ data: { data: proposalData() } })
  decisionMutation.mockResolvedValue({})
  renderPage()
  const user = userEvent.setup()
  expect(await screen.findByLabelText('评分方式')).toHaveValue('auto')
  expect(screen.queryByLabelText('评分票房需求')).not.toBeInTheDocument()
  await user.type(screen.getByLabelText('总成本（元）'), '400000')
  await user.click(screen.getByRole('button', { name: '生成并保存报告' }))
  expect(decisionMutation).toHaveBeenCalledWith('report/3', expect.objectContaining({
    inputs: expect.objectContaining({ scoring_mode: 'auto', total_cost: 400000, scores: {} }),
  }), expect.any(String))
})

it('saves auxiliary model inputs and explains the saved scoring snapshot', async () => {
  const item = proposalData()
  item.records = [{ id: 8, title: '已存匹配', kind: 'brand_match', status: 'pending', revision: 1, payload: {
    rule_version_id: 2, metrics: { target_coverage: .8 }, model_snapshot: proposal.auxiliary_models.brand_match,
    source: '受众样本', evidence_ids: [],
  }, result: { value: 80, max: 100, missing: [], source: '受众样本', rule_version_id: 2,
    dimensions: [{ key: 'target_coverage', label: '目标受众覆盖', raw_value: .8, score: 8, max_score: 10,
      weight: 1, contribution: 80, formula: '线性归一' }] } }]
  getDecisionWorkspace.mockResolvedValue({ data: { data: item } })
  decisionMutation.mockResolvedValue({})
  const { container } = renderPage('Brand', 'valuation')
  const user = userEvent.setup()
  await user.selectOptions(await screen.findByLabelText('记录类型'), 'brand_match')
  await user.type(screen.getByLabelText('记录名称'), '品牌评分')
  await user.selectOptions(screen.getByLabelText('辅助评分规则版本'), '2')
  await user.type(screen.getByLabelText('目标受众覆盖（0–1）'), '.75')
  await user.type(screen.getByLabelText('指标来源与参考基准'), '调研样本')
  await user.click(screen.getByRole('button', { name: '保存测算记录' }))
  expect(decisionMutation).toHaveBeenCalledWith('records', expect.objectContaining({ kind: 'brand_match',
    project_id: 3, payload: expect.objectContaining({ rule_version_id: 2, metrics: { target_coverage: .75 }, source: '调研样本' }),
  }), expect.any(String))
  expect(screen.getByText('80 / 100')).toBeInTheDocument()
  expect(container.textContent).not.toContain('[object Object]')
  await user.click(screen.getByRole('button', { name: '编辑' }))
  expect(screen.getByLabelText('目标受众覆盖（0–1）')).toHaveValue(.8)
})
