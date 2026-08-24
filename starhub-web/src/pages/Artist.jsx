import { useState } from 'react'
import { searchArtist } from '../api'

export default function Artist({role='B'}) {
  const [query, setQuery] = useState('')
  const [artist, setArtist] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleSearch = async () => {
    if(!query) return
    setLoading(true)
    try{
      const res = await searchArtist(query)
      setArtist(res.data.data && res.data.data[0] ? res.data.data[0] : null)
    }catch(e){
      console.error(e)
      setArtist(null)
    }
    setLoading(false)
  }

  return (
    <div>
      <div className="card card-white" style={{padding:16}}>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
          <h2 style={{margin:0,fontSize:18,fontWeight:700}}>🔍 艺人热度查询</h2>
          <div style={{fontSize:13,color:'var(--text-gray)'}}>在此可进行项目立项与快速导出艺人报告</div>
        </div>

        <div style={{display:'flex',gap:12,marginTop:12}}>
          <input
            className=""
            placeholder="输入艺人名字，如：周杰伦"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            style={{flex:1,padding:'10px 12px',borderRadius:8,border:'1px solid var(--border-glass)',background:'transparent',color:'var(--text-white)'}}
          />
          <button className="ai-btn" onClick={handleSearch}>{loading ? '查询中...' : (<><span className="spark">✨</span> 查询热度</>)}</button>
        </div>
      </div>

      {artist ? (
        <div className="card" style={{marginTop:12}}>
          <div className="artist-card">
            <div className="avatar">{artist.name && artist.name[0]}</div>
            <div>
              <div style={{fontSize:20,fontWeight:700}}>{artist.name}</div>
              <div style={{color:'var(--text-gray)'}}>{artist.tags}</div>
            </div>
            <div style={{marginLeft:'auto',textAlign:'right'}}>
              <div style={{fontSize:12,color:'var(--text-gray)'}}>评分</div>
              <div style={{fontSize:18,fontWeight:700,color:'var(--primary-light)'}}>{artist.heat_score}</div>
            </div>
          </div>

          <div className="metrics-grid">
            <div className="metric">
              <div style={{fontSize:18,fontWeight:700,color:'var(--primary-light)'}}>{artist.heat_score}</div>
              <div style={{color:'var(--text-gray)'}}>综合热度</div>
            </div>
            <div className="metric">
              <div style={{fontSize:18,fontWeight:700,color:'#34D399'}}>{artist.fan_count}</div>
              <div style={{color:'var(--text-gray)'}}>全网粉丝</div>
            </div>
            <div className="metric">
              <div style={{fontSize:18,fontWeight:700,color:'#F59E0B'}}>{artist.risk_level}</div>
              <div style={{color:'var(--text-gray)'}}>风险等级</div>
            </div>
          </div>

          <div style={{marginTop:12,background:'rgba(124,58,237,0.06)',padding:12,borderRadius:8}}>
            <div style={{fontWeight:700}}>🤖 AI 演出建议</div>
            <p style={{marginTop:8,color:'var(--text-light)'}}>该艺人当前热度极高，建议在一线城市举办大型场馆演出，预估单场票房可观。最佳档期：暑期/国庆。</p>
          </div>
        </div>
      ) : (
        <div className="card" style={{marginTop:12,textAlign:'center',padding:32,color:'var(--text-gray)'}}>在上方输入艺人名字并点击“查询热度”以查看结果</div>
      )}
    </div>
  )
}
