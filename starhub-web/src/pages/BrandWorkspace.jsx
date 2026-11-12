import { useState } from 'react'
import { Link } from 'react-router-dom'
import { getBrandWorkspace } from '../api'
import PersonalInbox from '../components/PersonalInbox'
import WorkspaceProjects from '../components/WorkspaceProjects'
import { useWorkspace, WorkspaceState } from './workspaceSupport'

const goals = {
  awareness: '核验渠道发布记录、品牌露出位置、触达口径与去重方法；曝光数据待接入。',
  engagement: '核验现场互动、品牌体验参与记录、有效参与定义与授权范围；互动数据待接入。',
  conversion: '核验转化归因、核销记录、统计周期与退款剔除规则；转化数据待接入。',
}
export default function BrandWorkspace({ mode = 'overview' }) {
  const workspace = useWorkspace(getBrandWorkspace)
  const [goal, setGoal] = useState('awareness')
  const [query, setQuery] = useState('')
  if (workspace.status !== 'success') return <WorkspaceState {...workspace} />
  const { projects = [], personal } = workspace.data || {}
  const visible = projects.filter(p => `${p.name} ${p.city} ${p.artist_name}`.includes(query.trim()))
  return <div className="page-stack role-workspace">
    <section className="page-lead"><div><h2>{({ overview: '品牌合作工作台', opportunities: '合作候选', evidence: '效果与证据' })[mode]}</h2><p>围绕目标受众和可验收权益评估合作。候选项目尚不代表签约。</p></div><Link className="button button-secondary" to="/artist">查看受众资料</Link></section>
    {mode === 'overview' && <PersonalInbox personal={personal} role="Brand" data={workspace.data} />}
    <section className="panel brand-goal-panel"><div className="panel-heading"><h3>合作目标与验收口径</h3>
      <label className="field"><span>合作目标</span><select aria-label="合作目标" value={goal} onChange={e => setGoal(e.target.value)}><option value="awareness">品牌认知</option><option value="engagement">现场互动</option><option value="conversion">销售转化</option></select></label></div><p>{goals[goal]}</p>
      <p className="role-disclosure">权益清单、签约金额与效果指标需由真实合作材料补齐，当前不计算品牌投资回报率。</p></section>
    <section className="panel"><div className="panel-heading"><h3>{mode === 'evidence' ? '项目材料核验' : '可评估合作候选'}</h3><span className="section-count">{visible.length} 个</span></div>
      <label className="field role-search"><span>搜索合作项目</span><input value={query} onChange={e => setQuery(e.target.value)} placeholder="项目、城市或艺人" /></label>
      <WorkspaceProjects projects={visible} /></section>
  </div>
}
