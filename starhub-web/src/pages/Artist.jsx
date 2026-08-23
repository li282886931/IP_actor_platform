import { useState } from 'react'
import { searchArtist } from '../api'

export default function Artist({role='B'}) {
  const [query, setQuery] = useState('')
  const [artist, setArtist] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleSearch = async () => {
    if(!query) return
    setLoading(true)
    try{
      const res = await searchArtist(query)
      setArtist(res.data.data && res.data.data[0] ? res.data.data[0] : null)
    }catch(e){
      console.error(e)
      setArtist(null)
    }
    setLoading(false)
  }

  return (
    <div className="space-y-6">
      <div className="card card-white p-6">
        <h2 className="text-2xl font-bold mb-3">🔍 艺人热度查询</h2>
        <div className="flex gap-3">
          <input
            className="flex-1 border rounded-lg px-4 py-3"
            placeholder="输入艺人名字，如：周杰伦"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button
            className="ai-btn"
            onClick={handleSearch}
          >
            {loading ? '查询中...' : (<><span className="spark">✨</span> 查询热度</>)}
          </button>
        </div>

        {role === 'B' && (
          <div className="mt-3 text-sm text-gray-600">在此可进行项目立项与快速导出艺人报告。</div>
        )}
      </div>

      {artist ? (
        <div className="card card-white p-6">
          <div className="flex items-center gap-6 mb-6">
            <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center text-white text-2xl font-bold">
              {artist.name && artist.name[0]}
            </div>
            <div>
              <h1 className="text-3xl font-bold">{artist.name}</h1>
              <span className="text-gray-500">{artist.tags}</span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold text-blue-600">{artist.heat_score}</div>
              <div className="text-sm text-gray-500">综合热度</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold text-green-600">{artist.fan_count}</div>
              <div className="text-sm text-gray-500">全网粉丝</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold text-orange-600">{artist.risk_level}</div>
              <div className="text-sm text-gray-500">风险等级</div>
            </div>
          </div>

          <div className="bg-blue-50 rounded-lg p-4">
            <h3 className="font-bold text-blue-800 mb-2">🤖 AI 演出建议</h3>
            <p className="text-blue-700">
              该艺人当前热度极高，建议在<strong>一线城市</strong>举办大型场馆演出，预估单场票房可达 <strong>3000万+</strong>。最佳档期：暑期/国庆。
            </p>
          </div>
        </div>
      ) : (
        <div className="card p-12 text-center text-gray-400">在上方输入艺人名字并点击“查询热度”以查看结果</div>
      )}
    </div>
  )
}
