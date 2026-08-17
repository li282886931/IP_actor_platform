import { Routes, Route, Link } from 'react-router-dom'
import Home from './pages/Home'
import Artist from './pages/Artist'
import Generate from './pages/Generate'
import ShowDetail from './pages/ShowDetail'
import Sidebar from './components/Sidebar'

export default function App(){
  return (
    <div className="min-h-screen">
      <div className="container">
        <header className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">🎵 锐音场 StarHub</h1>
          <nav className="space-x-4">
            <Link to="/artist" className="text-sm text-gray-300">艺人查询</Link>
            <Link to="/generate" className="text-sm text-gray-300">AI宣发</Link>
          </nav>
        </header>

        <div className="flex gap-6">
          <div className="w-56">
            <Sidebar />
          </div>
          <div className="flex-1">
            <Routes>
              <Route path="/" element={<Home/>} />
              <Route path="/artist" element={<Artist/>} />
              <Route path="/generate" element={<Generate/>} />
              <Route path="/show/:id" element={<ShowDetail/>} />
            </Routes>
          </div>
        </div>
      </div>
    </div>
  )
}
