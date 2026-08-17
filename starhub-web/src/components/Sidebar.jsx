import { Link } from 'react-router-dom'

export default function Sidebar(){
  return (
    <div className="bg-white rounded-xl shadow p-6 text-black">
      <ul className="space-y-3">
        <li><Link to="/" className="block">🏠 首页</Link></li>
        <li><Link to="/artist" className="block">🔍 艺人</Link></li>
        <li><Link to="/generate" className="block">✨ AI宣发</Link></li>
        <li className="text-sm text-gray-500">📊 数据</li>
      </ul>
    </div>
  )
}
