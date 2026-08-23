import { Link } from 'react-router-dom'

export default function Sidebar({role}){
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
    <div className="bg-white rounded-xl shadow p-6 text-black">
      <ul className="space-y-3">
        {list.map(i=> (
          <li key={i.to}><Link to={i.to} className="block">{i.label}</Link></li>
        ))}
      </ul>
    </div>
  )
}
