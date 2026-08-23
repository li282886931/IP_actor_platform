import { Link } from 'react-router-dom'

export default function BottomNav({role='C'}){
  if(role !== 'C') return null

  const items = [
    {to: '/', label: '🏠 首页'},
    {to: '/generate', label: '✨ 为你推荐'},
    {to: '/mytickets', label: '🎫 我的票夹'},
    {to: '/community', label: '💬 社群'}
  ]

  return (
    <nav className="bottom-nav" aria-label="底部导航">
      {items.map(i=> (
        <Link key={i.to} to={i.to} className="bottom-nav-item">{i.label}</Link>
      ))}
    </nav>
  )
}
