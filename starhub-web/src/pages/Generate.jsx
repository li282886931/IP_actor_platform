import { useState } from 'react'

import { generateAI } from '../api'

const contentTypes = [
  { value: 'poster', label: '海报文案', description: '适合票务页、社交平台与线下物料' },
  { value: 'video_script', label: '短视频脚本', description: '生成分镜节奏与口播内容' },
]

export default function Generate({ role = 'B' }) {
  const [form, setForm] = useState({ type: 'poster', show_name: '', artist: '', city: '' })
  const [result, setResult] = useState('')
  const [status, setStatus] = useState('idle')
  const [copyStatus, setCopyStatus] = useState('')

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }))
  }

  const handleGenerate = async (event) => {
    event?.preventDefault()
    setStatus('loading')
    setCopyStatus('')
    setResult('')
    try {
      const response = await generateAI({
        ...form,
        generation_nonce: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      })
      setResult(response.data?.data?.result || response.data?.result || JSON.stringify(response.data))
      setStatus('success')
    } catch {
      setResult('')
      setStatus('error')
    }
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(result)
      setCopyStatus('已复制')
    } catch {
      setCopyStatus('复制失败')
    }
  }

  return (
    <div className="page-stack">
      <section className="page-lead">
        <div>
          <span className="eyebrow">AI CONTENT STUDIO</span>
          <h2>{role === 'Brand' ? '品牌内容生成' : 'AI 宣发内容生成'}</h2>
          <p>输入演出核心信息，快速生成可直接编辑和投放的宣传内容。</p>
        </div>
        <span className="status-badge positive">Qwen 文本能力</span>
      </section>

      <div className="generator-layout">
        <form className="panel generator-form" onSubmit={handleGenerate}>
          <div className="panel-heading">
            <div>
              <span className="eyebrow">CONTENT BRIEF</span>
              <h3>创作需求</h3>
            </div>
            <span className="step-indicator">01</span>
          </div>

          <fieldset className="field">
            <legend>内容类型</legend>
            <div className="segmented-control">
              {contentTypes.map((type) => (
                <label className={form.type === type.value ? 'selected' : ''} key={type.value}>
                  <input
                    checked={form.type === type.value}
                    name="content-type"
                    onChange={() => updateField('type', type.value)}
                    type="radio"
                    value={type.value}
                  />
                  <strong>{type.label}</strong>
                  <small>{type.description}</small>
                </label>
              ))}
            </div>
          </fieldset>

          <div className="form-grid">
            <label className="field field-wide">
              <span>演出名称</span>
              <input
                placeholder="例如：周杰伦嘉年华世界巡回演唱会"
                value={form.show_name}
                onChange={(event) => updateField('show_name', event.target.value)}
              />
            </label>
            <label className="field">
              <span>艺人</span>
              <input
                placeholder="输入艺人名称"
                value={form.artist}
                onChange={(event) => updateField('artist', event.target.value)}
              />
            </label>
            <label className="field">
              <span>城市</span>
              <input
                placeholder="输入演出城市"
                value={form.city}
                onChange={(event) => updateField('city', event.target.value)}
              />
            </label>
          </div>

          <div className="form-actions">
            <button className="button button-primary" disabled={status === 'loading'} type="submit">
              {status === 'loading' ? (
                <><span className="loader" aria-hidden="true" />AI 生成中...</>
              ) : '一键生成'}
            </button>
            <span>生成结果仍可继续编辑和复制</span>
          </div>
        </form>

        <section className="panel result-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">OUTPUT</span>
              <h3>生成结果</h3>
            </div>
            {result && (
              <button className="button button-text" onClick={handleCopy} type="button">
                {copyStatus || '复制文案'}
              </button>
            )}
          </div>

          {status === 'error' && (
            <div className="state-panel error">
              <strong>内容生成失败</strong>
              <span>请检查后端服务或稍后重试。</span>
            </div>
          )}
          {result ? (
            <article className="generated-copy">{result}</article>
          ) : status !== 'error' && (
            <div className="result-placeholder">
              <span className="result-placeholder-mark" aria-hidden="true">AI</span>
              <strong>等待生成内容</strong>
              <p>完成左侧创作需求后，结果将在这里显示。</p>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
