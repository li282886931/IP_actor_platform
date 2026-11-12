import { useState } from 'react'

const priorities = {
  主办方: ['城市消费水平与目标观众的来源证据', '场馆容量、上座率、票价与扣费口径', '预算、资金盘及保本可达性'],
  政府: ['当地可用场馆、审批与安全条件', '项目舆情风险与处置预案', '地方消费带动与公共效益的测算依据'],
  品牌: ['传播体量、数据来源与统计周期', '品牌调性匹配与赞助权益标准', '赞助报价、转化口径与品牌回报依据'],
  资方: ['资金监管、合同保障与分期付款节点', '项目成本回报率与合同收益分配口径', '市场选择与艺人历史票房证据'],
}

export default function DecisionReview({ facts = [], evidences = [], risks = [], gates = [] }) {
  const [role, setRole] = useState('主办方')
  const verified = facts.filter((fact) => fact.status === 'verified' && fact.source?.trim()).length
  return (
    <section className="panel decision-review">
      <div className="panel-heading">
        <div><h3>B 端决策核验</h3><p>先核实来源，再形成决策；外部采集及 AI 建议均需人工核验。</p></div>
        <div className="decision-role-switch" aria-label="决策视角">
          {Object.keys(priorities).map((item) => (
            <button className="button button-secondary" type="button" aria-pressed={role === item}
              key={item} onClick={() => setRole(item)}>{item}</button>
          ))}
        </div>
      </div>
      <div className="decision-review-body">
        <div><strong>{role}核验重点</strong><ul>{priorities[role].map((text) => <li key={text}>{text}</li>)}</ul></div>
        <div className="decision-evidence-summary">
          <span>有来源且已核验事实：{verified} / {facts.length} 条</span>
          <span>证据材料：{evidences.length} 份，需逐项核验</span>
          <span>开放风险：{risks.filter((risk) => risk.status === 'open').length} 项</span>
          <span>未通过关卡：{gates.filter((gate) => !['approved', 'passed', 'completed'].includes(gate.status)).length} 项</span>
        </div>
      </div>
      <div className="button-row">
        <a className="button button-secondary" href="#project-facts">核验事实与来源</a>
        <a className="button button-secondary" href="#project-evidences">补充证据材料</a>
        <a className="button button-secondary" href="#project-risks">查看风险与关卡</a>
      </div>
    </section>
  )
}
