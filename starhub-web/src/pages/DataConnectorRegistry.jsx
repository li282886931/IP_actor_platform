import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  activateDataSourceRegistration,
  createCustomConnectorDefinition,
  disableDataSourceRegistration,
  listConnectorDefinitions,
  registerDataSource,
  testDataSourceRegistration,
  updateDataSourceRegistration,
} from '../api'

const BLOCKED_AVAILABILITY = new Set(['adapter_required', 'contract_required', 'runner_required', 'disabled'])

const availabilityLabels = {
  available: '可注册',
  adapter_required: '待适配器',
  contract_required: '待商务授权',
  runner_required: '待执行器注册',
  disabled: '已停用',
}

const statusLabels = {
  unregistered: '待注册',
  pending_config: '待配置',
  pending_credentials: '待鉴权',
  pending_test: '待测试',
  testing: '测试中',
  ready: '待启用',
  active: '已启用',
  error: '异常',
  disabled: '已停用',
}

const kindLabels = { api: 'API', mcp: 'MCP', skill: 'Skill', file: '文件' }

const initialFilters = { query: '', kind: '', domain: '', availability: '', status: '' }

const publicFields = (definition) => ((definition.config_schema || {}).fields || [])
  .filter((field) => !/secret|password|token|api[_-]?key/i.test(`${field.name || ''} ${field.type || ''}`))

const registrationStatus = (row) => row.registration?.status || 'unregistered'

export const connectorAction = (row) => {
  if (BLOCKED_AVAILABILITY.has(row.availability)) return 'blocked'
  if (!row.registration) return 'register'
  if (row.registration.status === 'active') return 'active'
  if (row.registration.status === 'pending_config') return 'configure'
  if (row.registration.status === 'pending_credentials') return 'credentials'
  if (row.registration.status === 'pending_test') return 'test'
  if (row.registration.status === 'testing') return 'testing'
  if (row.registration.status === 'ready') return 'activate'
  if (row.registration.status === 'error') return 'retry'
  return 'test'
}

const credentialExample = (definition, value) => {
  if (value) return `DATA_CONNECTOR_SECRET_${value}`
  if (definition.source_kind === 'mcp') return 'DATA_CONNECTOR_SECRET_MCP_PROD'
  return `DATA_CONNECTOR_SECRET_${String(definition.key || 'CONNECTOR').toUpperCase()}_PROD`
}

const customConfigSchema = (sourceKind) => {
  if (sourceKind === 'api') {
    return {
      fields: [{ name: 'endpoint', label: '服务地址', type: 'url', required: true }],
    }
  }
  if (sourceKind === 'mcp') {
    return {
      fields: [
        { name: 'endpoint', label: '服务地址', type: 'url', required: true },
        { name: 'tool', label: '工具名称', type: 'text', required: true },
        { name: 'url_argument', label: 'URL 参数名', type: 'text', required: true, default: 'url' },
      ],
    }
  }
  return { fields: [] }
}

