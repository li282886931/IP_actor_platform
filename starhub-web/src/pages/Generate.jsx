import { useState } from 'react'
import { generateAI } from '../api'

export default function Generate({role='B'}){
  const [form, setForm] = useState({ type: 'poster', show_name: '', artist: '', city: '' })
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)

  const handleGenerate = async () =>{
    setLoading(true)
    try{
      // simulate AI latency if backend missing
      const res = await generateAI(form)
      setResult(res.data.result || JSON.stringify(res.data))
    }catch(e){
      console.error(e)
      setResult('生成失败，请检查后端或日志')
    }
    setLoading(false)
  }

  return (
    <div className="flex gap-8 h-[70vh]">
      <div className="w-1/3 card card-white space-y-4">
        <h2 className="text-xl font-bold mb-4">✨ AI 宣发内容生成</h2>

        <select
          className="w-full border rounded-lg px-4 py-2"
          value={form.type}
          onChange={(e) => setForm({...form, type: e.target.value})}
        >
          <option value="poster">海报文案</option>
          <option value="video_script">短视频脚本</option>
        </select>

        <input className="w-full border rounded-lg px-4 py-2" placeholder="演出名称"
          value={form.show_name} onChange={(e) => setForm({...form, show_name: e.target.value})} />
        <input className="w-full border rounded-lg px-4 py-2" placeholder="艺人"
          value={form.artist} onChange={(e) => setForm({...form, artist: e.target.value})} />
        <input className="w-full border rounded-lg px-4 py-2" placeholder="城市"
          value={form.city} onChange={(e) => setForm({...form, city: e.target.value})} />

        <div className="flex items-center gap-3">
          <button
            className="ai-btn"
            onClick={handleGenerate}
          >
            <span className="spark">✨</span>
            {loading ? (<span className="flex items-center gap-2"><span className="loader"></span> AI 生成中...</span>) : '一键生成宣发'}
          </button>
          <button className="px-3 py-2 border rounded">预览</button>
        </div>
      </div>

      <div className="w-2/3 card card-white p-8">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-bold text-lg">生成结果</h3>
          {result && (
            <button
              className="text-sm text-blue-600 hover:underline"
              onClick={() => navigator.clipboard.writeText(result)}
            >
              📋 复制文案
            </button>
          )}
        </div>
        {result ? (
          <div className="bg-gray-50 rounded-lg p-6 text-lg leading-relaxed whitespace-pre-wrap">
            {result}
          </div>
        ) : (
          <div className="flex items-center justify-center h-64 text-gray-400">
            填写左侧信息，点击一键生成（或等待 AI 输出）
          </div>
        )}
      </div>
    </div>
  )
}
