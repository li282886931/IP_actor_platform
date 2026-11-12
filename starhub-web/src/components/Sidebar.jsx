import { NavLink } from 'react-router-dom'

import { BrandMark, NavIcon } from './icons'
import { navigationByRole } from '../roleConfig'

export default function Sidebar({ role, canManageUsers = false }) {
  const items = navigationByRole[canManageUsers ? 'Admin' : role] || navigationByRole.C
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
            <span>{item.short || item.label}</span>
          </NavLink>
        ))}
      </nav>
    </>
  )
}
