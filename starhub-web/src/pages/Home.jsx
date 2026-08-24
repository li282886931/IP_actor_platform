import { useEffect, useState } from 'react'
import { listShows } from '../api'
import ShowCard from '../components/ShowCard'

export default function Home({ role = 'C' }) {
  const [shows, setShows] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const res = await listShows()
        setShows(res.data.data || [])
      } catch (e) {
        console.error(e)
      }
      setLoading(false)
    }
    load()
  }, [])

  const kpis = [
    { label: '预估票房', value: '¥12.5M' },
    { label: '已售票数', value: '18,342' },
    { label: '宣发消耗', value: '¥432,000' },
    { label: '风险告警', value: 2 }
  ]

  if (role === 'B') {
    return (
      <div className="space-y-6">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>工作台首页</h2>
          <button className="ai-btn"><span className="spark">✨</span> 新建项目</button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginTop: 12 }}>
          {kpis.map(k => (
            <div key={k.label} className="card" style={{ padding: 16 }}>
              <div style={{ fontSize: 12, color: 'var(--text-gray)' }}>{k.label}</div>
              <div style={{ fontSize: 20, fontWeight: 700, marginTop: 8, color: 'var(--primary-light)' }}>{k.value}</div>
            </div>
          ))}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12, marginTop: 12 }}>
          <div className="card">🧠 艺人智策</div>
          <div className="card">📣 AI宣发</div>
          <div className="card">🎟 智慧票务</div>
        </div>

        <div className="card alert-danger" style={{ marginTop: 12 }}>高风险告警：艺人舆情异常，建议立即查看并处理。</div>
      </div>
    )
  }

  if (role === 'Brand') {
    return (
      <div className="space-y-6">
        <h2 style={{ fontSize: 20, fontWeight: 700 }}>品牌工作台</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 12, marginTop: 12 }}>
          <div className="card">受众画像（示例）</div>
          <div className="card">ROI 报表（示例）</div>
        </div>
        <div className="card" style={{ marginTop: 12 }}>✨ AI 生成定制品宣方案</div>
      </div>
    )
  }

  if (role === 'G') {
    return (
      <div className="space-y-6">
        <h2 style={{ fontSize: 20, fontWeight: 700 }}>城市文旅看板</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12, marginTop: 12 }}>
          <div className="card">跨城观演人数</div>
          <div className="card">预估餐饮住宿消费拉动</div>
          <div className="card">热力地图（占位）</div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <div style={{ flex: 1 }}>
          <div className="search-bar">
            <i className="fas fa-search muted"></i>
            <input placeholder="搜索演出 / 艺人" />
          </div>
        </div>
        <div>
          <button className="ai-btn"><span className="spark">✨</span> 为你推荐</button>
        </div>
      </div>

      <div className="card" style={{ padding: 16, marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700 }}>发现精彩演出</div>
            <div className="muted">AI 推荐 · 智能匹配你的口味</div>
          </div>
          <div className="tag">New</div>
        </div>
      </div>

      <div className="grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 16 }}>
        {loading && <div style={{ color: 'var(--text-gray)' }}>加载中…</div>}
        {shows.length === 0 && !loading && <div className="card" style={{ gridColumn: '1 / -1', color: 'var(--text-gray)' }}>暂无演出，后端启动并有 demo 数据时显示</div>}
        {shows.map(s => <ShowCard key={s.id} show={s} />)}
      </div>
    </div>
  )
}