function ConfigDrawer({ row, busy, onClose, onSaved }) {
  const registration = row.registration
  const fields = publicFields(row)
  const [name, setName] = useState(registration?.name || row.name)
  const [credentialRef, setCredentialRef] = useState(registration?.credential_ref || '')
  const [values, setValues] = useState(() => Object.fromEntries(fields.map((field) => [
    field.name,
    registration?.scope_config?.[field.name] ?? field.default ?? '',
  ])))
  const [error, setError] = useState('')

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    const scopeConfig = Object.fromEntries(fields.map((field) => [
      field.name,
      field.type === 'number' && values[field.name] !== '' ? Number(values[field.name]) : values[field.name],
    ]))
    try {
      if (registration) {
        await updateDataSourceRegistration(registration.id, {
          credential_ref: credentialRef.trim(),
          scope_config: scopeConfig,
          schedule_config: registration.schedule_config || {},
        })
      } else {
        await registerDataSource({
          definition_key: row.key,
          name: name.trim() || row.name,
          credential_ref: credentialRef.trim(),
          scope_config: scopeConfig,
          schedule_config: {},
        })
      }
      await onSaved()
    } catch {
      setError('配置保存失败，请检查字段后重试。')
    }
  }

  return (
    <div className="connector-drawer-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <aside className="connector-drawer" role="dialog" aria-modal="true" aria-label={`配置${row.name}`}>
        <div className="connector-drawer-heading">
          <div>
            <h3>配置{row.name}</h3>
            <p>这里只保存公开参数和凭据引用，真实密钥由服务器环境变量提供。</p>
          </div>
          <button className="connector-close" type="button" onClick={onClose} aria-label="关闭配置">关闭</button>
        </div>
        <form className="connector-form" onSubmit={handleSubmit}>
          {!registration && (
            <label className="field">
              <span>注册名称</span>
              <input value={name} onChange={(event) => setName(event.target.value)} required />
            </label>
          )}
          {fields.map((field) => (
            <label className={`field${field.type === 'boolean' ? ' connector-boolean-field' : ''}`} key={field.name}>
              <span>{field.label || field.name}</span>
              {field.type === 'boolean' ? (
                <input
                  type="checkbox"
                  checked={Boolean(values[field.name])}
                  onChange={(event) => setValues((current) => ({ ...current, [field.name]: event.target.checked }))}
                />
              ) : field.type === 'select' ? (
                <select
                  value={values[field.name]}
                  onChange={(event) => setValues((current) => ({ ...current, [field.name]: event.target.value }))}
                  required={field.required}
                >
                  {!field.required && <option value="">不设置</option>}
                  {(field.options || []).map((option) => {
                    const value = typeof option === 'object' ? option.value : option
                    const label = typeof option === 'object' ? option.label : option
                    return <option key={value} value={value}>{label}</option>
                  })}
                </select>
              ) : field.type === 'textarea' ? (
                <textarea
                  value={values[field.name]}
                  onChange={(event) => setValues((current) => ({ ...current, [field.name]: event.target.value }))}
                  required={field.required}
                  rows="3"
                />
              ) : (
                <input
                  type={field.type === 'url' || field.type === 'number' ? field.type : 'text'}
                  value={values[field.name]}
                  onChange={(event) => setValues((current) => ({ ...current, [field.name]: event.target.value }))}
                  required={field.required}
                />
              )}
            </label>
          ))}
          <label className="field">
            <span>凭据引用</span>
            <input
              aria-label="凭据引用"
              type="text"
              value={credentialRef}
              onChange={(event) => setCredentialRef(event.target.value)}
              pattern="[A-Za-z0-9_-]*"
              placeholder={row.auth_type === 'none' ? '无需鉴权，可留空' : '例如 AMAP_PROD'}
            />
            <small>服务器变量：<code>{credentialExample(row, credentialRef.trim())}</code></small>
          </label>
          {error && <div className="inline-message error">{error}</div>}
          <div className="connector-form-actions">
            <button className="button button-secondary" type="button" onClick={onClose}>取消</button>
            <button className="button button-primary" type="submit" disabled={busy}>
              {busy ? '保存中...' : registration ? '保存配置' : '保存注册'}
            </button>
          </div>
        </form>
      </aside>
    </div>
  )
}

