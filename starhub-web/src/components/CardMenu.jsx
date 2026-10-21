import { useEffect, useRef, useState } from 'react'

// 参考图交互 ④：项目卡片右上角“…”展开更多操作。
// 仅承载真实可用动作（查看详情、分享报告），不提供没有后端支撑的编辑/复制/删除。
export default function CardMenu({ ariaLabel = '更多操作', children, align = 'right' }) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    const handlePointerDown = (event) => {
      if (rootRef.current && !rootRef.current.contains(event.target)) setOpen(false)
    }
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('touchstart', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('touchstart', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open])

  return (
    <div className={`card-menu${open ? ' open' : ''} ${align === 'left' ? 'align-left' : ''}`} ref={rootRef}>
      <button
        type="button"
        className="card-menu-trigger"
        aria-label={ariaLabel}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={(event) => {
          event.preventDefault()
          event.stopPropagation()
          setOpen((current) => !current)
        }}
      >
        ⋯
      </button>
      {open && (
        <div className="card-menu-popover" role="menu" onClick={(event) => event.stopPropagation()}>
          {children?.({ close: () => setOpen(false) })}
        </div>
      )}
    </div>
  )
}
