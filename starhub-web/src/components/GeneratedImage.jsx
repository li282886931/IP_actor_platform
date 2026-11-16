import { useEffect, useRef, useState } from 'react'
import { generateAIImage, getAIImage } from '../api'
import './GeneratedImage.css'

const sizes = [
  ['portrait_4_3', '竖版 3:4'], ['portrait_16_9', '竖版 9:16'],
  ['landscape_16_9', '横版 16:9'], ['landscape_4_3', '横版 4:3'],
  ['square', '方形'], ['square_hd', '高清方形'],
]

function readSavedId(key) {
  try { return key ? JSON.parse(localStorage.getItem(`${key}:image`) || '{}').id : null } catch { return null }
}

function imageData(response) {
  const value = response?.data?.data
  if (response?.data?.code !== 0 || !value?.id || !/^https:\/\//.test(value.image_url || '')) {
    throw new Error('未返回可访问的 HTTPS 图片链接')
  }
  return value
}

export default function GeneratedImage({ storageKey }) {
  const [prompt, setPrompt] = useState('')
  const [size, setSize] = useState('portrait_4_3')
  const [image, setImage] = useState(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [copyMessage, setCopyMessage] = useState('')
  const active = useRef(null)

  const fetchImage = async (id) => {
    const request = {}
    active.current = request
    setBusy('refresh')
    setError('')
    try {
      const data = imageData(await getAIImage(id))
      if (active.current !== request) return
      setImage(data)
      setCopyMessage('')
    } catch (failure) {
      if (active.current === request) setError(failure?.response?.data?.detail || failure.message || '图片链接获取失败，请重试')
    } finally {
      if (active.current === request) setBusy('')
    }
  }

  useEffect(() => {
    const id = readSavedId(storageKey)
    if (Number.isInteger(id) && id > 0) fetchImage(id)
    return () => { active.current = null }
  }, [storageKey])

  const generate = async (event) => {
    event.preventDefault()
    if (!storageKey || !prompt.trim() || busy) return
    const request = {}
    active.current = request
    setBusy('generate')
    setError('')
    setCopyMessage('')
    try {
      const data = imageData(await generateAIImage({
        prompt: prompt.trim(), image_size: size,
        generation_nonce: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      }))
      if (active.current !== request) return
      setImage(data)
      localStorage.setItem(`${storageKey}:image`, JSON.stringify({ id: data.id }))
    } catch (failure) {
      if (active.current === request) setError(failure?.response?.data?.detail || failure.message || '图片生成失败，请重试')
    } finally {
      if (active.current === request) setBusy('')
    }
  }

  const copy = async () => {
    const request = active.current
    try {
      await navigator.clipboard.writeText(image.image_url)
      if (request === active.current) setCopyMessage('链接已复制')
    } catch {
      if (request === active.current) setCopyMessage('复制失败，请打开原图复制地址')
    }
  }

  return (
    <section className="panel image-studio" aria-label="宣发图片">
      <div className="panel-heading">
        <div><span className="eyebrow">VISUAL STUDIO</span><h3>宣发图片</h3></div>
        <span className="status-badge">云端图片</span>
      </div>
      <div className="image-studio-layout">
        <form onSubmit={generate}>
          <label className="field">
            <span>图片创作描述</span>
            <textarea maxLength={2000} rows={4} value={prompt} onChange={event => setPrompt(event.target.value)}
              placeholder="描述舞台、灯光、色调与构图，例如：蓝金灯光下的写实音乐现场，观众剪影，画面不含文字。" />
          </label>
          <p className="image-studio-hint">生成创意画面。日期、票价和艺人权益请核验后另行排版。</p>
          <div className="image-studio-controls">
            <label className="field"><span>图片尺寸</span>
              <select value={size} onChange={event => setSize(event.target.value)}>
                {sizes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <button className="button button-primary" disabled={!storageKey || !prompt.trim() || Boolean(busy)} type="submit">
              {busy === 'generate' ? '正在生成并保存…' : '生成图片'}
            </button>
          </div>
          <div className="image-studio-status" aria-live="polite">
            {busy && <span>{busy === 'generate' ? '正在创作图片并上传云端，请稍候。' : '正在获取图片链接…'}</span>}
            {error && <p role="alert">{error}</p>}
            {copyMessage && <span>{copyMessage}</span>}
          </div>
        </form>
        <div className="image-studio-preview">
          {image ? <>
            <img src={image.image_url} alt="宣发创意图片" onError={() => setError('图片加载失败，请刷新链接或检查网络。')} />
            <div className="image-studio-meta">
              <span>{image.width} × {image.height} 像素 · {Math.ceil(image.size / 1024)} KB</span>
              <small>{image.expires_in_seconds ? '私有图片链接有时效，可刷新获取' : '图片已保存，可通过链接访问'}</small>
            </div>
            <div className="image-studio-actions">
              <a className="button button-text" href={image.image_url} target="_blank" rel="noopener noreferrer">打开原图</a>
              <button className="button button-text" type="button" onClick={copy}>复制链接</button>
              <button className="button button-text" type="button" disabled={Boolean(busy)} onClick={() => fetchImage(image.id)}>刷新链接</button>
            </div>
          </> : <div className="image-studio-empty"><strong>图片预览</strong><span>填写画面描述后生成，图片保存后在这里展示。</span></div>}
        </div>
      </div>
    </section>
  )
}
