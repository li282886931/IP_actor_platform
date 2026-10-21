import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import Avatar, { avatarColor, hashName, initialsOf } from './Avatar'

describe('Avatar', () => {
  it('uses the last Chinese name character and falls back for empty names', () => {
    expect(initialsOf('张三')).toBe('三')
    expect(initialsOf('李尔康')).toBe('康')
    expect(initialsOf('alice')).toBe('A')
    expect(initialsOf('')).toBe('?')
    expect(initialsOf('  ')).toBe('?')
  })

  it('keeps the same color for the same name', () => {
    expect(avatarColor('张三')).toEqual(avatarColor('张三'))
    expect(hashName('a')).toBe(hashName('a'))
  })

  it('renders an inline styled circle with stable size', () => {
    const { rerender } = render(<Avatar name="张三" size={34} />)
    const avatar = screen.getByTitle('张三')
    expect(avatar).toHaveTextContent('三')
    expect(avatar).toHaveClass('avatar')
    expect(avatar.style.width).toBe('34px')
    expect(avatar.style.height).toBe('34px')
    expect(avatar.style.background).toMatch(/^rgb/)

    rerender(<Avatar name="" size={22} />)
    expect(screen.getByTitle('待分配')).toHaveTextContent('?')
  })
})
