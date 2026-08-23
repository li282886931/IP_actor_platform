import { NavLink } from 'react-router-dom'

export default function Sidebar({role}){
  // Hide vertical sidebar for C (观众) role — keep only top horizontal nav for C
  if(role === 'C') return null

  const items = {
    C: [
      {to:'/', label:'🏠 首页'},
      {to:'/generate', label:'✨ 为你推荐'},
      {to:'/mytickets', label:'🎫 我的票夹'},
      {to:'/community', label:'💬 社群'}
    ],
    B: [
      {to:'/', label:'🏠 工作台首页'},
      {to:'/artist', label:'🧾 艺人智策'},
      {to:'/generate', label:'📣 AI宣发'},
      {to:'/tickets', label:'🎟 智慧票务'}
    ],
    Brand: [
      {to:'/', label:'🏠 品牌首页'},
      {to:'/audience', label:'👥 受众画像'},
      {to:'/campaigns', label:'📈 品宣方案'}
    ],
    G: [
      {to:'/', label:'🏛️ 城市看板'},
      {to:'/reports', label:'📊 消费拉动'},
      {to:'/heatmap', label:'🗺 热力图'}
    ]
  }

  const list = items[role] || items.C

  return (
    <aside className="sidebar">
      <ul className="space-y-2">
        {list.map(i=> (
          <li key={i.to}>
            <NavLink to={i.to} className={({isActive}) => 'sidebar-link' + (isActive? ' active': '')}>{i.label}</NavLink>
          </li>
        ))}
      </ul>
    </aside>
  )
}