function CustomConnectorDrawer({ busy, onClose, onSaved }) {
  const [form, setForm] = useState({
    key: '',
    name: '',
    source_kind: 'api',
    domain: '',
    description: '',
    auth_type: 'none',
  })
  const [error, setError] = useState('')
  const setField = (field, value) => setForm((current) => ({ ...current, [field]: value }))

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    try {
      await createCustomConnectorDefinition({
        ...form,
        key: form.key.trim(),
        name: form.name.trim(),
        domain: form.domain.trim(),
        description: form.description.trim(),
        capabilities: ['read'],
        config_schema: customConfigSchema(form.source_kind),
      })
      await onSaved()
    } catch {
      setError('自定义连接器创建失败，请检查标识是否重复。')
    }
  }

  return (
    <div className="connector-drawer-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <aside className="connector-drawer" role="dialog" aria-modal="true" aria-label="新建自定义连接器">
        <div className="connector-drawer-heading">
          <div>
            <h3>新建自定义连接器</h3>
            <p>创建受控元数据；Skill 仍需服务器注册执行器后才能测试。</p>
          </div>
          <button className="connector-close" type="button" onClick={onClose} aria-label="关闭自定义连接器">关闭</button>
        </div>
        <form className="connector-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>连接器名称</span>
            <input value={form.name} onChange={(event) => setField('name', event.target.value)} required />
          </label>
          <label className="field">
            <span>连接器标识</span>
            <input value={form.key} onChange={(event) => setField('key', event.target.value)} pattern="[a-z][a-z0-9_]+" required />
          </label>
          <label className="field">
            <span>连接器类型</span>
            <select value={form.source_kind} onChange={(event) => setField('source_kind', event.target.value)}>
              <option value="api">API</option>
              <option value="mcp">MCP</option>
              <option value="skill">Skill</option>
            </select>
          </label>
          <label className="field">
            <span>业务领域</span>
            <input value={form.domain} onChange={(event) => setField('domain', event.target.value)} required />
          </label>
          <label className="field">
            <span>鉴权方式</span>
            <select value={form.auth_type} onChange={(event) => setField('auth_type', event.target.value)}>
              <option value="none">无需鉴权</option>
              <option value="api_key">API Key 引用</option>
              <option value="bearer">Bearer 引用</option>
              <option value="oauth2">OAuth2 引用</option>
              <option value="basic">Basic 引用</option>
              <option value="signature">签名凭据引用</option>
            </select>
          </label>
          <label className="field connector-field-wide">
            <span>能力说明</span>
            <textarea value={form.description} onChange={(event) => setField('description', event.target.value)} rows="3" />
          </label>
          {error && <div className="inline-message error connector-field-wide">{error}</div>}
          <div className="connector-form-actions connector-field-wide">
            <button className="button button-secondary" type="button" onClick={onClose}>取消</button>
            <button className="button button-primary" type="submit" disabled={busy}>
              {busy ? '创建中...' : '创建连接器'}
            </button>
          </div>
        </form>
      </aside>
    </div>
  )
}

function ConnectorActions({ row, busy, onConfigure, onMutation }) {
  const action = connectorAction(row)
  if (action === 'blocked') return <span className="connector-condition">{availabilityLabels[row.availability]}</span>
  if (action === 'register') return <button className="button button-secondary connector-button" type="button" onClick={onConfigure}>注册</button>
  if (action === 'testing') return <button className="button button-secondary connector-button" type="button" disabled>测试中...</button>
  if (action === 'activate') return (
    <>
      <button className="button button-secondary connector-button" type="button" onClick={onConfigure}>配置</button>
      <button className="button button-primary connector-button" type="button" disabled={busy} onClick={() => onMutation('activate')}>启用</button>
    </>
  )
  if (action === 'active') return (
    <>
      <button className="button button-secondary connector-button" type="button" onClick={onConfigure}>配置</button>
      <button className="button button-secondary connector-button" type="button" disabled={busy} onClick={() => onMutation('test')}>测试</button>
      <button className="button button-secondary connector-button" type="button" disabled={busy} onClick={() => onMutation('disable')}>停用</button>
    </>
  )
  return (
    <>
      <button className="button button-secondary connector-button" type="button" onClick={onConfigure}>配置</button>
      {(action === 'credentials' || action === 'retry' || action === 'test') && (
        <button className="button button-secondary connector-button" type="button" disabled={busy} onClick={() => onMutation('test')}>
          {action === 'retry' ? '重新测试' : '测试'}
        </button>
      )}
    </>
  )
}

