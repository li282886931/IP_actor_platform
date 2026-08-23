import { Routes, Route, Link } from 'react-router-dom'
import { useState } from 'react'
import Home from './pages/Home'
import Artist from './pages/Artist'
import Generate from './pages/Generate'
import ShowDetail from './pages/ShowDetail'
import Sidebar from './components/Sidebar'
import BottomNav from './components/BottomNav'

export default function App(){
  const [role, setRole] = useState('C') // C: 观众, B: 主办方, Brand: 品牌, G: 政府

  return (
    <div className="min-h-screen pb-24">{/* pb for bottom nav space */}
      <div className="container">
        <header className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">🎵 锐音场 StarHub</h1>

          <div className="flex items-center gap-4">
            <select value={role} onChange={e=>setRole(e.target.value)} className="px-3 py-1 rounded border">
              <option value="C">观众 C</option>
              <option value="B">主办方 B</option>
              <option value="Brand">品牌 Brand</option>
              <option value="G">政府 G</option>
            </select>

            <nav className="space-x-4">
              <Link to="/artist" className="text-sm text-gray-300">艺人查询</Link>
              <Link to="/generate" className="text-sm text-gray-300">AI宣发</Link>
            </nav>
          </div>
        </header>

        <div className="flex gap-6">
          <div className="w-56">
            <Sidebar role={role} />
          </div>
          <div className="flex-1">
            <Routes>
              <Route path="/" element={<Home role={role} />} />
              <Route path="/artist" element={<Artist role={role} />} />
              <Route path="/generate" element={<Generate role={role} />} />
              <Route path="/show/:id" element={<ShowDetail role={role} />} />
            </Routes>
          </div>
        </div>
      </div>

      <BottomNav role={role} />
    </div>
  )
}
