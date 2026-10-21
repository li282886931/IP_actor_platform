// 首字母头像：系统暂无用户照片字段，使用姓名首字 + 按名字稳定哈希的配色。
// 同一用户在任何页面颜色一致；金色底使用墨色字保证对比度。
const PALETTE = [
  { bg: '#d4af37', fg: '#1a1405' }, // 鎏金
  { bg: '#5cc793', fg: '#0c1712' }, // 绿
  { bg: '#e2ab57', fg: '#1a1206' }, // 琥珀
  { bg: '#58b6c9', fg: '#08151a' }, // 青
  { bg: '#9a86d6', fg: '#140f24' }, // 紫
  { bg: '#d9806f', fg: '#241008' }, // 陶红
]

export function hashName(name = '') {
  const text = String(name)
  let hash = 0
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash * 31 + text.charCodeAt(i)) >>> 0
  }
  return hash
}

export function avatarColor(name = '') {
  return PALETTE[hashName(name) % PALETTE.length]
}

export function initialsOf(name = '') {
  const text = String(name).trim()
  if (!text) return '?'
  // 中文取末位名（如「张三」→ 三），英文取首字母
  const firstChar = text.charAt(0)
  if (/[\u4e00-\u9fa5]/.test(firstChar)) return text.charAt(text.length - 1)
  return firstChar.toUpperCase()
}

export default function Avatar({ name = '', size = 30, className = '' }) {
  const color = avatarColor(name || '?')
  return (
    <span
      className={`avatar ${className}`.trim()}
      style={{
        width: size,
        height: size,
        background: color.bg,
        color: color.fg,
        fontSize: Math.round(size * 0.44),
      }}
      aria-hidden="true"
      title={name || '待分配'}
    >
      {initialsOf(name)}
    </span>
  )
}