export default function DataConnectorRegistry() {
  const [definitions, setDefinitions] = useState([])
  const [status, setStatus] = useState('loading')
  const [filters, setFilters] = useState(initialFilters)
  const [drawer, setDrawer] = useState(null)
  const [busy, setBusy] = useState('')
  const [message, setMessage] = useState('')

  const loadDefinitions = useCallback(async () => {
    setStatus('loading')
    setMessage('')
    try {
      const response = await listConnectorDefinitions()
      setDefinitions(Array.isArray(response.data?.data) ? response.data.data : [])
      setStatus('success')
    } catch {
      setStatus('error')
    }
  }, [])

  useEffect(() => {
    loadDefinitions()
  }, [loadDefinitions])

  const domains = useMemo(() => [...new Set(definitions.map((row) => row.domain).filter(Boolean))].sort(), [definitions])
  const rows = useMemo(() => definitions.filter((row) => {
    const query = filters.query.trim().toLowerCase()
    if (query && !`${row.name} ${row.key} ${row.description || ''}`.toLowerCase().includes(query)) return false
    if (filters.kind && row.source_kind !== filters.kind) return false
    if (filters.domain && row.domain !== filters.domain) return false
    if (filters.availability && row.availability !== filters.availability) return false
    if (filters.status && registrationStatus(row) !== filters.status) return false
    return true
  }), [definitions, filters])

  const summary = useMemo(() => ({
    total: definitions.length,
    unregistered: definitions.filter((row) => row.availability === 'available' && !row.registration).length,
    credentials: definitions.filter((row) => row.registration?.status === 'pending_credentials').length,
    active: definitions.filter((row) => row.registration?.status === 'active').length,
    error: definitions.filter((row) => row.registration?.status === 'error').length,
  }), [definitions])

  const closeAndReload = async () => {
    setDrawer(null)
    setBusy('')
    await loadDefinitions()
  }

  const mutate = async (row, operation) => {
    const id = row.registration?.id
    if (!id) return
    setBusy(`${id}:${operation}`)
    setMessage('')
    try {
      if (operation === 'test') await testDataSourceRegistration(id)
      if (operation === 'activate') await activateDataSourceRegistration(id)
      if (operation === 'disable') await disableDataSourceRegistration(id)
      await loadDefinitions()
    } catch {
      setMessage(`${row.name}${operation === 'test' ? '连接测试' : operation === 'activate' ? '启用' : '停用'}失败，请重试。`)
    } finally {
      setBusy('')
    }
  }

  const updateFilter = (field, value) => setFilters((current) => ({ ...current, [field]: value }))

  return (
    <div className="page-stack connector-registry">
      <section className="page-lead connector-lead">
        <div>
          <h2>数据连接器</h2>
          <p>登记能力不等于已接通，启用前必须完成公开参数配置、服务器鉴权和连接测试。</p>
        </div>
        <button className="button button-primary" type="button" onClick={() => setDrawer({ type: 'custom' })}>
          自定义连接器
        </button>
      </section>

      <dl className="workspace-summary-strip connector-summary">
        <div aria-label="目录总数"><dt>目录总数</dt><dd>{summary.total}</dd></div>
        <div aria-label="待注册"><dt>待注册</dt><dd>{summary.unregistered}</dd></div>
        <div aria-label="待鉴权"><dt>待鉴权</dt><dd>{summary.credentials}</dd></div>
        <div aria-label="已启用"><dt>已启用</dt><dd>{summary.active}</dd></div>
        <div aria-label="异常"><dt>异常</dt><dd>{summary.error}</dd></div>
      </dl>

      <section className="connector-toolbar" aria-label="连接器筛选">
        <label className="connector-search">
          <span className="sr-only">搜索连接器</span>
          <input
            aria-label="搜索连接器"
            value={filters.query}
            onChange={(event) => updateFilter('query', event.target.value)}
            placeholder="搜索名称、标识或能力"
          />
        </label>
        <label>
          <span>业务领域</span>
          <select aria-label="业务领域" value={filters.domain} onChange={(event) => updateFilter('domain', event.target.value)}>
            <option value="">全部领域</option>
            {domains.map((domain) => <option key={domain} value={domain}>{domain}</option>)}
          </select>
        </label>
        <label>
          <span>连接器类型</span>
          <select aria-label="连接器类型" value={filters.kind} onChange={(event) => updateFilter('kind', event.target.value)}>
            <option value="">全部类型</option>
            <option value="api">API</option>
            <option value="mcp">MCP</option>
            <option value="skill">Skill</option>
            <option value="file">文件</option>
          </select>
        </label>
        <label>
          <span>接入条件</span>
          <select aria-label="接入条件" value={filters.availability} onChange={(event) => updateFilter('availability', event.target.value)}>
            <option value="">全部条件</option>
            {Object.entries(availabilityLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label>
          <span>注册状态</span>
          <select aria-label="注册状态" value={filters.status} onChange={(event) => updateFilter('status', event.target.value)}>
            <option value="">全部状态</option>
            {Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
      </section>

      {message && <div className="inline-message error">{message}</div>}
      {status === 'loading' && <div className="state-panel">正在加载连接器目录...</div>}
      {status === 'error' && (
        <div className="state-panel error connector-load-error">
          <span>连接器目录加载失败，请重试。</span>
          <button className="button button-secondary" type="button" onClick={loadDefinitions}>重新加载</button>
        </div>
      )}
      {status === 'success' && (
        <section className="connector-table" role="table" aria-label="连接器目录">
          <div className="connector-table-head" role="row">
            <span role="columnheader">连接器</span>
            <span role="columnheader">类型 / 领域</span>
            <span role="columnheader">接入条件</span>
            <span role="columnheader">空间状态</span>
            <span role="columnheader">鉴权 / 测试</span>
            <span role="columnheader">操作</span>
          </div>
          {rows.map((row) => {
            const rowStatus = registrationStatus(row)
            const action = connectorAction(row)
            return (
              <article className="connector-row" role="row" key={row.id || row.key}>
                <div className="connector-main" role="cell">
                  <strong>{row.name}</strong>
                  <code>{row.key}</code>
                  <small>{row.description || '暂无能力说明'}</small>
                </div>
                <div className="connector-cell" role="cell" data-label="类型 / 领域">
                  <strong>{kindLabels[row.source_kind] || row.source_kind}</strong>
                  <small>{row.domain || '未分类'} · {(row.capabilities || []).join(' / ') || '能力待确认'}</small>
                </div>
                <div className="connector-cell" role="cell" data-label="接入条件">
                  <span className={`status-badge ${row.availability === 'available' ? 'positive' : 'warning'}`}>
                    {availabilityLabels[row.availability] || row.availability}
                  </span>
                </div>
                <div className="connector-cell" role="cell" data-label="空间状态">
                  <span className={`status-badge ${rowStatus === 'active' ? 'positive' : rowStatus === 'error' ? 'error' : 'warning'}`}>
                    {statusLabels[rowStatus] || rowStatus}
                  </span>
                </div>
                <div className="connector-cell connector-test-meta" role="cell" data-label="鉴权 / 测试">
                  <strong>{row.registration?.credential_status === 'configured' ? '鉴权已配置' : row.auth_type === 'none' ? '无需鉴权' : '鉴权未配置'}</strong>
                  <small>{row.registration?.last_test_at ? new Date(row.registration.last_test_at).toLocaleString('zh-CN') : '尚未测试'}</small>
                </div>
                <div className="connector-actions" role="cell" data-label="操作">
                  <ConnectorActions
                    row={row}
                    busy={busy.startsWith(`${row.registration?.id}:`)}
                    onConfigure={() => setDrawer({ type: 'config', row })}
                    onMutation={(operation) => mutate(row, operation)}
                  />
                  {action === 'blocked' && <small>{row.availability === 'contract_required' ? '需取得合法授权后接入' : '当前不具备运行条件'}</small>}
                </div>
              </article>
            )
          })}
          {rows.length === 0 && <div className="state-panel connector-empty">当前筛选条件下没有连接器。</div>}
        </section>
      )}

      {drawer?.type === 'config' && (
        <ConfigDrawer row={drawer.row} busy={Boolean(busy)} onClose={() => setDrawer(null)} onSaved={closeAndReload} />
      )}
      {drawer?.type === 'custom' && (
        <CustomConnectorDrawer busy={Boolean(busy)} onClose={() => setDrawer(null)} onSaved={closeAndReload} />
      )}
    </div>
  )
}
