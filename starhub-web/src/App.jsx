import { Routes, Route } from 'react-router-dom'
import { useEffect, useState } from 'react'
import Home from './pages/Home'
import Artist from './pages/Artist'
import Generate from './pages/Generate'
import ShowDetail from './pages/ShowDetail'
import './design.css'

const roleMeta = {
  C: { label: '观众端', title: 'C 端用户', desc: '发现演出、看推荐、购票互动' },
  B: { label: '主办方', title: 'B 端管理', desc: '运营看板、艺人智策、活动管理' },
  Brand: { label: '品牌方', title: '品牌合作', desc: '受众画像、投放方案、ROI 分析' },
  G: { label: '政府/文旅', title: '政务端', desc: '城市文旅、消费拉动、舆情监测' }
}

export default function App() {
  const [role, setRole] = useState(() => localStorage.getItem('starhub-role') || 'C')
  const [isLoggedIn, setIsLoggedIn] = useState(() => localStorage.getItem('starhub-login') === 'true')
  const [account, setAccount] = useState('')

  useEffect(() => {
    localStorage.setItem('starhub-role', role)
  }, [role])

  useEffect(() => {
    localStorage.setItem('starhub-login', String(isLoggedIn))
  }, [isLoggedIn])

  const handleLogin = (e) => {
    e.preventDefault()
    setIsLoggedIn(true)
  }

  if (!isLoggedIn) {
    return (
      <div className="app-root" style={{minHeight:'100vh',display:'flex',alignItems:'center',justifyContent:'center',padding:24}}>
        <div style={{width:'100%',maxWidth:960,display:'grid',gridTemplateColumns:'1.1fr 0.9fr',gap:24,background:'rgba(255,255,255,0.03)',border:'1px solid rgba(255,255,255,0.08)',borderRadius:20,padding:24,boxShadow:'0 20px 60px rgba(0,0,0,0.35)'}}>
          <div>
            <div style={{display:'flex',alignItems:'center',gap:12,marginBottom:20}}>
              <div className="brand-icon" style={{width:42,height:42,borderRadius:12,display:'flex',alignItems:'center',justifyContent:'center',background:'linear-gradient(135deg, var(--primary), #3B82F6)',fontSize:20,fontWeight:700}}>✦</div>
              <h1 style={{margin:0,fontSize:30,letterSpacing:'-0.5px',background:'linear-gradient(135deg, #fff 60%, var(--primary-light))',WebkitBackgroundClip:'text',WebkitTextFillColor:'transparent'}}>锐音场 <span style={{fontSize:14,color:'var(--text-gray)',WebkitTextFillColor:'var(--text-gray)',marginLeft:6}}>StarHub</span></h1>
            </div>

            <h2 style={{margin:'0 0 8px',fontSize:36,lineHeight:1.2}}>根据登录身份切换不同页面</h2>
            <p style={{margin:'0 0 22px',color:'var(--text-gray)',fontSize:16,lineHeight:1.7}}>用户登录后，平台会自动切换到对应角色的工作台与展示页面。适配 C 端、B 端、品牌方和政府/文旅场景。</p>

            <div style={{display:'grid',gridTemplateColumns:'repeat(2, minmax(0, 1fr))',gap:12}}>
              {Object.entries(roleMeta).map(([value, item]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setRole(value)}
                  style={{
                    textAlign:'left',
                    padding:16,
                    borderRadius:14,
                    border: role === value ? '1px solid rgba(167,139,250,0.85)' : '1px solid rgba(255,255,255,0.08)',
                    background: role === value ? 'rgba(124,58,237,0.18)' : 'rgba(255,255,255,0.03)',
                    color:'var(--text-white)',
                    cursor:'pointer',
                    boxShadow: role === value ? '0 14px 32px rgba(124,58,237,0.25)' : 'none'
                  }}
                >
                  <div style={{fontSize:12,color:'var(--text-gray)',marginBottom:6}}>{item.label}</div>
                  <div style={{fontSize:18,fontWeight:700,marginBottom:4}}>{item.title}</div>
                  <div style={{fontSize:12,color:'var(--text-gray)'}}>{item.desc}</div>
                </button>
              ))}
            </div>
          </div>

          <div style={{background:'rgba(15,10,26,0.7)',border:'1px solid rgba(255,255,255,0.08)',borderRadius:18,padding:20}}>
            <div style={{fontSize:12,color:'var(--text-gray)',textTransform:'uppercase',letterSpacing:'0.12em',marginBottom:16}}>登录</div>
            <form onSubmit={handleLogin} style={{display:'grid',gap:14}}>
              <div>
                <label htmlFor="login-role" style={{display:'block',fontSize:12,color:'var(--text-gray)',marginBottom:8}}>登录角色</label>
                <select
                  id="login-role"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  style={{
                    width:'100%',
                    padding:'12px 14px',
                    borderRadius:10,
                    border:'1px solid rgba(255,255,255,0.08)',
                    background:'rgba(15,10,26,0.9)',
                    color:'#fff',
                    fontWeight:600,
                    outline:'none',
                    cursor:'pointer'
                  }}
                >
                  <option value="C">观众 C</option>
                  <option value="B">主办方 B</option>
                  <option value="Brand">品牌 Brand</option>
                  <option value="G">政府 G</option>
                </select>
              </div>

              <div>
                <label htmlFor="account" style={{display:'block',fontSize:12,color:'var(--text-gray)',marginBottom:8}}>账号</label>
                <input id="account" value={account} onChange={(e) => setAccount(e.target.value)} placeholder="输入邮箱或手机号" style={{width:'100%',padding:'12px 14px',borderRadius:10,border:'1px solid rgba(255,255,255,0.08)',background:'rgba(255,255,255,0.03)',color:'#fff',outline:'none'}} />
              </div>

              <div>
                <label htmlFor="password" style={{display:'block',fontSize:12,color:'var(--text-gray)',marginBottom:8}}>密码</label>
                <input id="password" type="password" placeholder="••••••••" style={{width:'100%',padding:'12px 14px',borderRadius:10,border:'1px solid rgba(255,255,255,0.08)',background:'rgba(255,255,255,0.03)',color:'#fff',outline:'none'}} />
              </div>

              <button type="submit" style={{marginTop:8,padding:'14px 18px',border:'none',borderRadius:12,background:'linear-gradient(135deg, var(--primary), var(--primary-dark))',color:'#fff',fontWeight:700,fontSize:15,cursor:'pointer'}}>登录 {roleMeta[role].label}</button>
            </form>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="app-root">
      <header className="header">
        <div className="brand">
          <div className="brand-icon">✦</div>
          <h1>锐音场 <span>StarHub</span></h1>
        </div>

        <div style={{display:'flex',alignItems:'center',gap:12}}>
          <div className="header-tag"><i className="fas fa-sparkles" style={{color:'var(--gold)'}}></i> AI 驱动 · 全链路文娱平台 <span style={{opacity:0.3,margin:'0 6px'}}>|</span> MVP v1.0</div>
          <select value={role} onChange={(e) => setRole(e.target.value)} className="role-select">
            <option value="C">观众 C</option>
            <option value="B">主办方 B</option>
            <option value="Brand">品牌 Brand</option>
            <option value="G">政府 G</option>
          </select>
          <button type="button" onClick={() => setIsLoggedIn(false)} style={{padding:'8px 12px',borderRadius:10,border:'1px solid rgba(255,255,255,0.08)',background:'rgba(255,255,255,0.03)',color:'#fff',cursor:'pointer'}}>切换账号</button>
        </div>
      </header>

      <div className="showcase">
        <div className="device-container">
          <div className="device-header">
            <div className="label"><i className="fas fa-mobile-screen-button"></i> 小程序端 · {roleMeta[role].label}</div>
            <span className="badge"><i className="far fa-circle"></i> 微信生态</span>
          </div>

          <div className="device-frame phone-frame">
            <div className="phone-notch"><span className="speaker"></span><span className="cam"></span></div>
            <div className="phone-screen">
              <div className="phone-home">
                <div style={{display:'flex',justifyContent:'space-between',marginBottom:10}}>
                  <div className="muted">9:41</div>
                  <div className="muted">信号 · WiFi</div>
                </div>
                <div className="search-bar">
                  <i className="fas fa-search muted"></i>
                  <input placeholder="搜索演出、艺人或场地" />
                </div>
                <div className="banner">
                  <div className="text"><h3 style={{margin:0}}>发现精彩演出</h3><p style={{margin:0,color:'var(--text-gray)'}}>AI 推荐 · 智能匹配你的口味</p></div>
                  <div className="tag">New</div>
                </div>
                <div className="quick-grid">
                  <div className="quick-item"><div className="icon purple">🎤</div><div style={{fontSize:11}}>热门</div></div>
                  <div className="quick-item"><div className="icon gold">🕺</div><div style={{fontSize:11}}>演出</div></div>
                  <div className="quick-item"><div className="icon blue">🎟️</div><div style={{fontSize:11}}>购票</div></div>
                  <div className="quick-item"><div className="icon green">⭐</div><div style={{fontSize:11}}>榜单</div></div>
                </div>

                <div className="section">
                  <div className="section-title" style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
                    <div>为你推荐</div>
                    <a href="#" style={{fontSize:12,color:'var(--primary-light)'}}>更多</a>
                  </div>

                  <div className="show-card">
                    <div className="poster">海报</div>
                    <div className="info">
                      <h4 style={{margin:0}}>热力演出 · 洛杉矶之夜</h4>
                      <div className="meta muted">2026-09-01 · 20:00 · 场地 A</div>
                      <div className="price" style={{color:'var(--gold)',marginTop:6}}>￥199 起</div>
                    </div>
                  </div>

                  <div className="show-card">
                    <div className="poster">海报</div>
                    <div className="info">
                      <h4 style={{margin:0}}>AI 音乐节 · 夏日限定</h4>
                      <div className="meta muted">2026-09-10 · 19:30 · 场地 B</div>
                      <div className="price" style={{color:'var(--gold)',marginTop:6}}>￥299 起</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div>
          <div className="device-container desktop-frame">
            <div className="device-header" style={{padding:'12px 8px'}}>
              <div className="label"><i className="fas fa-desktop"></i> 后台管理 · {roleMeta[role].label}</div>
              <span className="badge">运营看板</span>
            </div>
            <div className="desktop-screen">
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12}}>
                <h2 style={{margin:0}}>{roleMeta[role].title}</h2>
                <div className="date muted">2026-08-24</div>
              </div>
              <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:12}}>
                <div style={{background:'rgba(255,255,255,0.03)',padding:12,borderRadius:8,border:'1px solid var(--border-glass)'}}>
                  <div style={{fontSize:24,fontWeight:700,background:'linear-gradient(135deg,#fff,var(--primary-light))',WebkitBackgroundClip:'text',WebkitTextFillColor:'transparent'}}>12.3k</div>
                  <div className="lbl muted">日活跃用户</div>
                </div>
                <div style={{background:'rgba(255,255,255,0.03)',padding:12,borderRadius:8,border:'1px solid var(--border-glass)'}}>
                  <div style={{fontSize:24,fontWeight:700,color:'var(--primary-light)'}}>¥1.2M</div>
                  <div className="lbl muted">当日票房</div>
                </div>
                <div style={{background:'rgba(255,255,255,0.03)',padding:12,borderRadius:8,border:'1px solid var(--border-glass)'}}>
                  <div style={{fontSize:24,fontWeight:700,color:'var(--gold)'}}>+8%</div>
                  <div className="lbl muted">环比增长</div>
                </div>
                <div style={{background:'rgba(255,255,255,0.03)',padding:12,borderRadius:8,border:'1px solid var(--border-glass)'}}>
                  <div style={{fontSize:24,fontWeight:700,color:'var(--text-white)'}}>45</div>
                  <div className="lbl muted">进行中项目</div>
                </div>
              </div>

              <div style={{marginTop:18}}>
                <Routes>
                  <Route path="/" element={<Home role={role} />} />
                  <Route path="/artist" element={<Artist role={role} />} />
                  <Route path="/generate" element={<Generate role={role} />} />
                  <Route path="/show/:id" element={<ShowDetail role={role} />} />
                </Routes>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
