import { useEffect, useState } from 'react'
import { listShows } from '../api'
import ShowCard from '../components/ShowCard'

export default function Home(){
  const [shows, setShows] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(()=>{ async function load(){ setLoading(true); try{ const res = await listShows(); setShows(res.data.data || []) }catch(e){ console.error(e) } setLoading(false) } load() },[])

  return (
    <div className="grid grid-cols-3 gap-6">
      {loading && <div className="text-gray-400">加载中…</div>}
      {shows.length===0 && !loading && <div className="col-span-3 text-gray-400">暂无演出，后端启动并有 demo 数据时显示</div>}
      {shows.map(s=> <ShowCard key={s.id} show={s} />)}
    </div>
  )
}
