import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { splitList, useCollaboration } from './collaborationSupport'

export default function PersonalPreferences({ role }) {
  const controller = useCollaboration(), { data, mutate, busy, error, setError } = controller
  const [cities, setCities] = useState(''), [genres, setGenres] = useState(''), [goals, setGoals] = useState([]), [risk, setRisk] = useState([])
  const [start, setStart] = useState(''), [end, setEnd] = useState(''), [note, setNote] = useState(''), [saved, setSaved] = useState(false)
  const [initialized, setInitialized] = useState(false)
  useEffect(() => {
    if (data && !initialized) { setCities(data.focus?.cities?.join('，') || ''); setGenres(data.focus?.genres?.join('，') || ''); setGoals(data.focus?.goals || []); setRisk(data.focus?.risk_levels || []); setInitialized(true) }
  }, [data, initialized])
  async function focus(e) {
    e.preventDefault(); setSaved(false)
    const row = data.personal.find(r => r.type === 'focus')
    if (await mutate('personal', { type: 'focus', record_key: 'default', payload: { cities: splitList(cities), goals, risk_levels: risk, genres: splitList(genres) }, ...(row ? { revision: row.revision } : {}) })) setSaved(true)
  }
  async function reset() {
    const row = data.personal.find(r => r.type === 'focus')
    if (await mutate('personal', { type: 'focus', record_key: 'default', remove: true, ...(row ? { revision: row.revision } : {}) })) {
      setCities(''); setGenres(''); setGoals([]); setRisk([]); setSaved(true)
    }
  }
  async function availability(e) {
    e.preventDefault()
    if (new Date(end) <= new Date(start)) { setError('结束时间须晚于开始时间'); return }
    if (await mutate('personal', { type: 'availability', record_key: crypto.randomUUID(), payload: { start: new Date(start).toISOString(), end: new Date(end).toISOString(), note } })) { setStart(''); setEnd(''); setNote('') }
  }
  const toggle = (setter, value, checked) => setter(old => checked ? [...old, value] : old.filter(v => v !== value))
  return <div className="role-workspace collaboration-workspace"><div className="page-lead"><div><h1>个人关注设置</h1><p>仅保存在当前账号与空间；关注城市、合作目标和风险偏好影响协作列表排序，不扩大访问权限。</p></div><Link className="button button-secondary" to="/collaboration">返回协作事项</Link></div>
    {error && <p className="state-panel error" role="alert">{String(error)} <button onClick={controller.reload}>刷新记录</button></p>}
    {!data ? <p role="status">正在加载个人设置…</p> : <>
      <section className="panel"><h3>我关注的方向</h3><form onSubmit={focus}>
        <div className="collab-form-grid"><label><span>关注城市</span><input aria-label="关注城市" value={cities} onChange={e => setCities(e.target.value)} placeholder="用逗号分隔" /></label>
          <label><span>关注音乐类型</span><input aria-label="关注音乐类型" value={genres} onChange={e => setGenres(e.target.value)} placeholder="用逗号分隔" /></label></div>
        <fieldset className="collab-checks"><legend>合作目标</legend>{['曝光', '互动', '转化'].map(g => <label key={g}><input type="checkbox" checked={goals.includes(g)} onChange={e => toggle(setGoals, g, e.target.checked)} />{g}</label>)}</fieldset>
        <fieldset className="collab-checks"><legend>关注风险级别</legend>{[['low', '低风险'], ['medium', '中风险'], ['high', '高风险']].map(([key, text]) => <label key={key}><input type="checkbox" checked={risk.includes(key)} onChange={e => toggle(setRisk, key, e.target.checked)} />{text}</label>)}</fieldset>
        <p className="role-disclosure">音乐类型偏好已保存；待接入可匹配的艺人类型数据后用于推荐。</p>
        <div className="collab-actions"><button type="button" className="button button-secondary" disabled={busy} onClick={reset}>恢复默认关注</button><button className="button button-primary" disabled={busy}>保存关注设置</button></div>{saved && <p role="status">关注设置已保存</p>}
      </form></section>
      {role === 'Artist' && <section className="panel"><h3>个人档期登记</h3><p className="role-muted">登记不可用时段，用于邀请冲突提示；具体时段和备注仅本人可见。</p><form onSubmit={availability}><div className="collab-form-grid">
        <label><span>开始时间</span><input type="datetime-local" aria-label="档期开始时间" required value={start} onChange={e => setStart(e.target.value)} /></label>
        <label><span>结束时间</span><input type="datetime-local" aria-label="档期结束时间" required value={end} onChange={e => setEnd(e.target.value)} /></label>
        <label><span>个人备注</span><input aria-label="档期个人备注" value={note} onChange={e => setNote(e.target.value)} /></label></div><button className="button button-primary" disabled={busy}>登记档期</button></form>
        {data.personal.filter(r => r.type === 'availability').map(r => <div className="workspace-compact-row" key={r.id}><div><strong>{new Date(r.payload.start).toLocaleString('zh-CN')} — {new Date(r.payload.end).toLocaleString('zh-CN')}</strong><small>{r.payload.note}</small></div><button className="button button-secondary" disabled={busy} onClick={() => mutate('personal', { type: 'availability', record_key: r.record_key, revision: r.revision, remove: true })}>删除档期</button></div>)}
        {!data.personal.some(r => r.type === 'availability') && <p className="role-muted">暂无个人档期登记；未绑定艺人身份时请先联系管理员。</p>}
      </section>}
    </>}
  </div>
}
