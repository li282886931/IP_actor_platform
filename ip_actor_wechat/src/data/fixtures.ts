import type { DisplayItem } from '@/types/domain'

const common: Record<string, DisplayItem[]> = {
  认证: [
    { id: 'auth-1', title: '可信身份', description: '登录后签发统一令牌，跨端身份保持一致', status: '安全' },
    { id: 'auth-2', title: '客户隔离', description: '项目、资料和 Agent 按当前客户空间隔离', status: '最小权限' },
    { id: 'auth-3', title: '人工确认', description: '政策、场地、授权与资金责任由负责人确认', status: '硬门禁' },
  ],
  发现: [
    { id: 'discover-1', title: '华东万人场案例 A', description: '南京 · 12,000 席 · 已核验结算', status: '盈利', value: '+105 万' },
    { id: 'discover-2', title: '城市剧场项目', description: '通过缩小规模降低资金风险', status: '可迁移', value: 'ROI 18%' },
    { id: 'discover-3', title: '十月档期机会', description: '同量级项目存在可比案例，档期仍需核验', status: '待证据', value: '3 例' },
  ],
  项目: [
    { id: 'project-1', title: '星河计划·南京站', description: '艺人 A · 南京 · 2027 年 10 月', status: '调整后推进', value: '+118 万' },
    { id: 'project-2', title: '星河计划·杭州站', description: '档期与场馆报价待补充', status: '缺资料' },
    { id: 'project-3', title: '冬季剧场项目', description: '组合待选 · 2027 年 12 月', status: '草稿' },
  ],
  创建项目: [
    { id: 'create-1', title: '输入可先留待确认', description: '未知成本不会自动按零处理', status: '可保存草稿' },
    { id: 'create-2', title: '资料按客户隔离', description: '草稿只在当前客户空间恢复', status: '受保护' },
  ],
  组合: [
    { id: 'option-1', title: '艺人 A × 南京 × 场馆 A', description: '资金边界内的可比案例更多', status: '建议比较', value: '72 / 100' },
    { id: 'option-2', title: '艺人 B × 杭州 × 场馆 B', description: '热度较高，固定成本可能超预算', status: '资金风险' },
    { id: 'option-3', title: '艺人 C × 成都 × 场馆 C', description: '成本较低，万人场案例不足', status: '缺案例' },
  ],
  财务: [
    { id: 'finance-1', title: '保守情景', description: '65% 上座率 · 利润缓冲较薄', status: '压力边界', value: '+12.86 万' },
    { id: 'finance-2', title: '中性情景', description: '80% 上座率 · 当前判断口径', status: '条件推进', value: '+118.19 万' },
    { id: 'finance-3', title: '乐观情景', description: '95% 上座率 · 不作为销售承诺', status: '上行空间', value: '+223.53 万' },
  ],
  判断: [
    { id: 'call-1', title: '确定性财务结果', description: '中性利润 118.19 万，保本上座率 63.2%', status: 'finance-v1' },
    { id: 'call-2', title: '规则约束', description: '人工门禁未关闭时不能输出无条件推进', status: 'rules-v1' },
    { id: 'call-3', title: 'AI 辅助解释', description: '建议先补齐授权、资金与场地依据', status: '待核验' },
  ],
  依据: [
    { id: 'evidence-1', title: '可用资金 500 万', description: '资金确认单 · 已由负责人核验', status: '已核验' },
    { id: 'evidence-2', title: '可售规模 12,000 人', description: '项目输入 · 待场馆正式确认', status: '待确认' },
    { id: 'evidence-3', title: '场馆容量冲突', description: '项目输入 12,000 与资料 10,500', status: '需处理' },
  ],
  风险: [
    { id: 'risk-1', title: '峰值资金缺口未落实', description: '中性情景缺口 94.61 万', status: '高风险' },
    { id: 'risk-2', title: '艺人授权范围未核验', description: '影响履约、版权与正式签约', status: '高风险' },
    { id: 'risk-3', title: '保守利润缓冲很薄', description: '65% 上座率利润仅 12.86 万', status: '中风险' },
  ],
  门禁: [
    { id: 'gate-1', title: '政策与大型活动审批', description: '负责人已核验示意文件', status: '已确认' },
    { id: 'gate-2', title: '场地承载、消防与安保', description: '容量冲突仍待消解', status: '待确认' },
    { id: 'gate-3', title: '艺人授权、履约与版权', description: '正式授权文件待补充', status: '待确认' },
    { id: 'gate-4', title: '资金拨付与合同责任', description: '资金缺口和亏损承担待确认', status: '待确认' },
  ],
  决策: [
    { id: 'decision-1', title: '落实峰值资金缺口', description: '财务负责人 · 待分配', status: '前置条件' },
    { id: 'decision-2', title: '完成艺人授权核验', description: '商务负责人 · 待分配', status: '前置条件' },
    { id: 'decision-3', title: '完成场地安全确认', description: '地方执行 · 待分配', status: '前置条件' },
  ],
  版本: [
    { id: 'version-1', title: 'V2 · 重新评估', description: '场馆报价变化 · 等待负责人确认', status: '最新', value: '+94.19 万' },
    { id: 'version-2', title: 'V1 · 调整后推进', description: '已由张敏确认，记录不可覆盖', status: '已确认', value: '+118.19 万' },
  ],
  报告: [
    { id: 'report-1', title: '判断摘要与推进条件', description: '利润区间、保本线与关键前提', status: '可查看' },
    { id: 'report-2', title: '三种情景与计算口径', description: '完整假设与可复算结果', status: '可查看' },
    { id: 'report-3', title: '依据、风险和确认记录', description: '来源定位、负责人、版本与时间', status: '受限' },
  ],
  Agent: [
    { id: 'agent-1', title: '确认新增资金安排', description: '财务负责人 · 今天 18:00', status: '优先' },
    { id: 'agent-2', title: '补充艺人授权文件', description: '商务负责人 · 明天 12:00', status: '待证据' },
    { id: 'agent-3', title: '核对场馆报价口径', description: '地方执行 · 明天 18:00', status: '进行中' },
  ],
  任务: [
    { id: 'task-1', title: '确认资金安排', description: '今天 18:00 · 财务 · 未认领', status: '高优先' },
    { id: 'task-2', title: '补充艺人授权范围', description: '明天 12:00 · 商务', status: '进行中' },
    { id: 'task-3', title: '核对场馆售票区域', description: '明天 18:00 · 地方执行', status: '待处理' },
  ],
  巡演: [
    { id: 'tour-1', title: '南京站', description: '10 月 3 日 · 中性利润 +118.19 万', status: '待确认' },
    { id: 'tour-2', title: '杭州站', description: '10 月 10 日 · 场馆报价待补齐', status: '待资料' },
    { id: 'tour-3', title: '成都站', description: '10 月 24 日 · 档期待核实', status: '待核验' },
  ],
  复盘: [
    { id: 'review-1', title: '收入差异', description: '712.80 万预测 / 705.00 万实际', status: '低于预测', value: '-7.80 万' },
    { id: 'review-2', title: '成本差异', description: '594.61 万预测 / 600.00 万实际', status: '高于预测', value: '+5.39 万' },
    { id: 'review-3', title: '校准队列', description: '折扣、结算口径与临时执行费用待核对', status: '3 项' },
  ],
  我的: [
    { id: 'account-1', title: '团队与项目权限', description: '管理成员、角色和项目范围', status: '8 位成员' },
    { id: 'account-2', title: 'Agent 授权设置', description: '内部任务、提醒与对外行为', status: '最小权限' },
    { id: 'account-3', title: '数据授权与隐私', description: '连接、文件、可见范围与撤回', status: '可管理' },
  ],
  设置: [
    { id: 'setting-1', title: '通知偏好', description: '每日摘要、项目异常与任务到期', status: '已开启' },
    { id: 'setting-2', title: '个人信息与隐私', description: '资料访问、授权和账户操作', status: '可管理' },
    { id: 'setting-3', title: '开发者联调', description: '连接 FastAPI 决策服务', status: '开发版本' },
  ],
  状态: [
    { id: 'state-1', title: '操作上下文已保留', description: '恢复后会先检查客户、项目与数据版本', status: '安全恢复' },
    { id: 'state-2', title: '不会静默补造数据', description: '失败不会被解释为没有风险或结果为零', status: '可信边界' },
  ],
}

export const getFixtureItems = (group: string) => common[group] || common.项目

