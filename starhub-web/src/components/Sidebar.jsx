import { NavLink } from 'react-router-dom'

import { BrandMark, NavIcon } from './icons'

const navigationByRole = {
  C: [
    { to: '/', label: '演出发现' },
    { to: '/artist', label: '艺人查询' },
  ],
  B: [
    { to: '/', label: '工作台' },
    { to: '/artist', label: '艺人智策' },
    { to: '/generate', label: 'AI 宣发' },
  ],
  Brand: [
    { to: '/', label: '品牌概览' },
    { to: '/artist', label: '受众洞察' },
    { to: '/generate', label: 'AI 品宣' },
  ],
  G: [
    { to: '/', label: '城市概览' },
    { to: '/artist', label: '艺人洞察' },
    { to: '/generate', label: 'AI 宣发' },
  ],
}

const mobileLabels = {
  '/': '首页',
  '/artist': '智策',
  '/generate': '宣发',
  '/users': '我的',
}

export default function Sidebar({ role, canManageUsers = false }) {
  const baseItems = navigationByRole[role] || navigationByRole.C
  const items = canManageUsers
    ? [...baseItems, { to: '/users', label: '用户管理' }]
    : baseItems
  const renderLink = (item) => (
    <NavLink
      key={item.to}
      className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
      end={item.to === '/'}
      to={item.to}
    >
      <span className="sidebar-link-icon" aria-hidden="true"><NavIcon to={item.to} size={20} /></span>
      <span>{item.label}</span>
    </NavLink>
  )

  return (
    <>
      <aside className="app-sidebar">
        <div className="sidebar-brand">
          <BrandMark />
          <span>
            <strong>锐音场</strong>
            <small>StarHub Studio</small>
          </span>
        </div>

        <div className="sidebar-section-label">工作空间</div>
        <nav className="sidebar-nav" aria-label="主导航">
          {items.map(renderLink)}
        </nav>

        <div className="sidebar-status">
          <span className="status-dot" aria-hidden="true" />
          <span>
            <strong>系统运行正常</strong>
            <small>API 与数据服务在线</small>
          </span>
        </div>
      </aside>

      <nav className="mobile-tabbar" aria-label="移动端主导航">
        {items.map((item) => (
          <NavLink
            key={item.to}
            className={({ isActive }) => `mobile-tab${isActive ? ' active' : ''}`}
            end={item.to === '/'}
            to={item.to}
          >
            <span className="mobile-tab-icon" aria-hidden="true"><NavIcon to={item.to} size={20} /></span>
            <span>{mobileLabels[item.to] || item.label}</span>
          </NavLink>
        ))}
      </nav>
    </>
  )
}

