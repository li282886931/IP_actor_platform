import { expect, it } from 'vitest'
import { canAccessRoute, navigationByRole, roleFromUser } from './roleConfig'

it('limits root to account creation and rejects business deep links', () => {
  expect(navigationByRole.Admin.map(i => i.to)).toEqual(['/users'])
  for (const path of ['/', '/admin/data', '/collaboration', '/preferences', '/artist',
    '/generate', '/operations/projects', '/projects/1', '/show/1']) {
    expect(canAccessRoute('Admin', path)).toBe(false)
  }
})

it('derives the role from the actual account and recognizes all seven roles', () => {
  expect(roleFromUser({ group_code: 'root', role: 'C' })).toBe('Admin')
  for (const role of ['B', 'Brand', 'G', 'C', 'Investor', 'Artist']) expect(roleFromUser({ group_code: role })).toBe(role)
})
it('only grants dedicated routes to the role that owns them', () => {
  for (const [role, items] of Object.entries(navigationByRole)) {
    for (const item of items) expect(canAccessRoute(role, item.to)).toBe(true)
  }
  for (const role of ['C', 'Brand', 'G', 'Investor', 'Artist']) {
    expect(canAccessRoute(role, '/projects/1')).toBe(false)
    expect(canAccessRoute(role, '/operations/projects')).toBe(false)
    expect(canAccessRoute(role, '/users')).toBe(false)
  }
  expect(canAccessRoute('Brand', '/city/review')).toBe(false)
  expect(canAccessRoute('C', '/generate')).toBe(false)
  expect(canAccessRoute('Artist', '/artist')).toBe(false)
})
