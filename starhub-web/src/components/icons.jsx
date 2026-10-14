// Single-weight line icon system (1.7 stroke, round caps).
// Every icon inherits `currentColor` so the gold/ink themes control it.

function Svg({ children, size = 22, ...props }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {children}
    </svg>
  )
}

export function HomeIcon(props) {
  return (
    <Svg {...props}>
      <path d="M3.5 10.7 12 3.8l8.5 6.9" />
      <path d="M5.5 9.6V20h13V9.6" />
      <path d="M9.5 20v-5.4h5V20" />
    </Svg>
  )
}

export function CompassIcon(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="m15.6 8.4-2.1 5.1-5.1 2.1 2.1-5.1 5.1-2.1Z" />
    </Svg>
  )
}

export function SparkIcon(props) {
  return (
    <Svg {...props}>
      <path d="M12 3.5c.5 4.2 2.3 6 6.5 6.5-4.2.5-6 2.3-6.5 6.5-.5-4.2-2.3-6-6.5-6.5C9.7 9.5 11.5 7.7 12 3.5Z" />
      <path d="M18.4 14.6c.2 1.7.9 2.4 2.6 2.6-1.7.2-2.4.9-2.6 2.6-.2-1.7-.9-2.4-2.6-2.6 1.7-.2 2.4-.9 2.6-2.6Z" />
    </Svg>
  )
}

export function UsersIcon(props) {
  return (
    <Svg {...props}>
      <circle cx="9" cy="8.2" r="3.1" />
      <path d="M3.4 19.6c.6-3.1 2.7-4.7 5.6-4.7s5 1.6 5.6 4.7" />
      <path d="M15.4 5.4a3.1 3.1 0 0 1 0 5.7" />
      <path d="M17.1 15.1c1.9.5 3.1 2 3.5 4.5" />
    </Svg>
  )
}

export function FolderIcon(props) {
  return (
    <Svg {...props}>
      <path d="M3.5 6.8A1.8 1.8 0 0 1 5.3 5h4.1l2 2.2h7.3a1.8 1.8 0 0 1 1.8 1.8v8.2a1.8 1.8 0 0 1-1.8 1.8H5.3a1.8 1.8 0 0 1-1.8-1.8V6.8Z" />
    </Svg>
  )
}

export function CalendarIcon(props) {
  return (
    <Svg {...props}>
      <rect x="3.8" y="5.2" width="16.4" height="15" rx="2" />
      <path d="M3.8 9.6h16.4M8 3.4v3.4M16 3.4v3.4" />
      <path d="M8 13.4h.01M12 13.4h.01M16 13.4h.01M8 17h.01M12 17h.01" />
    </Svg>
  )
}

export function TicketIcon(props) {
  return (
    <Svg {...props}>
      <path d="M4 8.2A1.8 1.8 0 0 1 5.8 6.4h12.4A1.8 1.8 0 0 1 20 8.2v1.5a1.9 1.9 0 0 0 0 3.8v1.5a1.8 1.8 0 0 1-1.8 1.8H5.8A1.8 1.8 0 0 1 4 15v-1.5a1.9 1.9 0 0 0 0-3.8V8.2Z" />
      <path d="M14 6.8v10.4" strokeDasharray="2.4 2.6" />
    </Svg>
  )
}

export function WalletIcon(props) {
  return (
    <Svg {...props}>
      <path d="M4 7.4A1.9 1.9 0 0 1 5.9 5.5h10.4A1.9 1.9 0 0 1 18.2 7.4v.9H5.9A1.9 1.9 0 0 0 4 10.2V7.4Z" />
      <path d="M4 10.2a1.9 1.9 0 0 1 1.9-1.9H18.2A1.8 1.8 0 0 1 20 10.1v6a1.8 1.8 0 0 1-1.8 1.8H5.9A1.9 1.9 0 0 1 4 16v-5.8Z" />
      <circle cx="15.6" cy="13.6" r="1.15" fill="currentColor" stroke="none" />
    </Svg>
  )
}

export function TrendIcon(props) {
  return (
    <Svg {...props}>
      <path d="M3.8 16.2 9.3 10.7l3.2 3.2 7.2-7.3" />
      <path d="M15.6 6.6h4.1v4.1" />
    </Svg>
  )
}

export function AlertIcon(props) {
  return (
    <Svg {...props}>
      <path d="M12 4.2 21 19.4H3L12 4.2Z" />
      <path d="M12 10.2v4.2" />
      <path d="M12 17.2h.01" />
    </Svg>
  )
}

export function PulseIcon(props) {
  return (
    <Svg {...props}>
      <path d="M3.5 12h4l2.2-5.2 4 10.4L16 12h4.5" />
    </Svg>
  )
}

export function FlareIcon(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3.6v2.2M12 18.2v2.2M3.6 12h2.2M18.2 12h2.2M6 6l1.6 1.6M16.4 16.4 18 18M18 6l-1.6 1.6M7.6 16.4 6 18" />
    </Svg>
  )
}

const navIcons = {
  '/': HomeIcon,
  '/artist': CompassIcon,
  '/generate': SparkIcon,
  '/users': UsersIcon,
}

export function NavIcon({ to, ...props }) {
  const Icon = navIcons[to] || HomeIcon
  return <Icon {...props} />
}

export function MetricIcon({ label = '', ...props }) {
  const text = String(label)
  let Icon = TrendIcon
  if (/风险|告警|待办|任务/.test(text)) Icon = AlertIcon
  else if (/售票|人数|观演|预约|覆盖|成员/.test(text)) Icon = UsersIcon
  else if (/票房|收入|利润|ROI|消耗|预算|资金|消费/.test(text)) Icon = WalletIcon
  else if (/项目|合作|热度|排名/.test(text)) Icon = FolderIcon
  else if (/票/.test(text)) Icon = TicketIcon
  return <Icon {...props} />
}

export function BrandGlyph({ size = 20 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M8 6.4v11.2c0 1.1 1.2 1.8 2.2 1.2l8.8-5.3c.9-.5.9-1.9 0-2.4l-8.8-5.3C9.2 5.2 8 5.9 8 7v-.6Z"
        fill="#1a1405"
      />
      <path d="M5 8.4v7.2" stroke="#1a1405" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}

export function BrandMark({ className = 'brand-mark' }) {
  return (
    <span className={className} aria-hidden="true">
      <BrandGlyph />
    </span>
  )
}
