// 纯 CSS 图表组件：环形进度、情景利润分歧柱状图、分段状态条
// 与小程序端 ScreenPrimitives 中的同名图表保持同一视觉语言（影院深色 + 鎏金）

const ringToneColors = {
  gold: '#d4af37',
  green: '#5cc793',
  amber: '#e2ab57',
  red: '#f0837f',
}

const segmentToneClass = {
  gold: 'seg-gold',
  green: 'seg-green',
  amber: 'seg-amber',
  muted: 'seg-muted',
  muted2: 'seg-muted2',
}

function normalizePercent(value) {
  if (!Number.isFinite(value)) return { display: 0, clamped: 0 }
  const display = Math.round(value)
  return { display, clamped: Math.max(0, Math.min(100, display)) }
}

export function formatCompactCurrency(value) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '-'
  const abs = Math.abs(value)
  if (abs >= 100000000) return `${(value / 100000000).toFixed(1)}亿`
  if (abs >= 10000) return `${(value / 10000).toFixed(1)}万`
  return String(Math.round(value))
}

export function ProgressRing({ percent, label, caption, tone = 'gold' }) {
  const { display, clamped } = normalizePercent(percent)
  const color = ringToneColors[tone] || ringToneColors.gold
  return (
    <div className="progress-ring-block">
      <div
        className="progress-ring"
        role="img"
        aria-label={`${label} ${display}%`}
        style={{
          '--ring-progress': `${clamped * 3.6}deg`,
          backgroundImage: `conic-gradient(${color} ${clamped * 3.6}deg, rgba(255, 255, 255, 0.08) 0deg)`,
        }}
      >
        <div className="progress-ring-inner">
          <strong>{display}%</strong>
        </div>
      </div>
      <div className="progress-ring-meta">
        <span className="progress-ring-label">{label}</span>
        {caption ? <small>{caption}</small> : null}
      </div>
    </div>
  )
}

export function ScenarioBarChart({ items, note }) {
  const validItems = items.filter((item) => typeof item.value === 'number' && Number.isFinite(item.value))
  if (!validItems.length) return null
  const maxAbs = Math.max(...validItems.map((item) => Math.abs(item.value)), 1)

  return (
    <div className="scenario-chart">
      {validItems.map((item) => {
        const negative = item.value < 0
        const ratio = Math.max(Math.abs(item.value) / maxAbs, item.value === 0 ? 0 : 0.02) * 50
        return (
          <div className="scenario-row" key={item.label}>
            <span className="scenario-label">{item.label}</span>
            <span className="scenario-track">
              <span className="scenario-zero" />
              <span
                className={`scenario-fill ${negative ? 'negative' : 'positive'}`}
                style={negative ? { right: '50%', width: `${ratio}%` } : { left: '50%', width: `${ratio}%` }}
              />
            </span>
            <span className={`scenario-value${negative ? ' negative' : ''}`}>
              {negative ? '-' : ''}{formatCompactCurrency(Math.abs(item.value))}
            </span>
          </div>
        )
      })}
      {note ? <small className="scenario-chart-note">{note}</small> : null}
    </div>
  )
}

export function SegmentedBar({ segments }) {
  const visible = segments.filter((segment) => Number.isFinite(segment.value) && segment.value > 0)
  const total = visible.reduce((sum, segment) => sum + segment.value, 0)
  if (!total) return <div className="segmented-empty">暂无状态数据</div>

  return (
    <div className="segmented-wrap">
      <div className="segmented-bar" aria-label="项目状态分布">
        {visible.map((segment) => (
          <span
            key={segment.label}
            className={`segment ${segmentToneClass[segment.tone] || segmentToneClass.muted}`}
            style={{ width: `${(segment.value / total) * 100}%` }}
            title={`${segment.label} ${segment.value}`}
          />
        ))}
      </div>
      <ul className="segmented-legend">
        {visible.map((segment) => (
          <li key={segment.label}>
            <i className={segmentToneClass[segment.tone] || segmentToneClass.muted} />
            {segment.label}
            <strong>{segment.value}</strong>
          </li>
        ))}
      </ul>
    </div>
  )
}
