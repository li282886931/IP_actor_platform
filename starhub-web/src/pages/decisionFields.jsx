export const stageLabels = { initiation: '立项', approval: '报批', sponsorship: '招商', ticketing: '票务', execution: '执行', review: '复盘' }
export const statusLabels = { pending: '待核验', verified: '已核验', vetoed: '触发否决', pending_input: '参数待补齐', pending_configuration: '规则待配置', requires_plan: '需止损预案', ready_for_review: '待人工评审', calculated: '已计算', work: '作品', update: '动态', live: '直播预告', support: '应援活动' }
export const vetoLabels = { V1: '未拿批文且存在不可退大额支出', V2: '综合保本超过红线', V3: '止损线超过成本阈值，需预案', V4: '劣迹或涉外审批红线', V5: '公售比例低于红线' }
export const kindLabels = { brand_match: '品牌匹配评分', city_fit: '城市资产适配评分', artist_benchmark: '艺人对标评分', incremental: '增量价值', sponsorship: '赞助权益', investment: '投资现金流', asset: '闲置资产', impact: '文旅成效', artist_post: '艺人动态', artist_metrics: '成长数据', wishlist: '年度清单', checkin: '观演打卡', comment: '评论' }
const field = (key, label, type = 'number', options) => ({ key, label, type, options })
export const budgetFields = [
  field('total_cost', '总成本（元）'), field('full_ticket_gross', '满场票房（元）'), field('net_ticket_rate', '净票房率（0–1）'),
  field('sponsorship', '已落实赞助（元）'), field('subsidy', '已落实补贴（元）'), field('expected_occupancy', '预计上座率（0–1）'),
  field('artist_fee', '艺人费用（元）'), field('nonrefundable_spend', '不可退支出（元）'), field('stop_loss_amount', '止损金额（元）'),
  field('public_sale_ratio', '公售比例（0–1）'), field('presale_ratio', '预售比例（0–1）'),
  ...[['permit_received', '批文已收到'], ['artist_misconduct', '存在劣迹风险'], ['foreign_artist', '涉及涉外艺人'], ['foreign_approval', '涉外审批已收到']].map(([k, label]) => field(k, label, 'boolean')),
  { ...field('cost_overrun_ratio', '成本超支比例（实际/预算−1）'), min: -1 },
  field('weather_risk', '有来源的天气风险值（0–1）'), field('reputation_risk', '有来源的舆情风险值（0–1）'),
  field('schedule_conflict', '已确认档期冲突', 'boolean'),
  ...[
    field('ticket_price', '项目定价（元）'), field('willingness_price', '有来源购票意愿价（元）'),
    field('audience_match_ratio', '受众匹配比例（0–1）'), field('comparable_artist_fee', '可比艺人报价（元）'),
    { ...field('fan_growth_ratio', '已观测粉丝增长比例'), min: -1 },
    field('available_funds', '可用资金（元）'), field('contracted_sponsorship', '约定赞助（元）'),
    { ...field('days_until_show', '距演出天数（可为负）'), min: -36500 },
    ...[['demand_verified', '购票需求已核验'], ['supplier_quotes_verified', '供应商报价已核验'],
      ['sponsorship_verified', '赞助凭证已核验'], ['subsidy_verified', '补贴凭证已核验'],
      ['application_submitted', '报批已提交'], ['foreign_approval_verified', '涉外审批证明已核验'],
      ['copyright_authorized', '版权授权已完成'], ['safety_verified', '现场安全已核验'],
      ['insurance_verified', '保险已核验']].map(([k, label]) => field(k, label, 'boolean')),
  ].map(f => ({ ...f, advanced: true })),
  field('source', '参数来源说明', 'text'), field('evidence_ids', '证明材料编号（逗号分隔）', 'ids'),
]
export const recordFields = {
  brand_match: [], city_fit: [], artist_benchmark: [],
  sponsorship: [field('investment', '赞助投入（元）'), field('onsite_exposures', '现场曝光（次）'), field('media_exposures', '传播曝光（次）'),
    field('onsite_cpm', '现场千次曝光价值（元）'), field('media_cpm', '传播千次曝光价值（元）'), field('rights_value', '其他权益价值（元）'),
    field('actual_sales_profit', '实际销售贡献利润（元）'), field('target_audience', '目标受众', 'text'), field('audience_age', '观众年龄', 'text'),
    field('audience_city', '观众城市', 'text'), field('purchasing_power', '消费力', 'text'), field('interests', '观众兴趣', 'text'), field('deliverables', '权益交付', 'textarea')],
  incremental: [field('avoided_projects', '放弃的否决项目数'), field('potential_loss_per_project', '单项目潜在亏损（元）'),
    field('baseline_occupancy', '基准上座率（0–1）'), field('optimized_occupancy', '优化上座率（0–1）'), field('full_ticket_gross', '满场票房（元）'),
    field('net_ticket_rate', '净票房率（0–1）'), field('saved_hours', '节省工时（小时）'), field('hourly_cost', '每小时成本（元）'),
    field('supplier_savings', '供应商节省（元）'), field('share_rate', '约定分成比例（0–1）'), field('attribution', '增量归因与对照依据', 'textarea')],
  investment: [field('invested_amount', '投入本金（元）'), field('supervised_balance', '第三方监管余额（元）'),
    field('stop_loss_amount', '约定止损金额（元）'), field('profit_share', '利润分配比例（0–1）'),
    field('custody_reference', '第三方监管凭证', 'text'), field('due_diligence', '独立尽调意见', 'textarea'), field('exit_plan', '退出与止损预案', 'textarea')],
  asset: [field('city', '资产城市', 'text'), field('category', '资产类别', 'select', [['venue', '场馆'], ['scenic', '景区'], ['stadium', '体育场']]),
    field('venue_id', '关联场馆编号'), field('capacity', '可用容量（人）'), field('idle_days', '闲置天数（天）'),
    field('activation_cost', '盘活投入（元）'), field('operating_income', '经营收入（元）'), field('operating_cost', '经营成本（元）'),
    field('suitable_genres', '适合品类（逗号分隔）', 'list'), field('operating_plan', '盘活运营方案', 'textarea')],
  impact: [field('city', '成效城市', 'text'), field('period', '统计期间', 'text'), field('subsidy', '财政补贴（元）'),
    field('visitor_spend', '观众直接消费（元）'), field('consumption_coefficient', '消费带动系数'), field('coefficient_source', '系数来源', 'text'),
    field('attributable_revenue', '可归因收入（元）')],
  artist_post: [field('post_type', '发布类型', 'select', [['update', '动态'], ['work', '作品'], ['live', '直播预告'], ['support', '应援活动']]),
    field('content', '发布正文', 'textarea'), field('scheduled_at', '活动日期', 'date'), field('link', '官方作品或活动链接', 'url')],
  artist_metrics: [field('observed_at', '数据日期', 'date'), field('city', '统计城市', 'text'), field('fan_count', '粉丝人数（人）'),
    field('heat', '来源热度值'), field('ticket_gross', '实际票房（元）'), field('artist_fee', '秀费收入（元）'),
    field('sponsorship', '赞助收入（元）'), field('merchandise', '衍生收入（元）'), field('live_income', '直播收入（元）')],
  wishlist: [field('year', '计划年份'), field('show_ids', '想看演出编号（逗号分隔）', 'ids'), field('note', '年度心愿说明', 'textarea')],
  checkin: [field('show_id', '演出编号'), field('attended_at', '观演日期', 'date'), field('content', '现场分享', 'textarea'), field('public', '公开展示打卡', 'boolean')],
}
export const valueLabels = {
  ...Object.fromEntries([...budgetFields, ...Object.values(recordFields).flat()].map(f => [f.key, f.label])),
  pure_breakeven: '纯票房保本上座率', comprehensive_breakeven: '综合保本上座率', predicted_profit: '预测利润（元）',
  potential_avoided_loss: '潜在避坑增量（元）', earned_increment: '多赚增量（元）', efficiency_increment: '效率增量（元）',
  operating_increment: '经营增量（元）', realized_increment: '已实现增量（元）', share_amount: '可计分成（元）',
  verification_status: '核验状态', counterfactual_notice: '核算说明', total_value: '权益总价值（元）',
  exposure_value: '曝光等价价值（元）', roi: '估值ROI', sales_roi: '销售ROI', valuation_notice: '估值口径',
  irr: '年化IRR', irr_note: 'IRR说明', net_cashflow: '净现金流（元）', custody_notice: '资金说明',
  activation_profit: '盘活净收益（元）', activation_roi: '盘活ROI', consumption_impact: '消费带动（元）',
  subsidy_leverage: '补贴杠杆倍数', cashflows: '现金流明细', artist_id: '艺人编号',
}
export function Fields({ fields, values, setValues }) {
  return <div className="decision-form-grid">{fields.map(f => <label key={f.key}><span>{f.label}</span>
    {f.type === 'textarea' ? <textarea aria-label={f.label} value={values[f.key] ?? ''} onChange={e => setValues(v => ({ ...v, [f.key]: e.target.value }))} rows={3} />
      : f.type === 'boolean' || f.type === 'select' ? <select aria-label={f.label} value={values[f.key] ?? ''} onChange={e => setValues(v => ({ ...v, [f.key]: e.target.value }))}>
        <option value="">待填写</option>{(f.type === 'boolean' ? [['true', '是'], ['false', '否']] : f.options).map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select>
        : <input aria-label={f.label} type={['ids', 'list'].includes(f.type) ? 'text' : f.type} min={f.type === 'number' ? f.min ?? 0 : undefined} step={f.type === 'number' ? 'any' : undefined}
          value={values[f.key] ?? ''} onChange={e => setValues(v => ({ ...v, [f.key]: e.target.value }))} />}
  </label>)}</div>
}
export function parseFields(fields, values) {
  return Object.fromEntries(fields.filter(f => values[f.key] !== undefined && values[f.key] !== '').map(f => {
    const raw = values[f.key]
    if (f.type === 'ids') {
      const ids = String(raw).split(/[,，]/).map(x => x.trim()).filter(Boolean)
      if (ids.some(x => !/^[1-9]\d*$/.test(x))) throw new Error('编号须为正整数，以逗号分隔')
      return [f.key, ids.map(Number)]
    }
    return [f.key, f.type === 'number' ? Number(raw) : f.type === 'boolean' ? raw === 'true' || raw === true : f.type === 'list' ? String(raw).split(/[,，]/).map(x => x.trim()).filter(Boolean) : raw]
  }))
}
export const percent = value => typeof value === 'number' ? `${(value * 100).toFixed(2)}%` : '待补齐'
export function Values({ values }) {
  return <dl className="decision-values">{Object.entries(values || {}).filter(([key]) => valueLabels[key]).map(([key, value]) => <div key={key}>
    <dt>{valueLabels[key]}</dt><dd>{value == null ? '待补齐' : ['roi', 'sales_roi', 'irr', 'pure_breakeven', 'comprehensive_breakeven'].includes(key) ? percent(value)
      : Array.isArray(value) ? value.map(x => typeof x === 'object' ? `${x.date}：${x.amount} 元` : String(x)).join('；') || '暂无'
        : typeof value === 'boolean' ? value ? '是' : '否' : typeof value === 'number' ? value.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) : statusLabels[value] || String(value)}</dd>
  </div>)}</dl>
}
