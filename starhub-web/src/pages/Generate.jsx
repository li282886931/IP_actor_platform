import { useState } from 'react'
import { generateAI } from '../api'

export default function Generate({role='B'}){
  const [form, setForm] = useState({ type: 'poster', show_name: '', artist: '', city: '' })
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)

  const handleGenerate = async () =>{
    setLoading(true)
    try{
      const res = await generateAI(form)
      setResult(res.data.result || JSON.stringify(res.data))
    }catch(e){
      console.error(e)
      setResult('生成失败，请检查后端或日志')
    }
    setLoading(false)
  }

  return (
    <div>
      <div className="card card-white" style={{padding:16}}>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
          <h2 style={{margin:0,fontSize:18,fontWeight:700}}>✨ AI 宣发内容生成</h2>
          <div style={{fontSize:13,color:'var(--text-gray)'}}>为演出生成海报、短视频脚本等宣发素材</div>
        </div>

        <div style={{display:'grid',gridTemplateColumns:'1fr 2fr',gap:12,marginTop:12}}>
          <select value={form.type} onChange={(e)=>setForm({...form,type:e.target.value})} style={{padding:10,borderRadius:8,border:'1px solid var(--border-glass)',background:'transparent',color:'var(--text-white)'}}>
            <option value="poster">海报文案</option>
            <option value="video_script">短视频脚本</option>
          </select>

          <input placeholder="演出名称" value={form.show_name} onChange={(e)=>setForm({...form,show_name:e.target.value})} style={{padding:10,borderRadius:8,border:'1px solid var(--border-glass)',background:'transparent',color:'var(--text-white)'}} />

          <input placeholder="艺人" value={form.artist} onChange={(e)=>setForm({...form,artist:e.target.value})} style={{padding:10,borderRadius:8,border:'1px solid var(--border-glass)',background:'transparent',color:'var(--text-white)'}} />
          <input placeholder="城市" value={form.city} onChange={(e)=>setForm({...form,city:e.target.value})} style={{padding:10,borderRadius:8,border:'1px solid var(--border-glass)',background:'transparent',color:'var(--text-white)'}} />

          <div style={{display:'flex',gap:8,alignItems:'center'}}>
            <button className="ai-btn" onClick={handleGenerate}>
              <span className="spark">✨</span>
              {loading ? (<span style={{display:'inline-flex',alignItems:'center',gap:8}}><span className="loader"></span> AI 生成中...</span>) : '一键生成'}
            </button>
            <button style={{padding:'8px 12px',borderRadius:8,border:'1px solid var(--border-glass)',background:'transparent',color:'var(--text-white)'}}>预览</button>
          </div>
        </div>
      </div>

      <div className="card" style={{padding:16,marginTop:12}}>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12}}>
          <h3 style={{margin:0,fontWeight:700}}>生成结果</h3>
          {result && (
            <button onClick={() => navigator.clipboard.writeText(result)} style={{fontSize:13,color:'var(--primary-light)',background:'transparent',border:'none',cursor:'pointer'}}>📋 复制文案</button>
          )}
        </div>

        {result ? (
          <div style={{background:'rgba(255,255,255,0.03)',padding:12,borderRadius:8,whiteSpace:'pre-wrap'}}>{result}</div>
        ) : (
          <div style={{padding:32,textAlign:'center',color:'var(--text-gray)'}}>填写上方表单并点击“一键生成”来查看 AI 输出</div>
        )}
      </div>
    </div>
  )
}
