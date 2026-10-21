// Single-weight line icon system (1.7 stroke, round caps).
// 图标造型对齐参考设计板：首页 / 项目 / 作品库 / 团队 / 消息 / 设置、
// KPI 场记板与对勾方框、搜索 / 铃铛 / 新建，以及 X 形品牌标。
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

// 品牌 X 标（参考板左上角方形场记板 X）
export function XLogoIcon(props) {
  return (
    <Svg {...props}>
      <rect x="3.5" y="3.5" width="17" height="17" rx="4.5" />
      <path d="m8.8 8.8 6.4 6.4M15.2 8.8l-6.4 6.4" />
    </Svg>
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

// 作品库：2×2 九宫格
export function GridIcon(props) {
  return (
    <Svg {...props}>
      <rect x="3.8" y="3.8" width="6.8" height="6.8" rx="1.8" />
      <rect x="13.4" y="3.8" width="6.8" height="6.8" rx="1.8" />
      <rect x="3.8" y="13.4" width="6.8" height="6.8" rx="1.8" />
      <rect x="13.4" y="13.4" width="6.8" height="6.8" rx="1.8" />
    </Svg>
  )
}

// 消息气泡
export function ChatIcon(props) {
  return (
    <Svg {...props}>
      <path d="M4.5 5.3A1.8 1.8 0 0 1 6.3 3.5h11.4a1.8 1.8 0 0 1 1.8 1.8v8.4a1.8 1.8 0 0 1-1.8 1.8H9.4l-4.2 3.3v-3.3H6.3a1.8 1.8 0 0 1-1.8-1.8V5.3Z" />
      <path d="M8.2 9.4h.01M12 9.4h.01M15.8 9.4h.01" />
    </Svg>
  )
}

// 设置齿轮
export function GearIcon(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="3.1" />
      <path d="M12 2.8v2.4M12 18.8v2.4M21.2 12h-2.4M5.2 12H2.8M18.5 5.5l-1.7 1.7M7.2 16.8l-1.7 1.7M18.5 18.5l-1.7-1.7M7.2 7.2 5.5 5.5" />
    </Svg>
  )
}

export function SearchIcon(props) {
  return (
    <Svg {...props}>
      <circle cx="10.8" cy="10.8" r="6.3" />
      <path d="m15.6 15.6 4.1 4.1" />
    </Svg>
  )
}

export function BellIcon(props) {
  return (
    <Svg {...props}>
      <path d="M6.2 9.6a5.8 5.8 0 0 1 11.6 0c0 4.1 1.4 5.2 1.9 5.8H4.3c.5-.6 1.9-1.7 1.9-5.8Z" />
      <path d="M9.8 18.6a2.4 2.4 0 0 0 4.4 0" />
    </Svg>
  )
}

export function PlusIcon(props) {
  return (
    <Svg {...props}>
      <path d="M12 5.5v13M5.5 12h13" />
    </Svg>
  )
}

// 场记板（项目总数 KPI）
export function ClapperIcon(props) {
  return (
    <Svg {...props}>
      <path d="M4.2 8.2h16.3l-2.4-3.4a1.2 1.2 0 0 0-1.6-.4L4.6 9.6" />
      <path d="M4 9.2h16a.5.5 0 0 1 .5.5v8.3a1.5 1.5 0 0 1-1.5 1.5H5a1.5 1.5 0 0 1-1.5-1.5V9.7a.5.5 0 0 1 .5-.5Z" />
      <path d="m7.2 6.2 3.1 1.8M12.6 4.9l3.1 1.8" />
    </Svg>
  )
}

// 对勾方框（待办事项 KPI）
export function CheckSquareIcon(props) {
  return (
    <Svg {...props}>
      <rect x="4" y="4" width="16" height="16" rx="2.6" />
      <path d="m8.2 12.2 2.6 2.6 5-5.4" />
    </Svg>
  )
}

// 剪贴板对勾（小程序「工作」tab）
export function ClipboardCheckIcon(props) {
  return (
    <Svg {...props}>
      <rect x="5.2" y="4.8" width="13.6" height="16" rx="2.2" />
      <path d="M9.2 4.8h5.6v2.1a1 1 0 0 1-1 1h-3.6a1 1 0 0 1-1-1V4.8Z" />
      <path d="m8.6 13.4 2.3 2.3 4.3-4.6" />
    </Svg>
  )
}

export function InfoIcon(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="8.6" />
      <path d="M12 11v5" />
      <path d="M12 7.6h.01" />
    </Svg>
  )
}

export function FileIcon(props) {
  return (
    <Svg {...props}>
      <path d="M6 3.8h7.6L19 9.2v9.6a1.4 1.4 0 0 1-1.4 1.4H6a1.4 1.4 0 0 1-1.4-1.4V5.2A1.4 1.4 0 0 1 6 3.8Z" />
      <path d="M13.2 3.8v5.6H19" />
      <path d="M8.6 13.4h6.8M8.6 16.8h6.8" />
    </Svg>
  )
}

export function UserCircleIcon(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="8.6" />
      <circle cx="12" cy="9.8" r="2.7" />
      <path d="M7.4 18.2c.9-2 2.6-3 4.6-3s3.7 1 4.6 3" />
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
  let Icon = ClapperIcon
  if (/风险|告警|待办|任务/.test(text)) Icon = CheckSquareIcon
  else if (/作品|演出|售票|场次|热度|排名|观演|预约/.test(text)) Icon = GridIcon
  else if (/人数|覆盖|成员|团队/.test(text)) Icon = UsersIcon
  else if (/票房|收入|利润|ROI|消耗|预算|资金|消费/.test(text)) Icon = WalletIcon
  else if (/项目|合作/.test(text)) Icon = ClapperIcon
  else if (/票/.test(text)) Icon = TicketIcon
  return <Icon {...props} />
}

export function BrandGlyph({ size = 20 }) {
  return (
    <XLogoIcon
      size={size}
      stroke="#1a1405"
      style={{ display: 'block' }}
    />
  )
}

export function BrandMark({ className = 'brand-mark' }) {
  return (
    <span className={className} aria-hidden="true">
      <BrandGlyph />
    </span>
  )
}
