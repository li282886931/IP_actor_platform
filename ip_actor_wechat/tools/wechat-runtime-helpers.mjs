export const toggleSelection = (values, value) => (
  values.includes(value) ? values.filter((item) => item !== value) : values.concat(value)
)

export const detailUrl = ({ entity_type: entityType, entity_id: entityId }) => (
  `/pages/entity-detail/index?entityType=${encodeURIComponent(entityType)}&entityId=${entityId}`
)

export const runtimeHelperSource = `const toggleSelection = (values, value) => (
  values.includes(value) ? values.filter((item) => item !== value) : values.concat(value)
)

const detailUrl = (entityType, entityId) => (
  '/pages/entity-detail/index?entityType=' + encodeURIComponent(entityType) + '&entityId=' + entityId
)

const formatWan = (value) => {
  const abs = Math.abs(value)
  if (abs >= 100000000) return (value / 100000000).toFixed(1) + '亿'
  if (abs >= 10000) return (value / 10000).toFixed(1) + '万'
  return String(Math.round(value))
}

const ringData = (percent, label, caption, tone) => {
  if (!isFinite(percent)) return null
  const rounded = Math.round(percent)
  const clamped = Math.max(0, Math.min(100, rounded))
  const colors = { gold: '#d4af37', success: '#5cc793', warning: '#e2ab57', danger: '#f0837f' }
  return {
    percent: rounded,
    label,
    caption,
    style: 'background-image: conic-gradient(' + (colors[tone] || colors.gold) + ' ' + (clamped * 3.6) + 'deg, rgba(255,255,255,0.08) 0deg);'
  }
}

const buildCharts = (screenId, data) => {
  const charts = { metrics: [], breakevenRing: null, scenarioBars: [], ticketingRing: null }
  const rawItems = (data && Array.isArray(data.items)) ? data.items : []
  const countBy = (status) => rawItems.filter((item) => item.status === status).length
  const options = (data && data.options) || {}

  if (screenId === 'S04') {
    charts.metrics = [
      { label: '全部演出', value: String(rawItems.length), hint: '来自真实演出数据', tone: 'default' },
      { label: '售票中', value: String(countBy('on_sale')), tone: 'success' },
      { label: '已完成案例', value: String(countBy('completed')), tone: 'default' },
      { label: '待评估机会', value: String(countBy('opportunity')), tone: 'default' }
    ]
  } else if (screenId === 'S10') {
    const pendingConfirmation = countBy('pending_confirmation')
    charts.metrics = [
      { label: '全部项目', value: String(rawItems.length), tone: 'default' },
      { label: '进行中', value: String(rawItems.filter((item) => item.status !== 'archived').length), tone: 'success' },
      { label: '已测算', value: String(countBy('calculated')), tone: 'default' },
      { label: '待确认', value: String(pendingConfirmation), tone: pendingConfirmation ? 'warning' : 'default' }
    ]
  } else if (screenId === 'S52') {
    const briefing = options.work_briefing || {}
    const activeCount = briefing.active_project_count != null
      ? briefing.active_project_count
      : (Array.isArray(options.available_projects) ? options.available_projects.length : 0)
    charts.metrics = [
      {
        label: '待办任务',
        value: String(rawItems.length),
        tone: rawItems.length ? 'danger' : 'default',
        url: '/pages/s55/index'
      },
      {
        label: '进行中项目',
        value: String(activeCount),
        tone: 'success',
        url: '/pages/s10/index',
        tab: true
      },
      {
        label: '今日首要',
        value: briefing.top_task ? String(briefing.top_task.title || '') : '无待办',
        hint: briefing.top_task ? String(briefing.top_task.project_name || '') : '',
        tone: 'default',
        url: briefing.top_task ? '/pages/s55/index' : ''
      }
    ]
  }

  if (screenId === 'S11' || screenId === 'S25') {
    const cockpit = options.decision_cockpit || options.finance_cockpit
    if (cockpit) {
      const breakeven = Number(cockpit.breakeven_attendance)
      const capacity = screenId === 'S11'
        ? Number(cockpit.combination && cockpit.combination.venue_capacity)
        : Number(options.project && options.project.venue_capacity)
      if (isFinite(breakeven) && breakeven > 0 && isFinite(capacity) && capacity > 0) {
        const percent = (breakeven / capacity) * 100
        charts.breakevenRing = ringData(
          percent,
          '保本上座率',
          '保本 ' + breakeven.toLocaleString('zh-CN') + ' 人 · 容量 ' + capacity.toLocaleString('zh-CN') + ' 人',
          percent > 90 ? 'danger' : percent >= 75 ? 'warning' : 'gold'
        )
      }
      if (screenId === 'S25' && cockpit.scenarios) {
        const entries = [['conservative', '保守'], ['neutral', '中性'], ['optimistic', '乐观']]
        const profits = entries
          .map(function (entry) { return cockpit.scenarios[entry[0]] && cockpit.scenarios[entry[0]].profit })
          .filter(function (value) { return typeof value === 'number' && isFinite(value) })
        const maxAbs = Math.max.apply(null, profits.map(Math.abs).concat([1]))
        charts.scenarioBars = entries
          .filter(function (entry) {
            const scenario = cockpit.scenarios[entry[0]]
            return scenario && typeof scenario.profit === 'number' && isFinite(scenario.profit)
          })
          .map(function (entry) {
            const value = cockpit.scenarios[entry[0]].profit
            const negative = value < 0
            const ratio = Math.max(Math.abs(value) / maxAbs, value === 0 ? 0 : 0.02) * 50
            return {
              label: entry[1],
              valueText: (negative ? '-' : '') + formatWan(Math.abs(value)),
              negative,
              fillStyle: (negative ? 'right' : 'left') + ':50%;width:' + ratio.toFixed(2) + '%;'
            }
          })
      }
    }
  }

  if (screenId === 'S64' && options.ticketing_loop) {
    const loop = options.ticketing_loop
    const sold = Number(loop.current_sold_count)
    const forecast = Number(loop.forecast_attendance)
    if (isFinite(sold) && isFinite(forecast) && forecast > 0) {
      const variance = Number(loop.attendance_variance)
      let caption = '已售 ' + sold.toLocaleString('zh-CN') + ' 张 · 预计 ' + forecast.toLocaleString('zh-CN') + ' 张'
      if (isFinite(variance)) {
        caption += ' · 偏差 ' + (variance > 0 ? '+' : '') + variance.toLocaleString('zh-CN')
      }
      charts.ticketingRing = ringData(
        (sold / forecast) * 100,
        '售票进度 · 对比中性预计',
        caption,
        variance < 0 ? 'warning' : 'success'
      )
    }
  }

  return charts
}
`
