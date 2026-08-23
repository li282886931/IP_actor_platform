import { Link } from 'react-router-dom'

export default function ShowCard({show}){
  return (
    <Link to={`/show/${show.id}`} className="show-card">
      <div className="show-poster">{show.poster || '演出海报'}</div>
      <div className="p-4 bg-transparent">
        <div className="flex items-start justify-between">
          <div>
            <div className="font-bold text-lg">{show.title}</div>
            <div className="text-sm text-gray-300">{show.city} · {show.venue}</div>
          </div>
          <div className="ml-4">
            <div className="price-badge">¥{show.price}</div>
          </div>
        </div>
        <div className="mt-3 text-sm text-gray-400">{show.short_desc || 'AI 推荐 · 热度稳定'}</div>
      </div>
    </Link>
  )
}
