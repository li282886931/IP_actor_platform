import { useEffect, useState } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'

import Sidebar from './components/Sidebar'
import { webLogin } from './api'
import Artist from './pages/Artist'
import Generate from './pages/Generate'
import Home from './pages/Home'
import ShowDetail from './pages/ShowDetail'

const roleMeta = {
  C: { label: '观众端', title: '演出发现', desc: '浏览演出、查看推荐并管理预约' },
  B: { label: '主办方', title: '运营工作台', desc: '掌握项目经营、艺人热度与宣发进展' },
  Brand: { label: '品牌方', title: '品牌合作', desc: '分析受众价值、合作表现与投放机会' },
  G: { label: '政府 / 文旅', title: '城市文旅', desc: '洞察演出经济、消费拉动与城市热度' },
}

const routeTitles = {
  '/artist': '艺人洞察',
  '/generate': 'AI 宣发',
}

function LoginView({ account, onAccountChange, role, onRoleChange, onLogin, loginStatus, loginError }) {
  return (
    <main className="login-page">
      <section className="login-intro">
        <div className="login-brand">
          <span className="brand-mark" aria-hidden="true">✦</span>
          <span>
            <strong>锐音场</strong>
            <small>StarHub</small>
          </span>
        </div>
        <div className="login-copy">
          <span className="eyebrow">AI DRIVEN ENTERTAINMENT OPERATIONS</span>
          <h1>连接演出决策、内容宣发与经营增长</h1>
          <p>面向观众、主办方、品牌与文旅机构的一体化演出运营平台。</p>
        </div>
        <div className="role-preview-grid">
          {Object.entries(roleMeta).map(([value, item]) => (
            <button
              className={`role-preview${role === value ? ' selected' : ''}`}
              key={value}
              onClick={() => onRoleChange(value)}
              type="button"
            >
              <span>{item.label}</span>
              <strong>{item.title}</strong>
              <small>{item.desc}</small>
            </button>
          ))}
        </div>
      </section>

      <section className="login-panel">
        <div className="login-panel-heading">
          <span className="eyebrow">WELCOME BACK</span>
          <h2>登录工作台</h2>
          <p>选择身份并进入运营工作台。</p>
        </div>
        <form onSubmit={onLogin} className="login-form">
          <label>
            <span>登录角色</span>
            <select value={role} onChange={(event) => onRoleChange(event.target.value)}>
              <option value="C">观众 C</option>
              <option value="B">主办方 B</option>
              <option value="Brand">品牌 Brand</option>
              <option value="G">政府 G</option>
            </select>
          </label>
          <label>
            <span>账号</span>
            <input
              value={account}
              onChange={(event) => onAccountChange(event.target.value)}
              placeholder="输入邮箱或手机号"
            />
          </label>
          <label>
            <span>密码</span>
            <input type="password" placeholder="输入登录密码" />
          </label>
          <button className="button button-primary button-block" type="submit">
            {loginStatus === 'loading' ? '登录中...' : `登录 ${roleMeta[role].label}`}
          </button>
        </form>
        {loginError && <div className="inline-message error">{loginError}</div>}
      </section>
    </main>
  )
}

export default function App() {
  const location = useLocation()
  const [role, setRole] = useState(() => localStorage.getItem('starhub-role') || 'C')
  const [isLoggedIn, setIsLoggedIn] = useState(() => localStorage.getItem('starhub-login') === 'true')
  const [account, setAccount] = useState('')
  const [loginStatus, setLoginStatus] = useState('idle')
  const [loginError, setLoginError] = useState('')

  useEffect(() => {
    localStorage.setItem('starhub-role', role)
  }, [role])

  useEffect(() => {
    localStorage.setItem('starhub-login', String(isLoggedIn))
  }, [isLoggedIn])

  const handleLogin = async (event) => {
    event.preventDefault()
    const loginAccount = account.trim() || 'operator@ruiyinchang.com'
    setLoginStatus('loading')
    setLoginError('')
    try {
      const response = await webLogin({ account: loginAccount, name: loginAccount })
      const data = response.data?.data || {}
      if (data.token) {
        localStorage.setItem('starhub-token', data.token)
      }
      if (data.current_tenant) {
        localStorage.setItem('starhub-tenant', JSON.stringify(data.current_tenant))
      }
      setIsLoggedIn(true)
      setLoginStatus('success')
    } catch {
      setLoginStatus('error')
      setLoginError('登录失败，请确认后端服务可用。')
    }
  }

  if (!isLoggedIn) {
    return (
      <LoginView
        account={account}
        onAccountChange={setAccount}
        role={role}
        onRoleChange={setRole}
        onLogin={handleLogin}
        loginStatus={loginStatus}
        loginError={loginError}
      />
    )
  }

  const currentTitle = location.pathname.startsWith('/show/')
    ? '演出详情'
    : routeTitles[location.pathname] || roleMeta[role].title

  return (
    <div className="app-shell">
      <Sidebar role={role} />

      <div className="app-workspace">
        <header className="topbar">
          <div className="topbar-heading">
            <span className="eyebrow">{roleMeta[role].label}</span>
            <h1>{currentTitle}</h1>
            <p>{roleMeta[role].desc}</p>
          </div>

          <div className="topbar-actions">
            <span className="platform-badge">AI 驱动 · 运营平台</span>
            <label className="role-control">
              <span className="sr-only">当前角色</span>
              <select
                aria-label="当前角色"
                value={role}
                onChange={(event) => setRole(event.target.value)}
              >
                <option value="C">观众 C</option>
                <option value="B">主办方 B</option>
                <option value="Brand">品牌 Brand</option>
                <option value="G">政府 G</option>
              </select>
            </label>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => {
                localStorage.removeItem('starhub-token')
                setIsLoggedIn(false)
              }}
            >
              切换账号
            </button>
          </div>
        </header>

        <main className="workspace-content">
          <Routes>
            <Route path="/" element={<Home role={role} />} />
            <Route path="/artist" element={<Artist role={role} />} />
            <Route path="/generate" element={<Generate role={role} />} />
            <Route path="/show/:id" element={<ShowDetail role={role} />} />
            <Route path="*" element={<Navigate replace to="/" />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
