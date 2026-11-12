import { Link } from 'react-router-dom'
import { getArtistWorkspace } from '../api'
import Avatar from '../components/Avatar'
import { projectStatus, useWorkspace, WorkspaceState } from './workspaceSupport'

const profileLabels = {
  audience: '受众资料', city: '城市', age: '年龄', gender: '性别', summary: '简介',
  positioning: '艺人定位', genres: '音乐风格', region: '地区', source: '资料来源',
  audience_profile: '受众画像', audience_structure: '受众结构', market_position: '市场定位',
  platform: '平台', count: '人数', value: '数值', ratio: '占比', name: '名称',
  market_positioning: '市场定位', touring_box_office_reference: '巡演与票房参考',
  differentiation_with_zhao_yazhi: '与赵雅芝的差异', cooperation_recommendation: '合作建议',
}

function ProfileValues({ value, depth = 0 }) {
  if (value == null || value === '') return <span>待补齐</span>
  if (Array.isArray(value)) return <div className="role-profile-values">{value.map((item, index) =>
    <div key={index}><ProfileValues value={item} depth={depth + 1} /></div>)}</div>
  if (typeof value === 'object') return <dl className="role-profile-values">{Object.entries(value).map(([key, item]) =>
    <div key={key}><dt>{profileLabels[key] || '补充资料'}</dt><dd><ProfileValues value={item} depth={depth + 1} /></dd></div>)}</dl>
  return <span>{typeof value === 'boolean' ? (value ? '是' : '否') : String(value)}</span>
}

function ArtistProfile({ artist }) {
  const fanCount = Number(artist.fan_count)
  return <section className="panel">
    <div className="role-artist-heading"><Avatar name={artist.name} size={52} /><div><h3>{artist.name}</h3><p>{artist.tags || '标签待补齐'}</p></div>
      <span className="role-verification">资料待核验</span></div>
    <dl className="role-value-grid">
      <div><dt>资料库粉丝数</dt><dd>{artist.fan_count == null || artist.fan_count === '' ? '待补齐' : Number.isFinite(fanCount) ? `${fanCount.toLocaleString('zh-CN')} 人` : artist.fan_count}</dd></div>
      <div><dt>资料库热度</dt><dd>{artist.heat_score == null ? '待补齐' : `${artist.heat_score} 分`}</dd></div>
    </dl>
    <p className="role-muted">粉丝与热度来自数据库资料，来源、采集时间及授权范围需人工核验。</p>
    {artist.profile && Object.keys(artist.profile).length > 0 && <details className="role-profile-more"><summary>展开完整资料</summary><ProfileValues value={artist.profile} /></details>}
  </section>
}

export default function ArtistWorkspace({ mode = 'overview' }) {
  const workspace = useWorkspace(getArtistWorkspace)
  if (workspace.status !== 'success') return <WorkspaceState {...workspace} />
  const { artist, projects = [] } = workspace.data || {}
  return <div className="page-stack role-workspace">
    <section className="page-lead"><div><h2>{({ overview: '我的演出工作台', profile: '我的资料', opportunities: '演出机会' })[mode]}</h2>
      <p>查看个人资料、关联演出与专属宣发内容。</p></div>
      <Link className="button button-secondary" to="/generate">创建宣发内容</Link>
    </section>
    {!artist ? <section className="panel state-panel"><strong>尚未关联艺人资料</strong>
      <span>请联系管理员，在用户管理中为当前账号选择对应艺人。</span></section> : <>
      {mode !== 'opportunities' && <ArtistProfile artist={artist} />}
      {mode !== 'profile' && <section className="panel"><div className="panel-heading"><h3>关联演出项目</h3><span className="section-count">{projects.length} 个</span></div>
        {!projects.length ? <div className="state-panel">暂无与您关联的演出项目</div> : <div className="role-opportunity-list">{projects.map(project =>
          <article className="role-opportunity" key={project.id}><div><h4>{project.name}</h4><p>{project.city || '城市待补齐'} · {project.venue || '场馆待补齐'}</p></div>
            <div><span>{project.schedule || '档期待补齐'}</span><small>{projectStatus(project.status)}</small></div></article>)}</div>}
        <p className="role-disclosure">仅显示当前空间明确关联您的项目。报名、签约与结算功能尚未开放，请联系项目主办方。</p>
      </section>}
    </>}
  </div>
}
