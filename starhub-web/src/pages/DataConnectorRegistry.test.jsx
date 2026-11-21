import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import DataConnectorRegistry, { connectorAction } from './DataConnectorRegistry'
import {
  activateDataSourceRegistration,
  createCustomConnectorDefinition,
  disableDataSourceRegistration,
  listConnectorDefinitions,
  registerDataSource,
  testDataSourceRegistration,
  updateDataSourceRegistration,
} from '../api'

vi.mock('../api', () => ({
  activateDataSourceRegistration: vi.fn(),
  createCustomConnectorDefinition: vi.fn(),
  disableDataSourceRegistration: vi.fn(),
  listConnectorDefinitions: vi.fn(),
  registerDataSource: vi.fn(),
  testDataSourceRegistration: vi.fn(),
  updateDataSourceRegistration: vi.fn(),
}))

const definitions = [
  {
    id: 1,
    key: 'amap',
    name: '高德场馆',
    description: '搜索场馆 POI',
    source_kind: 'api',
    domain: 'venue',
    availability: 'available',
    auth_type: 'api_key',
    capabilities: ['search', 'read'],
    config_schema: {
      fields: [
        { name: 'operation', label: '读取能力', type: 'select', required: true, options: ['venue_search'], default: 'venue_search' },
      ],
    },
    registration: {
      id: 11,
      name: '高德场馆',
      status: 'pending_credentials',
      credential_ref: '',
      credential_status: 'missing',
      scope_config: { operation: 'venue_search' },
      last_test_at: null,
    },
  },
  {
    id: 2,
    key: 'damai_business',
    name: '大麦授权销售数据',
    description: '读取授权销售数据',
    source_kind: 'api',
    domain: 'ticketing',
    availability: 'contract_required',
    auth_type: 'vendor_contract',
    capabilities: ['read'],
    config_schema: { fields: [] },
    registration: null,
  },
  {
    id: 3,
    key: 'custom_mcp',
    name: '只读 MCP',
    description: '读取公开网页资料',
    source_kind: 'mcp',
    domain: 'research',
    availability: 'available',
    auth_type: 'none',
    capabilities: ['read'],
    config_schema: {
      fields: [
        { name: 'endpoint', label: '服务地址', type: 'url', required: true },
        { name: 'tool_name', label: '工具名称', type: 'text', required: true },
      ],
    },
    registration: null,
  },
  {
    id: 4,
    key: 'qweather',
    name: '和风天气',
    description: '三日天气预报',
    source_kind: 'api',
    domain: 'weather',
    availability: 'available',
    auth_type: 'api_key',
    capabilities: ['read'],
    config_schema: { fields: [] },
    registration: {
      id: 14,
      name: '和风天气',
      status: 'ready',
      credential_ref: 'QWEATHER_PROD',
      credential_status: 'configured',
      scope_config: {},
      last_test_at: '2026-11-20T08:00:00Z',
    },
  },
]

const wrappedDefinitions = () => ({ data: { code: 0, data: definitions } })

