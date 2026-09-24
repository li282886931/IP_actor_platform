import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import UserManagement from './UserManagement'
import { createUser, deleteUser, listUsers, updateUser } from '../api'

vi.mock('../api', () => ({
  createUser: vi.fn(),
  deleteUser: vi.fn(),
  listUsers: vi.fn(),
  updateUser: vi.fn(),
}))

describe('UserManagement', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('links user group cards to the create form without filtering the user list', async () => {
    const user = userEvent.setup()
    listUsers.mockResolvedValue({
      data: {
        data: [
          { id: 1, account: 'b_user', name: '主办方用户', group_code: 'B' },
          { id: 2, account: 'brand_user', name: '品牌用户', group_code: 'Brand' },
          { id: 3, account: 'g_user', name: '文旅用户', group_code: 'G' },
          { id: 4, account: 'c_user', name: '观众用户', group_code: 'C' },
        ],
      },
    })

    render(<UserManagement currentUser={{ account: 'root', group_code: 'root' }} />)

    const groups = screen.getByLabelText('用户组选择')
    expect(within(groups).getByRole('button', { name: /主办方/ })).toBeInTheDocument()
    expect(within(groups).getByRole('button', { name: /品牌方/ })).toBeInTheDocument()
    expect(within(groups).getByRole('button', { name: /政府 \/ 文旅/ })).toBeInTheDocument()
    expect(within(groups).getByRole('button', { name: /观众端/ })).toBeInTheDocument()
    expect(within(groups).queryByText('超级管理员')).not.toBeInTheDocument()
    const createForm = screen.getByRole('button', { name: '添加用户' }).closest('form')
    expect(createForm).toHaveClass('user-create-form')
    expect(createForm).not.toHaveClass('generator-form')

    expect(await screen.findByText('b_user')).toBeInTheDocument()
    expect(screen.getByText('brand_user')).toBeInTheDocument()
    expect(screen.getByText('g_user')).toBeInTheDocument()
    expect(screen.getByText('c_user')).toBeInTheDocument()
    expect(screen.getByLabelText('用户组')).toHaveTextContent('主办方')
    expect(screen.queryByRole('combobox', { name: '用户组' })).not.toBeInTheDocument()

    await user.click(within(groups).getByRole('button', { name: /品牌方/ }))

    expect(screen.getByLabelText('用户组')).toHaveTextContent('品牌方')
    expect(screen.getByText('b_user')).toBeInTheDocument()
    expect(screen.getByText('brand_user')).toBeInTheDocument()
    expect(screen.getByText('g_user')).toBeInTheDocument()
    expect(screen.getByText('c_user')).toBeInTheDocument()
  })

  it('creates and deletes users in the selected fixed user group', async () => {
    const user = userEvent.setup()
    listUsers.mockResolvedValue({ data: { data: [] } })
    createUser.mockResolvedValue({
      data: {
        data: { id: 5, account: 'brand_new', name: '新品牌用户', group_code: 'Brand' },
      },
    })
    deleteUser.mockResolvedValue({ data: { data: { deleted: true } } })

    render(<UserManagement currentUser={{ account: 'root', group_code: 'root' }} />)

    await user.click(screen.getByRole('button', { name: /品牌方/ }))
    await user.type(screen.getByLabelText('用户账号'), 'brand_new')
    await user.type(screen.getByLabelText('用户姓名'), '新品牌用户')
    await user.type(screen.getByLabelText('初始密码'), '123456')
    await user.click(screen.getByRole('button', { name: '添加用户' }))

    await waitFor(() => {
      expect(createUser).toHaveBeenCalledWith({
        account: 'brand_new',
        name: '新品牌用户',
        password: '123456',
        group_code: 'Brand',
      })
    })
    expect(await screen.findByText('brand_new')).toBeInTheDocument()

    expect(screen.queryByRole('button', { name: '删除 brand_new' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '删除' }))
    expect(deleteUser).toHaveBeenCalledWith(5)
  })

  it('updates user name password and group from the user list', async () => {
    const user = userEvent.setup()
    listUsers.mockResolvedValue({
      data: {
        data: [
          { id: 6, account: 'brand_edit', name: '品牌用户', group_code: 'Brand' },
        ],
      },
    })
    updateUser.mockResolvedValue({
      data: {
        data: { id: 6, account: 'brand_edit', name: '文旅用户', group_code: 'G' },
      },
    })

    render(<UserManagement currentUser={{ account: 'root', group_code: 'root' }} />)

    expect(await screen.findByText('brand_edit')).toBeInTheDocument()

    expect(screen.queryByRole('button', { name: '修改 brand_edit' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '修改' }))
    await user.clear(screen.getByLabelText('编辑用户姓名'))
    await user.type(screen.getByLabelText('编辑用户姓名'), '文旅用户')
    await user.type(screen.getByLabelText('新密码'), 'newpass123')
    await user.selectOptions(screen.getByLabelText('编辑用户组'), 'G')
    await user.click(screen.getByRole('button', { name: '保存修改' }))

    await waitFor(() => {
      expect(updateUser).toHaveBeenCalledWith(6, {
        name: '文旅用户',
        password: 'newpass123',
        group_code: 'G',
      })
    })
    expect(await screen.findByText('文旅用户')).toBeInTheDocument()
  })
})
