export default function ScoreBreakdown({ result }) {
  if (!result) return null
  const display = value => value == null ? '待补齐' : typeof value === 'boolean' ? (value ? '是' : '否') : Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 4 })
  return <div className="decision-score">
    <p><strong>{result.value == null ? '评分参数待补齐' : `${result.value} / ${result.max}`}</strong>
      {result.rule_version_id && <span> · 规则 #{result.rule_version_id}</span>}</p>
    {result.missing?.length > 0 && <p className="role-disclosure">缺项：{result.missing.map(k => result.dimensions?.find(d => d.metric === k)?.label || k).join('、')}。缺项保留原权重，不计算完整总分。</p>}
    {result.source && <p>来源：{result.source}</p>}
    {result.notice && <p>{result.notice}</p>}
    <details><summary>分项原值、归一公式与贡献</summary>
      {(result.dimensions || []).map(d => <div className="decision-score-row" key={d.key}>
        <strong>{d.label}</strong><span>原值 {display(d.raw_value)} · 得分 {display(d.score)} / {d.max_score}</span>
        <span>权重 {d.weight} · 贡献 {display(d.contribution)} 分</span>
        <small>{d.formula} {d.source && `· ${d.source}`}</small>
      </div>)}
    </details>
  </div>
}
