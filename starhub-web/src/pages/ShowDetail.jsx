import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getShow, mockOrder } from '../api'

export default function ShowDetail({ role = 'C' }) {
  const { id } = useParams()
  const [show, setShow] = useState(null)
  const [status, setStatus] = useState('loading')
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [orderStatus, setOrderStatus] = useState('idle')
  const [message, setMessage] = useState('')

  useEffect(() => {
    let active = true
    setStatus('loading')

    getShow(id)
      .then((response) => {
        if (!active) return
        setShow(response.data.data)
        setStatus('success')
      })
      .catch(() => {
        if (active) setStatus('error')
      })

    return () => {
      active = false
    }
  }, [id])

  const handleOrder = async (event) => {
    event.preventDefault()
    if (!name.trim() || !phone.trim()) {
      setMessage('请填写姓名与手机号')
      return
    }

    setOrderStatus('loading')
    setMessage('')
    try {
      await mockOrder(id, { name: name.trim(), phone: phone.trim() })
      setOrderStatus('success')
      setMessage('预约成功，我们将通过手机号同步后续信息。')
    } catch {
      setOrderStatus('error')
      setMessage('预约失败，请稍后重试。')
    }
  }

  if (status === 'loading') {
    return <div className="state-panel">正在加载演出详情...</div>
  }

  if (status === 'error' || !show) {
    return (
      <div className="state-panel error">
        <strong>未能加载演出详情</strong>
        <span>请返回演出列表后重试。</span>
        <Link className="button button-secondary" to="/">返回工作台</Link>
      </div>
    )
  }

  const imagePrompt = encodeURIComponent(
    `Realistic live concert photography for ${show.artist_name || show.title}, full stage and audience, premium editorial event photography, no text`,
  )
  const imageUrl = show.poster_url || `https://copilot-cn.bytedance.net/api/ide/v1/text_to_image?prompt=${imagePrompt}&image_size=landscape_16_9`

  return (
    <div className="page-stack">
      <Link className="back-link" to="/">← 返回演出列表</Link>

      <section className="show-detail-grid">
        <article className="panel show-detail-main">
          <div className="detail-image-wrap">
            <img className="detail-image" src={imageUrl} alt={`${show.title}演出现场`} />
            <span className="show-status">{show.status === 'on_sale' ? '售票中' : '即将开售'}</span>
          </div>

          <div className="detail-heading">
            <div>
              <span className="eyebrow">{show.artist_name || 'LIVE EVENT'}</span>
              <h2>{show.title}</h2>
              <p>{show.description || '演出详情持续更新中。'}</p>
            </div>
            <strong className="detail-price">¥{show.price}<small> 起</small></strong>
          </div>

          <dl className="detail-facts">
            <div><dt>演出日期</dt><dd>{show.date || '待公布'}</dd></div>
            <div><dt>举办城市</dt><dd>{show.city || '待公布'}</dd></div>
            <div><dt>演出场馆</dt><dd>{show.venue || '待公布'}</dd></div>
            <div><dt>当前状态</dt><dd>{show.status === 'on_sale' ? '公开售票' : show.status}</dd></div>
          </dl>
        </article>

        {role === 'C' ? (
          <aside className="panel booking-panel">
            <div className="panel-heading">
              <div>
                <span className="eyebrow">RESERVATION</span>
                <h3>预约演出</h3>
              </div>
            </div>
            <p>提交预约后，我们会通过手机号同步开票与场次信息。</p>
            <form className="booking-form" onSubmit={handleOrder}>
              <label className="field">
                <span>姓名</span>
                <input value={name} onChange={(event) => setName(event.target.value)} placeholder="请输入姓名" />
              </label>
              <label className="field">
                <span>手机号</span>
                <input value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="请输入手机号" />
              </label>
              <button className="button button-primary button-block" disabled={orderStatus === 'loading'} type="submit">
                {orderStatus === 'loading' ? '提交中...' : '立即预约'}
              </button>
            </form>
            {message && <div className={`inline-message ${orderStatus === 'success' ? 'success' : 'error'}`}>{message}</div>}
          </aside>
        ) : (
          <aside className="panel booking-panel">
            <div className="panel-heading">
              <div>
                <span className="eyebrow">PROJECT STATUS</span>
                <h3>项目概况</h3>
              </div>
            </div>
            <div className="summary-list">
              <span>售票状态<strong>正常</strong></span>
              <span>宣发素材<strong>6 项</strong></span>
              <span>风险等级<strong>低</strong></span>
            </div>
            <Link className="button button-primary button-block" to="/generate">生成宣发内容</Link>
          </aside>
        )}
      </section>
    </div>
  )
}
