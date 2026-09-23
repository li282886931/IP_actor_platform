import { useEffect, useState } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'

import Sidebar from './components/Sidebar'
import { webLogin } from './api'
import Artist from './pages/Artist'
import Generate from './pages/Generate'
import Home from './pages/Home'
import ShowDetail from './pages/ShowDetail'
import UserManagement from './pages/UserManagement'

const roleMeta = {
  C: { label: '观众端', title: '演出发现', desc: '浏览演出、查看推荐并管理预约' },
  B: { label: '主办方', title: '运营工作台', desc: '掌握项目经营、艺人热度与宣发进展' },
  Brand: { label: '品牌方', title: '品牌合作', desc: '分析受众价值、合作表现与投放机会' },
  G: { label: '政府 / 文旅', title: '城市文旅', desc: '洞察演出经济、消费拉动与城市热度' },
}

const routeTitles = {
  '/artist': '艺人洞察',
  '/generate': 'AI 宣发',
  '/users': '用户管理',
}

function roleFromUser(user) {
  if (!user) return null
  if (user.can_manage_users || user.group_code === 'root' || user.account === 'root') return 'B'
  return roleMeta[user.role] ? user.role : null
}

function normalizeRole(value) {
  return roleMeta[value] ? value : 'C'
}

function clearReadableCookies() {
  document.cookie.split(';').forEach((cookie) => {
    const name = cookie.split('=')[0]?.trim()
    if (!name) return
    document.cookie = `${name}=; Max-Age=0; path=/`
  })
}

function LoginView({ account, onAccountChange, password, onPasswordChange, onLogin, loginStatus, loginError }) {
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
            <article
              className="role-preview"
              key={value}
            >
              <span>{item.label}</span>
              <strong>{item.title}</strong>
              <small>{item.desc}</small>
            </article>
          ))}
        </div>
      </section>

      <section className="login-panel">
        <div className="login-panel-heading">
          <span className="eyebrow">WELCOME BACK</span>
          <h2>登录工作台</h2>
          <p>使用账号密码登录，系统会根据用户组进入对应工作台。</p>
        </div>
        <form onSubmit={onLogin} className="login-form">
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
            <input
              type="password"
              value={password}
              onChange={(event) => onPasswordChange(event.target.value)}
              placeholder="输入登录密码"
            />
          </label>
          <button className="button button-primary button-block" type="submit">
            {loginStatus === 'loading' ? '登录中...' : '登录'}
          </button>
        </form>
        {loginError && <div className="inline-message error">{loginError}</div>}
      </section>
    </main>
  )
}

export default function App() {
  const location = useLocation()
  const [role, setRole] = useState(() => normalizeRole(localStorage.getItem('starhub-role') || 'C'))
  const [isLoggedIn, setIsLoggedIn] = useState(() => localStorage.getItem('starhub-login') === 'true')
  const [currentUser, setCurrentUser] = useState(() => {
    const stored = localStorage.getItem('starhub-user')
    return stored ? JSON.parse(stored) : null
  })
  const [account, setAccount] = useState('')
  const [password, setPassword] = useState('')
  const [loginStatus, setLoginStatus] = useState('idle')
  const [loginError, setLoginError] = useState('')
  const activeRole = roleFromUser(currentUser) || normalizeRole(role)
  const canManageUsers = currentUser?.can_manage_users || currentUser?.group_code === 'root' || currentUser?.account === 'root'

  useEffect(() => {
    if (activeRole !== role) {
      setRole(activeRole)
    }
  }, [activeRole, role])

  useEffect(() => {
    localStorage.setItem('starhub-role', role)
  }, [role])

  useEffect(() => {
    localStorage.setItem('starhub-login', String(isLoggedIn))
  }, [isLoggedIn])

  const handleLogin = async (event) => {
    event.preventDefault()
    const loginAccount = account.trim()
    setLoginStatus('loading')
    setLoginError('')
    try {
      const response = await webLogin({ account: loginAccount, password })
      const data = response.data?.data || {}
      if (data.token) {
        localStorage.setItem('starhub-token', data.token)
      }
      if (data.user) {
        localStorage.setItem('starhub-user', JSON.stringify(data.user))
        setCurrentUser(data.user)
        setRole(roleFromUser(data.user) || 'C')
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
        password={password}
        onPasswordChange={setPassword}
        onLogin={handleLogin}
        loginStatus={loginStatus}
        loginError={loginError}
      />
    )
  }

  const currentTitle = location.pathname.startsWith('/show/')
    ? '演出详情'
    : routeTitles[location.pathname] || roleMeta[activeRole].title

  return (
    <div className="app-shell">
      <Sidebar role={activeRole} canManageUsers={canManageUsers} />

      <div className="app-workspace">
        <header className="topbar">
          <div className="topbar-heading">
            <span className="eyebrow">{roleMeta[activeRole].label}</span>
            <h1>{currentTitle}</h1>
            <p>{roleMeta[activeRole].desc}</p>
          </div>

          <div className="topbar-actions">
            <span className="platform-badge">AI 驱动 · 运营平台</span>
            {currentUser && <span className="platform-badge">{currentUser.name || currentUser.account}</span>}
            <button
              className="button button-secondary"
              type="button"
              onClick={() => {
                localStorage.removeItem('starhub-token')
                localStorage.removeItem('starhub-user')
                localStorage.removeItem('starhub-tenant')
                clearReadableCookies()
                setCurrentUser(null)
                setIsLoggedIn(false)
              }}
            >
              退出
            </button>
          </div>
        </header>

        <main className="workspace-content">
          <Routes>
            <Route path="/" element={<Home role={activeRole} currentUser={currentUser} />} />
            <Route path="/artist" element={<Artist role={activeRole} />} />
            <Route path="/generate" element={<Generate role={activeRole} />} />
            <Route path="/users" element={<UserManagement currentUser={currentUser} />} />
            <Route path="/show/:id" element={<ShowDetail role={activeRole} />} />
            <Route path="*" element={<Navigate replace to="/" />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
