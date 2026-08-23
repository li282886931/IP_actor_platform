import { NavLink } from 'react-router-dom'

export default function BottomNav({role='C'}){
  // Render horizontal nav for all roles (C / B / Brand / G)
  const items = [
    {to: '/', label: '🏠 首页'},
    {to: '/generate', label: '✨ 为你推荐'},
    {to: '/mytickets', label: '🎫 我的票夹'},
    {to: '/community', label: '💬 社群'},
    {to: '/artist', label: '🧾 艺人查询'},
    {to: '/generate', label: '📣 AI宣发'}
  ]

  return (
    <nav className="bottom-nav" aria-label="顶部横向导航">
      {items.map(i=> (
        <NavLink key={i.to + i.label} to={i.to} className={({isActive}) => 'bottom-nav-item' + (isActive? ' active': '')}>
          {i.label}
        </NavLink>
      ))}
    </nav>
  )
}