describe('DataConnectorRegistry', () => {
  beforeEach(() => {
    listConnectorDefinitions.mockResolvedValue(wrappedDefinitions())
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('maps definition and registration states to safe actions', () => {
    expect(connectorAction(definitions[0])).toBe('credentials')
    expect(connectorAction(definitions[1])).toBe('blocked')
    expect(connectorAction(definitions[2])).toBe('register')
    expect(connectorAction(definitions[3])).toBe('activate')
    expect(connectorAction({ availability: 'available', registration: { status: 'active' } })).toBe('active')
  })

  it('renders a compact catalog with summary, blocked states, and no plaintext secret field', async () => {
    render(<DataConnectorRegistry />)

    expect(await screen.findByRole('heading', { name: '数据连接器' })).toBeInTheDocument()
    expect(screen.getByText('高德场馆')).toBeInTheDocument()
    expect(screen.getByText('大麦授权销售数据')).toBeInTheDocument()
    const amapRow = screen.getByText('高德场馆').closest('[role="row"]')
    expect(within(amapRow).getByText('待鉴权')).toBeInTheDocument()
    expect(screen.getAllByText('待商务授权').length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: '自定义连接器' })).toBeInTheDocument()
    expect(screen.getByLabelText('目录总数')).toHaveTextContent('4')
    expect(screen.getByLabelText('待注册')).toHaveTextContent('1')
    expect(screen.getByLabelText('待鉴权')).toHaveTextContent('1')
    expect(screen.queryByText('输入密钥')).not.toBeInTheDocument()
    expect(document.querySelector('input[type="password"]')).not.toBeInTheDocument()

    const contractRow = screen.getByText('大麦授权销售数据').closest('[role="row"]')
    expect(within(contractRow).queryByRole('button', { name: /测试|启用/ })).not.toBeInTheDocument()
  })

  it('filters the catalog by query, domain, kind, availability, and registration status', async () => {
    const user = userEvent.setup()
    render(<DataConnectorRegistry />)
    await screen.findByText('高德场馆')

    await user.type(screen.getByLabelText('搜索连接器'), '天气')
    expect(screen.getByText('和风天气')).toBeInTheDocument()
    expect(screen.queryByText('高德场馆')).not.toBeInTheDocument()
    await user.clear(screen.getByLabelText('搜索连接器'))

    await user.selectOptions(screen.getByLabelText('连接器类型'), 'mcp')
    expect(screen.getByText('只读 MCP')).toBeInTheDocument()
    expect(screen.queryByText('和风天气')).not.toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('连接器类型'), '')

    await user.selectOptions(screen.getByLabelText('业务领域'), 'ticketing')
    expect(screen.getByText('大麦授权销售数据')).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('业务领域'), '')

    await user.selectOptions(screen.getByLabelText('接入条件'), 'available')
    expect(screen.queryByText('大麦授权销售数据')).not.toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('接入条件'), '')

    await user.selectOptions(screen.getByLabelText('注册状态'), 'ready')
    expect(screen.getByText('和风天气')).toBeInTheDocument()
    expect(screen.queryByText('高德场馆')).not.toBeInTheDocument()
  })

  it('registers from schema fields and only submits a credential reference', async () => {
    const user = userEvent.setup()
    registerDataSource.mockResolvedValue({ data: { code: 0, data: { id: 30 } } })
    render(<DataConnectorRegistry />)
    await screen.findByText('只读 MCP')

    const row = screen.getByText('只读 MCP').closest('[role="row"]')
    await user.click(within(row).getByRole('button', { name: '注册' }))
    const drawer = screen.getByRole('dialog', { name: '配置只读 MCP' })
    expect(within(drawer).getByLabelText('服务地址')).toBeInTheDocument()
    expect(within(drawer).getByLabelText('工具名称')).toBeInTheDocument()
    expect(within(drawer).queryByText('读取能力')).not.toBeInTheDocument()
    expect(within(drawer).getByLabelText('凭据引用')).toHaveAttribute('type', 'text')
    expect(within(drawer).getByText('DATA_CONNECTOR_SECRET_MCP_PROD')).toBeInTheDocument()

    await user.type(within(drawer).getByLabelText('服务地址'), 'https://mcp.example.com')
    await user.type(within(drawer).getByLabelText('工具名称'), 'read_page')
    await user.type(within(drawer).getByLabelText('凭据引用'), 'MCP_PROD')
    await user.click(within(drawer).getByRole('button', { name: '保存注册' }))

    await waitFor(() => expect(registerDataSource).toHaveBeenCalledWith({
      definition_key: 'custom_mcp',
      name: '只读 MCP',
      credential_ref: 'MCP_PROD',
      scope_config: {
        endpoint: 'https://mcp.example.com',
        tool_name: 'read_page',
      },
      schedule_config: {},
    }))
  })

  it('preserves boolean schema values instead of submitting string flags', async () => {
    const user = userEvent.setup()
    const apiDefinition = {
      ...definitions[2],
      id: 8,
      key: 'agent_api',
      name: '通用只读 API',
      source_kind: 'api',
      config_schema: {
        fields: [
          { name: 'endpoint', label: '服务地址', type: 'url', required: true },
          { name: 'read_only', label: '只读模式', type: 'boolean', required: true, default: true },
        ],
      },
    }
    listConnectorDefinitions.mockResolvedValue({ data: { code: 0, data: [apiDefinition] } })
    registerDataSource.mockResolvedValue({ data: { code: 0, data: { id: 31 } } })
    render(<DataConnectorRegistry />)

    const row = (await screen.findByText('通用只读 API')).closest('[role="row"]')
    await user.click(within(row).getByRole('button', { name: '注册' }))
    const drawer = screen.getByRole('dialog', { name: '配置通用只读 API' })
    expect(within(drawer).getByLabelText('只读模式')).toBeChecked()
    await user.type(within(drawer).getByLabelText('服务地址'), 'https://api.example.com')
    await user.click(within(drawer).getByLabelText('只读模式'))
    await user.click(within(drawer).getByRole('button', { name: '保存注册' }))

    expect(registerDataSource).toHaveBeenCalledWith(expect.objectContaining({
      scope_config: {
        endpoint: 'https://api.example.com',
        read_only: false,
      },
    }))
  })

  it('updates, tests, activates, and disables registrations from right-side actions', async () => {
    const user = userEvent.setup()
    updateDataSourceRegistration.mockResolvedValue({ data: { code: 0, data: {} } })
    testDataSourceRegistration.mockResolvedValue({ data: { code: 0, data: {} } })
    activateDataSourceRegistration.mockResolvedValue({ data: { code: 0, data: {} } })
    disableDataSourceRegistration.mockResolvedValue({ data: { code: 0, data: {} } })
    render(<DataConnectorRegistry />)
    await screen.findByText('高德场馆')

    const amapRow = screen.getByText('高德场馆').closest('[role="row"]')
    await user.click(within(amapRow).getByRole('button', { name: '配置' }))
    const drawer = screen.getByRole('dialog', { name: '配置高德场馆' })
    await user.type(within(drawer).getByLabelText('凭据引用'), 'AMAP_PROD')
    await user.click(within(drawer).getByRole('button', { name: '保存配置' }))
    await waitFor(() => expect(updateDataSourceRegistration).toHaveBeenCalledWith(11, expect.objectContaining({
      credential_ref: 'AMAP_PROD',
    })))

    const refreshedAmapRow = screen.getByText('高德场馆').closest('[role="row"]')
    await user.click(within(refreshedAmapRow).getByRole('button', { name: '测试' }))
    await waitFor(() => expect(testDataSourceRegistration).toHaveBeenCalledWith(11))

    const weatherRow = screen.getByText('和风天气').closest('[role="row"]')
    await user.click(within(weatherRow).getByRole('button', { name: '启用' }))
    await waitFor(() => expect(activateDataSourceRegistration).toHaveBeenCalledWith(14))
  })

  it('disables an active registration without deleting its catalog entry', async () => {
    const user = userEvent.setup()
    const activeDefinitions = definitions.map((definition) => definition.key === 'qweather'
      ? { ...definition, registration: { ...definition.registration, status: 'active' } }
      : definition)
    listConnectorDefinitions.mockResolvedValue({ data: { code: 0, data: activeDefinitions } })
    disableDataSourceRegistration.mockResolvedValue({ data: { code: 0, data: {} } })
    render(<DataConnectorRegistry />)

    const weatherRow = (await screen.findByText('和风天气')).closest('[role="row"]')
    await user.click(within(weatherRow).getByRole('button', { name: '停用' }))
    await waitFor(() => expect(disableDataSourceRegistration).toHaveBeenCalledWith(14))
  })

  it('creates a custom skill as metadata without exposing an execution or secret field', async () => {
    const user = userEvent.setup()
    createCustomConnectorDefinition.mockResolvedValue({ data: { code: 0, data: {} } })
    render(<DataConnectorRegistry />)
    await screen.findByText('高德场馆')

    await user.click(screen.getByRole('button', { name: '自定义连接器' }))
    const drawer = screen.getByRole('dialog', { name: '新建自定义连接器' })
    await user.type(within(drawer).getByLabelText('连接器名称'), '市场研究能力')
    await user.type(within(drawer).getByLabelText('连接器标识'), 'market_custom')
    await user.selectOptions(within(drawer).getByLabelText('连接器类型'), 'skill')
    await user.type(within(drawer).getByLabelText('业务领域'), 'research')
    expect(within(drawer).queryByLabelText(/命令|代码|密钥/)).not.toBeInTheDocument()
    await user.click(within(drawer).getByRole('button', { name: '创建连接器' }))

    expect(createCustomConnectorDefinition).toHaveBeenCalledWith(expect.objectContaining({
      key: 'market_custom',
      name: '市场研究能力',
      source_kind: 'skill',
      domain: 'research',
      config_schema: { fields: [] },
    }))
  })

  it('creates a custom API with a required public endpoint schema', async () => {
    const user = userEvent.setup()
    createCustomConnectorDefinition.mockResolvedValue({ data: { code: 0, data: {} } })
    render(<DataConnectorRegistry />)
    await screen.findByText('高德场馆')

    await user.click(screen.getByRole('button', { name: '自定义连接器' }))
    const drawer = screen.getByRole('dialog', { name: '新建自定义连接器' })
    await user.type(within(drawer).getByLabelText('连接器名称'), '票务只读接口')
    await user.type(within(drawer).getByLabelText('连接器标识'), 'ticket_read_api')
    await user.type(within(drawer).getByLabelText('业务领域'), 'ticketing')
    await user.click(within(drawer).getByRole('button', { name: '创建连接器' }))

    expect(createCustomConnectorDefinition).toHaveBeenCalledWith(expect.objectContaining({
      source_kind: 'api',
      config_schema: {
        fields: [
          { name: 'endpoint', label: '服务地址', type: 'url', required: true },
        ],
      },
    }))
  })

  it('shows a recoverable loading error and an explicit empty result', async () => {
    listConnectorDefinitions.mockRejectedValueOnce(new Error('offline'))
    const { rerender } = render(<DataConnectorRegistry />)
    expect(await screen.findByText('连接器目录加载失败，请重试。')).toBeInTheDocument()

    listConnectorDefinitions.mockResolvedValueOnce({ data: { code: 0, data: [] } })
    await userEvent.click(screen.getByRole('button', { name: '重新加载' }))
    rerender(<DataConnectorRegistry />)
    expect(await screen.findByText('当前筛选条件下没有连接器。')).toBeInTheDocument()
  })
})
