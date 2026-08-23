import { useEffect, useState } from 'react'
import { listShows } from '../api'
import ShowCard from '../components/ShowCard'

export default function Home({role='C'}){
  const [shows, setShows] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(()=>{ async function load(){ setLoading(true); try{ const res = await listShows(); setShows(res.data.data || []) }catch(e){ console.error(e) } setLoading(false) } load() },[])

  // Mock KPI data for B-side dashboard
  const kpis = [
    {label: '预估票房', value: '¥12.5M'},
    {label: '已售票数', value: '18,342'},
    {label: '宣发消耗', value: '¥432,000'},
    {label: '风险告警', value: 2}
  ]

  if(role === 'B'){
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">工作台首页</h2>
          <button className="ai-btn"><span className="spark">✨</span> 新建项目</button>
        </div>

        <div className="grid grid-cols-4 gap-4">
          {kpis.map(k=> (
            <div key={k.label} className="card">
              <div className="text-sm text-gray-300">{k.label}</div>
              <div className="text-2xl font-bold mt-2" style={{color: 'var(--color-accent)'}}>{k.value}</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="card">🧠 艺人智策</div>
          <div className="card">📣 AI宣发</div>
          <div className="card">🎟 智慧票务</div>
        </div>

        <div className="card alert-danger">高风险告警：艺人舆情异常，建议立即查看并处理。</div>

      </div>
    )
  }

  if(role === 'Brand'){
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold">品牌工作台</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="card">受众画像（示例）</div>
          <div className="card">ROI 报表（示例）</div>
        </div>
        <div className="card">✨ AI 生成定制品宣方案</div>
      </div>
    )
  }

  if(role === 'G'){
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold">城市文旅看板</h2>
        <div className="grid grid-cols-3 gap-4">
          <div className="card">跨城观演人数</div>
          <div className="card">预估餐饮住宿消费拉动</div>
          <div className="card">热力地图（占位）</div>
        </div>
      </div>
    )
  }

  // 默认 C 端观众首页
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex-1 pr-4">
          <input className="w-full border rounded-lg px-4 py-3" placeholder="搜索演出 / 艺人" />
        </div>
        <div className="ml-4">
          <button className="ai-btn"><span className="spark">✨</span> 为你推荐</button>
        </div>
      </div>

      <div className="mb-6">
        <div className="card p-4">AI 个性化推荐轮播（占位）</div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {loading && <div className="text-gray-400">加载中…</div>}
        {shows.length===0 && !loading && <div className="col-span-3 text-gray-400">暂无演出，后端启动并有 demo 数据时显示</div>}
        {shows.map(s=> <ShowCard key={s.id} show={s} />)}
      </div>
    </div>
  )
}
