import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { agentChat, listAgentSources } from '../api'
import './LiveAnalysis.css'

function publicLink(value) {
  try {
    const url = new URL(value)
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null
  } catch { return null }
}

function excerptText(reading) {
  const text = reading.excerpt || ''
  try {
    const data = JSON.parse(text)
    if (typeof data.text === 'string') return data.text
    const labels = { capacity: '容量', unit: '单位', city: '城市', venue: '场馆', name: '名称',
      price: '价格', count: '数量', date: '日期', status: '状态', total: '总计' }
    return Object.entries(data).map(([key, value]) =>
      `${labels[key] || key}：${value && typeof value === 'object' ? '展开查看内容' : value}`).join('；')
  } catch { return text }
}

export default function LiveAnalysis({ projectId, onEvidenceChanged }) {
  const [sources, setSources] = useState([])
  const [sourceStatus, setSourceStatus] = useState('loading')
  const [selected, setSelected] = useState([])
  const [urls, setUrls] = useState({})
  const [question, setQuestion] = useState('')
  const [useAI, setUseAI] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [attempt, setAttempt] = useState(0)
  const alive = useRef(true)

  useEffect(() => {
    alive.current = true
    let active = true
    setSourceStatus('loading')
    Promise.resolve().then(() => listAgentSources(projectId)).then(response => {
      if (active) { setSources(response.data.data || []); setSourceStatus('success') }
    }).catch(() => { if (active) setSourceStatus('error') })
    return () => { active = false; alive.current = false }
  }, [projectId, attempt])

  async function submit(event) {
    event.preventDefault()
    if (busy || !question.trim()) return
    setError('')
    const reads = []
    for (const source of sources.filter(item => selected.includes(item.id))) {
      const url = urls[source.id]?.trim()
      if (source.requires_url && !publicLink(url)) {
        setError(`请填写 ${source.name} 的有效 HTTP／HTTPS 网页地址。`)
        return
      }
      reads.push({ source_id: source.id, ...(source.requires_url ? { url } : {}) })
    }
    setBusy(true)
    try {
      const response = await agentChat({ project_id: projectId, message: question.trim(), reads, use_ai: useAI })
      if (!alive.current) return
      const data = response.data.data
      setResult(data)
      if (data.readings?.some(item => item.evidence_id) && onEvidenceChanged) {
        try { await onEvidenceChanged() } catch { setError('研判已完成，证据列表刷新失败，请刷新页面查看。') }
      }
    } catch {
      if (alive.current) setError('研判请求失败，请检查项目授权和服务后重试；输入内容已保留。')
    } finally {
      if (alive.current) setBusy(false)
    }
  }

  return <article className="panel live-analysis" aria-busy={busy}>
    <div className="panel-heading"><div><h3>智能体建议</h3><p>可读取实时网页和接口资料，再形成分析研判。</p></div></div>
    <form className="compact-form" onSubmit={submit}>
      <fieldset disabled={busy} className="live-analysis-fields">
        <legend>实时数据来源</legend>
        {sourceStatus === 'loading' && <p className="role-muted">正在加载可用来源…</p>}
        {sourceStatus === 'error' && <p className="role-muted">来源暂不可用，请检查项目授权。<button type="button" className="button button-secondary" onClick={() => setAttempt(n => n + 1)}>重试加载</button></p>}
        {sourceStatus === 'success' && sources.length === 0 && <p className="role-muted">当前项目暂无已授权网页或 API 来源，可先使用项目资料研判。</p>}
        {sources.map(source => <div className="live-source" key={source.id}>
          <label className="live-source-choice"><input type="checkbox" checked={selected.includes(source.id)}
            disabled={source.status !== 'ready' || (!selected.includes(source.id) && selected.length >= 4)}
            onChange={event => setSelected(current => event.target.checked ? [...current, source.id] : current.filter(id => id !== source.id))} />
            <strong>{source.name}</strong></label>
          <small>{source.kind === 'mcp_web' ? 'MCP 网页读取' : 'Agent API 查询'} · {source.status === 'ready' ? '可读取' : '待配置'}</small>
          {selected.includes(source.id) && source.requires_url && <label className="field">
            <span>网页地址 · {source.name}</span><input value={urls[source.id] || ''} placeholder="输入要核验的公开网页地址"
              onChange={event => setUrls(current => ({ ...current, [source.id]: event.target.value }))} />
          </label>}
        </div>)}
        <label className="field"><span>向智能体提问</span>
          <input value={question} onChange={event => setQuestion(event.target.value)} placeholder="询问下一步处理建议" />
        </label>
        <label className="live-source-choice"><input type="checkbox" checked={useAI} onChange={event => setUseAI(event.target.checked)} />AI 综合研判（可选）</label>
        <button className="button button-primary" type="submit" disabled={!question.trim()}>{busy ? '正在读取与研判…' : '询问智能体'}</button>
      </fieldset>
    </form>
    {busy && <p role="status" className="role-muted">正在读取选定来源，请稍候；AI 综合研判可能需要较长时间。</p>}
    {error && <div role="alert" className="inline-message error">{error}</div>}
    {result && <div className="live-analysis-result" aria-live="polite">
      {result.warning && <p className="role-disclosure">{result.warning}</p>}
      <div className="agent-answer"><ReactMarkdown>{result.answer || ''}</ReactMarkdown></div>
      {(result.readings || []).map((reading, index) => <div className="live-reading" key={`${reading.source_id}:${index}`}>
        <strong>[{index + 1}] {reading.source_name}</strong>
        {reading.status === 'completed' ? <>
          <small>证据 #{reading.evidence_id} · 待人工核验</small>
          <p>{excerptText(reading)}</p>
          <small>读取时间：{reading.captured_at ? new Date(reading.captured_at).toLocaleString('zh-CN') : '未返回'}</small>
          {publicLink(reading.source_uri) && <a href={publicLink(reading.source_uri)} target="_blank" rel="noreferrer">查看原始来源</a>}
          <details><summary>展开读取内容{reading.truncated ? '（已截断）' : ''}</summary><pre>{reading.content}</pre></details>
        </> : <p className="role-muted">{reading.status === 'blocked' ? '待配置' : '读取失败'}：{reading.error}</p>}
      </div>)}
      <p className="role-disclosure">网页和接口结果均需核验来源、日期与适用范围；研判建议不自动修改财务参数或通过审批。</p>
    </div>}
  </article>
}
