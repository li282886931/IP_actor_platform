import { useState } from 'react'
import { Link } from 'react-router-dom'
import { roleMeta } from '../roleConfig'
import { projectStatus } from '../pages/workspaceSupport'

// Guidance paths are deliberately separate from the states of persisted records.
const paths = {
  Admin: [['创建角色账号', '/users']],
  B: [['资料与测算', '/operations/projects'], ['关卡与决策', '/operations/projects'], ['分派与执行', '/collaboration'], ['交付与验收', '/collaboration']],
  Brand: [['合作候选', '/partnership/opportunities'], ['提交合作需求', '/collaboration'], ['权益共同确认', '/collaboration'], ['效果与证据', '/partnership/evidence']],
  G: [['城市项目', '/city/projects'], ['审批与安全', '/city/review'], ['材料核验', '/city/review'], ['文旅成效', '/city/impact']],
  Investor: [['项目评估', '/investment/projects'], ['版本与回报', '/collaboration'], ['资金与风险', '/investment/safeguards'], ['提交投资意见', '/collaboration']],
  Artist: [['我的资料', '/performer/profile'], ['维护个人档期', '/preferences'], ['邀约与履约', '/collaboration'], ['AI 宣发', '/generate']],
  C: [['演出发现', '/audience/discover'], ['详情与预约', '/audience/discover'], ['我的预约', '/audience/reservations'], ['购票与入场', null]],
}
const gaps = {
  Admin: 'root 仅创建业务角色账号，业务事项由对应角色账号处理。',
  B: '任务分派、提交与验收可在协作页处理；外部合同签约、付款待接入。',
  Brand: '合作需求、权益确认与交付验收可在协作页处理；合同签署、广告归因待接入。',
  G: '审批来源与实际成效可人工登记并核验；法定审批结果自动查询待接入，系统关卡通过不代表法定许可。',
  Investor: '投资意见与版本对照可在协作页处理；出资承诺签约、付款待接入，测算回报不代表合同收益。',
  Artist: '档期维护、邀约回复与资料核验已提供入口；合同签署与结算待接入。',
  C: '购票、支付与核销待接入；预约登记不代表已购票或取得入场资格。',
}
const owners = { root: '管理员', ...Object.fromEntries(Object.entries(roleMeta).map(([key, value]) => [key, value.label])) }
const jobStates = { queued: '排队中', pending: '待执行', running: '采集中', completed: '采集完成，待核验', failed: '采集失败', error: '采集异常' }

function ProjectFlow({ project, role }) {
  const gates = project.gates || []
  const pending = gates.filter(g => g.status !== 'passed')
  const openRisks = (project.risks || []).filter(r => !['resolved', 'closed'].includes(r.status))
  return <details className="agenda-project">
    <summary><strong>{project.name}</strong><span>{projectStatus(project.status)}</span><small>{role === 'Artist' ? '出演安排待确认' : gates.length ? `${pending.length} 项关卡未通过` : '关卡清单待补齐'}</small></summary>
    <div className="agenda-project-content">
      {gates.map(g => <article className="agenda-gate" key={g.id}>
        <strong>{g.name}</strong><span className="status-badge">{g.status === 'passed' ? '系统关卡通过' : g.status === 'pending' ? '待核验' : '状态待确认'}</span>
        <p>责任角色：{owners[g.owner_group] || '负责人待指定'}</p>
        <p>{g.status === 'passed' ? '下一步：保留核验凭证并关注条件变化' : `下一步：补齐并核验 · ${g.required_evidence || '所需材料待明确'}`}</p>
      </article>)}
      {!gates.length && <p className="role-muted">{role === 'Artist' ? `项目安排：${project.schedule || '档期待确认'} · ${project.venue || '场馆待确认'}。下一步：向主办方确认出演安排与流程状态，当前未提供关卡信息。` : '下一步：由主办方补齐关卡清单及责任角色，当前无法判断流程进度。'}</p>}
      {project.evidence && <p className="role-muted">{project.evidence.pending ?? 0} 份证据待核验 · {openRisks.length} 项开放风险</p>}
      {role === 'B' && <Link className="button button-secondary" to={`/projects/${project.id}`}>查看项目流程</Link>}
    </div>
  </details>
}

export default function WorkspaceFlow({ role, data = {} }) {
  const [expanded, setExpanded] = useState(false)
  if (!paths[role]) return null
  const projects = data.projects || []
  const records = role === 'Admin' ? data.jobs || [] : role === 'C' ? data.reservations || [] : projects
  const shown = expanded ? records : records.slice(0, 3)
  return <section className="panel workspace-flow">
    <div className="panel-heading"><h3>工作流程</h3><span className="section-count">{roleMeta[role].label} · 工作路径</span></div>
    <ol className="agenda-path" aria-label={`${roleMeta[role].label}工作路径`}>
      {paths[role].map(([label, to], index) => <li key={label}><span className="agenda-step">{index + 1}</span><div>
        {to ? <Link to={to}>{label}</Link> : <strong>{label}</strong>}<small>{to ? '查看入口' : '待接入'}</small>
      </div></li>)}
    </ol>
    <p className="role-disclosure">以上为操作路径，当前状态以下方实际记录为准，各关卡可并行处理。</p>
    <div className="agenda-live">
      <h4>{role === 'Admin' ? '采集流程当前状态' : role === 'C' ? '我的预约当前状态' : '项目流程当前状态'}</h4>
      {role === 'Artist' && <p className="role-muted">{data.artist ? '已关联艺人资料 · 下一步：核验资料并查看关联项目' : '尚未关联艺人资料 · 下一步：联系管理员绑定资料'}</p>}
      {shown.map(record => role === 'Admin' ? <article className="agenda-gate" key={record.id}>
        <strong>{record.purpose || `采集任务 ${record.id}`}</strong><span className="status-badge">{jobStates[record.status] || '状态待确认'}</span>
        <p>下一步：{['failed', 'error'].includes(record.status) ? '由数据接入人员核查失败原因' : record.status === 'completed' ? '由资料核验人员检查结果与来源' : ['queued', 'pending', 'running'].includes(record.status) ? '等待采集结果，关注数据接入状态' : '联系数据接入人员确认当前状态'}</p>
      </article> : role === 'C' ? <p className="role-muted" key={record.id}>{record.show?.title || '演出信息待确认'} · {record.status === 'cancelled' ? '已取消登记' : '已登记'} · 下一步：查看演出详情与通知</p>
        : <ProjectFlow project={record} role={role} key={record.id} />)}
      {!records.length && <p className="role-muted">{role === 'Admin' ? '暂无采集记录，请先查看数据接入配置。' : role === 'C' ? '暂无预约，请先发现演出并查看详情。' : '暂无可展示的项目流程，请先确认关联项目。'}</p>}
      {records.length > 3 && <button className="agenda-expand" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>{expanded ? '收起流程记录' : `展开全部 ${records.length} 条流程记录`}</button>}
    </div>
    <p className="role-disclosure">{gaps[role]}</p>
  </section>
}
