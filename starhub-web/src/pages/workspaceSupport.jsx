import { useEffect, useState } from 'react'

export function useWorkspace(load) {
  const [state, setState] = useState({ status: 'loading', data: null })
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    setState({ status: 'loading', data: null })
    load().then(response => {
      if (active) setState({ status: 'success', data: response.data.data })
    }).catch(() => {
      if (active) setState({ status: 'error', data: null })
    })
    return () => { active = false }
  }, [load, attempt])
  return { ...state, retry: () => setAttempt(value => value + 1) }
}

export function WorkspaceState({ status, retry }) {
  return <div className={`state-panel${status === 'error' ? ' error' : ''}`} role="status">
    {status === 'error' ? <><strong>工作台数据暂时不可用</strong><span>请检查登录状态或稍后重试。</span>
      <button className="button button-secondary" onClick={retry}>重试</button></> : '正在加载专属工作台…'}
  </div>
}

export const projectStatus = value => ({
  draft: '草稿', pending: '待评审', approved: '已通过', active: '进行中',
  completed: '已完成', rejected: '未通过', cancelled: '已取消',
}[value] || '待确认')
export const money = value => typeof value === 'number' && Number.isFinite(value)
  ? `¥${value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}` : '待补齐'
