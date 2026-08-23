import { useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { getShow, mockOrder } from '../api'

export default function ShowDetail({role='C'}){
  const { id } = useParams()
  const [show, setShow] = useState(null)
  const [loading, setLoading] = useState(false)
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [msg, setMsg] = useState('')

  useEffect(()=>{ async function load(){ setLoading(true); try{ const res = await getShow(id); setShow(res.data.data) }catch(e){console.error(e)} setLoading(false)} load() },[id])

  const handleOrder = async ()=>{
    if(!name||!phone) return setMsg('请填写姓名与手机号')
    try{
      const res = await mockOrder(id,{name,phone})
      setMsg('预约成功！')
    }catch(e){ console.error(e); setMsg('预约失败') }
  }

  if(loading) return <div className="text-gray-400">加载中…</div>
  if(!show) return <div className="text-gray-400">未找到演出（请启动后端并有数据）</div>

  return (
    <div className="relative">
      <div className="flex gap-6">
        <div className="flex-1 card card-white">
          <div className="h-64 bg-gray-200 rounded mb-4 flex items-center justify-center">海报预览</div>
          <h2 className="text-2xl font-bold">{show.title}</h2>
          <p className="text-gray-600">{show.venue} · {show.city}</p>
          <div className="mt-4 text-lg">票价：{show.price} 起</div>

          <div className="mt-6">
            <h3 className="font-bold mb-2">艺人介绍</h3>
            <p className="text-gray-700">示例艺人介绍内容，支持 AI 自动生成看点摘要</p>
          </div>

          <div className="mt-6">
            <h3 className="font-bold mb-2">观众讨论</h3>
            <div className="text-gray-600">暂无评论（演示数据）</div>
          </div>
        </div>

        {role !== 'C' ? (
          <div className="w-80 card">B端/其他侧边栏示例：营销投放、数据报表入口</div>
        ) : (
          <div className="w-80 card card-white">
            <h3 className="font-bold mb-3">立即预约</h3>
            <input className="w-full border rounded px-3 py-2 mb-2" placeholder="姓名" value={name} onChange={e=>setName(e.target.value)} />
            <input className="w-full border rounded px-3 py-2 mb-2" placeholder="手机号" value={phone} onChange={e=>setPhone(e.target.value)} />
            <button className="w-full ai-btn" onClick={handleOrder}>立即预约</button>
            {msg && <div className="mt-3 text-sm text-green-600">{msg}</div>}
          </div>
        )}
      </div>

      {/* 移动/小屏下的固定购票栏（仅 C 端显示） */}
      {role === 'C' && (
        <div className="purchase-bar">
          <div>
            <div className="text-sm text-gray-500">{show.title}</div>
            <div className="text-xl font-bold">¥{show.price} 起</div>
          </div>
          <div>
            <button className="ai-btn" onClick={handleOrder}>立即购票</button>
          </div>
        </div>
      )}
    </div>
  )
}
