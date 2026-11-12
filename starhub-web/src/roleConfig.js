const item = (to, label, short) => ({ to, label, short })
export const roleMeta = {
  Admin: { label: 'root 管理员', title: '创建角色账号', desc: '为主办方、品牌方、政府／文旅、观众、资方和艺人创建账号' },
  B: { label: '主办方', title: '主办方经营工作台', desc: '围绕项目落地、执行待办与经营决策开展工作' },
  Brand: { label: '品牌方', title: '品牌合作工作台', desc: '评估受众匹配、合作目标与交付证据' },
  G: { label: '政府 / 文旅', title: '城市文旅工作台', desc: '查看属地项目、安全材料与文旅成效核验' },
  C: { label: '观众', title: '我的现场', desc: '发现演出，查看属于自己的预约登记' },
  Investor: { label: '资方', title: '资方工作台', desc: '评估项目价值、资金缺口与投资风险' },
  Artist: { label: '艺人', title: '艺人工作台', desc: '管理个人资料、关联演出与内容宣发' },
}
export const navigationByRole = {
  Admin: [item('/users', '创建角色账号', '创建账号')],
  B: [item('/', '经营工作台', '首页'), item('/operations/projects', '项目运营', '项目'), item('/operations/tasks', '执行待办', '待办'), item('/artist', '艺人智策', '艺人'), item('/generate', 'AI 宣发', '宣发')],
  Brand: [item('/', '品牌工作台', '首页'), item('/partnership/opportunities', '合作候选', '候选'), item('/partnership/evidence', '效果与证据', '证据'), item('/artist', '受众洞察', '受众'), item('/generate', 'AI 品宣', '品宣')],
  G: [item('/', '城市工作台', '首页'), item('/city/projects', '城市项目', '项目'), item('/city/review', '审批与安全', '核验'), item('/city/impact', '文旅成效', '成效'), item('/generate', '城市宣发', '宣发')],
  C: [item('/', '我的现场', '首页'), item('/audience/discover', '演出发现', '发现'), item('/audience/reservations', '我的预约', '预约'), item('/artist', '艺人查询', '艺人')],
  Investor: [item('/', '资方工作台', '首页'), item('/investment/projects', '项目评估', '项目'), item('/investment/safeguards', '资金与风险', '资金风险'), item('/artist', '市场与艺人', '艺人')],
  Artist: [item('/', '艺人工作台', '首页'), item('/performer/profile', '我的资料', '资料'), item('/performer/opportunities', '演出机会', '演出机会'), item('/generate', 'AI 宣发', '宣发')],
}
const collaborationLabels = { Admin: '授权与异常协作', B: '项目执行协作', Brand: '品牌合作协作', G: '材料核验协作', Investor: '投资评估协作', Artist: '艺人履约协作', C: '收藏与预约' }
Object.entries(navigationByRole).forEach(([role, entries]) => {
  if (role === 'Admin') return
  entries.splice(1, 0, item('/collaboration', collaborationLabels[role], '协作'))
  entries.push(item('/preferences', '个人关注', '关注'))
})
export const routeTitles = { ...Object.fromEntries(Object.values(navigationByRole).flat().filter(i => i.to !== '/').map(i => [i.to, i.label])), '/collaboration': '角色协作', '/preferences': '个人关注' }
export function roleFromUser(user) {
  if (!user) return null
  if (user.group_code === 'root' || user.account === 'root' || user.can_manage_users) return 'Admin'
  const value = user.group_code || user.role
  return roleMeta[value] ? value : null
}
export function canAccessRoute(role, path) {
  if (navigationByRole[role]?.some(i => i.to === path)) return true
  if (role === 'Admin') return false
  if (/^\/show\/[^/]+$/.test(path)) return true
  if (/^\/projects\/[^/]+$/.test(path)) return role === 'B'
  return false
}
