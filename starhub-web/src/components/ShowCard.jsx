import { Link } from 'react-router-dom'

export default function ShowCard({show}){
  return (
    <Link to={`/show/${show.id}`} className="block bg-white rounded-lg shadow overflow-hidden text-black">
      <div className="h-44 bg-gray-200 flex items-center justify-center">海报</div>
      <div className="p-4">
        <div className="font-bold">{show.title}</div>
        <div className="text-sm text-gray-500">{show.city} · {show.venue}</div>
        <div className="mt-2 text-lg text-orange-600">¥{show.price} 起</div>
      </div>
    </Link>
  )
}
