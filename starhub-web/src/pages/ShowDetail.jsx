import { useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { getShow, mockOrder } from '../api'

export default function ShowDetail(){
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
    <div className="flex gap-6">
      <div className="flex-1 bg-white rounded-xl shadow p-6 text-black">
        <div className="h-64 bg-gray-200 rounded mb-4 flex items-center justify-center">海报预览</div>
        <h2 className="text-2xl font-bold">{show.title}</h2>
        <p className="text-gray-600">{show.venue} · {show.city}</p>
        <div className="mt-4 text-lg">票价：{show.price} 起</div>
      </div>

      <div className="w-80 bg-white rounded-xl shadow p-6 text-black">
        <h3 className="font-bold mb-3">立即预约</h3>
        <input className="w-full border rounded px-3 py-2 mb-2" placeholder="姓名" value={name} onChange={e=>setName(e.target.value)} />
        <input className="w-full border rounded px-3 py-2 mb-2" placeholder="手机号" value={phone} onChange={e=>setPhone(e.target.value)} />
        <button className="w-full bg-blue-600 text-white rounded py-2" onClick={handleOrder}>预约</button>
        {msg && <div className="mt-3 text-sm text-green-600">{msg}</div>}
      </div>
    </div>
  )
}
