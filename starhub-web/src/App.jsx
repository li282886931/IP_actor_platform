import { Routes, Route } from 'react-router-dom'
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
    <div className="min-h-screen">
      <div className="container">
        <header className="flex items-center justify-between mb-4">
          <div className="header">
            <div className="logo-badge">锐</div>
            <div>
              <div className="header-title">锐音场 StarHub</div>
              <div className="header-sub">AI 驱动 · 演出全链路智能服务平台</div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <select value={role} onChange={e=>setRole(e.target.value)} className="px-3 py-1 rounded border bg-transparent text-white">
              <option value="C">观众 C</option>
              <option value="B">主办方 B</option>
              <option value="Brand">品牌 Brand</option>
              <option value="G">政府 G</option>
            </select>
          </div>
        </header>

        {/* Top horizontal nav */}
        <BottomNav role={role} />

        <div className="flex gap-6 mt-4">
          {role !== 'C' && (
            <div className="w-56">
              <Sidebar role={role} />
            </div>
          )}

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
    </div>
  )
}
