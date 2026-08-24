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

  if(loading) return <div style={{color:'var(--text-gray)'}}>加载中…</div>
  if(!show) return <div style={{color:'var(--text-gray)'}}>未找到演出（请启动后端并有数据）</div>

  return (
    <div>
      <div style={{display:'grid',gridTemplateColumns:'1fr 320px',gap:16}}>
        <div className="card" style={{padding:16}}>
          <div style={{height:220,borderRadius:8,overflow:'hidden',background:'linear-gradient(135deg,#2D1B69,#6D28D9)',display:'flex',alignItems:'center',justifyContent:'center',color:'rgba(255,255,255,0.2)',fontSize:32}}>海报预览</div>
          <h2 style={{marginTop:12,fontSize:20,fontWeight:700}}>{show.title}</h2>
          <div className="meta">{show.venue} · {show.city}</div>
          <div style={{marginTop:12,fontSize:18,fontWeight:700,color:'var(--gold)'}}>票价：{show.price} 起</div>

          <div style={{marginTop:16}}>
            <h3 style={{fontWeight:700}}>艺人介绍</h3>
            <p style={{color:'var(--text-gray)'}}>示例艺人介绍内容，支持 AI 自动生成看点摘要</p>
          </div>

          <div style={{marginTop:16}}>
            <h3 style={{fontWeight:700}}>观众讨论</h3>
            <div style={{color:'var(--text-gray)'}}>暂无评论（演示数据）</div>
          </div>
        </div>

        {role !== 'C' ? (
          <div className="card" style={{padding:16}}>B端/其他侧边栏示例：营销投放、数据报表入口</div>
        ) : (
          <div className="card" style={{padding:16}}>
            <h3 style={{fontWeight:700,marginBottom:8}}>立即预约</h3>
            <input placeholder="姓名" value={name} onChange={e=>setName(e.target.value)} style={{width:'100%',padding:10,borderRadius:8,border:'1px solid var(--border-glass)',marginBottom:8,background:'transparent',color:'var(--text-white)'}} />
            <input placeholder="手机号" value={phone} onChange={e=>setPhone(e.target.value)} style={{width:'100%',padding:10,borderRadius:8,border:'1px solid var(--border-glass)',marginBottom:8,background:'transparent',color:'var(--text-white)'}} />
            <button className="ai-btn" style={{width:'100%'}} onClick={handleOrder}>立即预约</button>
            {msg && <div style={{marginTop:12,color: msg.includes('成功') ? '#34D399' : '#FCA5A5' }}>{msg}</div>}
          </div>
        )}
      </div>

      {role === 'C' && (
        <div className="purchase-bar">
          <div>
            <div style={{fontSize:12,color:'var(--text-gray)'}}>{show.title}</div>
            <div style={{fontSize:18,fontWeight:700}}>¥{show.price} 起</div>
          </div>
          <div>
            <button className="ai-btn" onClick={handleOrder}>立即购票</button>
          </div>
        </div>
      )}
    </div>
  )
}
