import { NavLink } from 'react-router-dom'

const navigationByRole = {
  C: [
    { to: '/', label: '演出发现', mark: '01' },
    { to: '/artist', label: '艺人查询', mark: '02' },
  ],
  B: [
    { to: '/', label: '工作台', mark: '01' },
    { to: '/artist', label: '艺人智策', mark: '02' },
    { to: '/generate', label: 'AI 宣发', mark: '03' },
  ],
  Brand: [
    { to: '/', label: '品牌概览', mark: '01' },
    { to: '/artist', label: '受众洞察', mark: '02' },
    { to: '/generate', label: 'AI 品宣', mark: '03' },
  ],
  G: [
    { to: '/', label: '城市概览', mark: '01' },
    { to: '/artist', label: '艺人洞察', mark: '02' },
    { to: '/generate', label: 'AI 宣发', mark: '03' },
  ],
}

export default function Sidebar({ role, canManageUsers = false }) {
  const baseItems = navigationByRole[role] || navigationByRole.C
  const items = canManageUsers
    ? [...baseItems, { to: '/users', label: '用户管理', mark: '04' }]
    : baseItems

  return (
    <aside className="app-sidebar">
      <div className="sidebar-brand">
        <span className="brand-mark" aria-hidden="true">✦</span>
        <span>
          <strong>锐音场</strong>
          <small>StarHub</small>
        </span>
      </div>

      <div className="sidebar-section-label">工作空间</div>
      <nav className="sidebar-nav" aria-label="主导航">
        {items.map((item) => (
          <NavLink
            key={item.to}
            className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
            end={item.to === '/'}
            to={item.to}
          >
            <span className="sidebar-link-mark" aria-hidden="true">{item.mark}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-status">
        <span className="status-dot" aria-hidden="true" />
        <span>
          <strong>系统运行正常</strong>
          <small>API 与数据服务在线</small>
        </span>
      </div>
    </aside>
  )
}
