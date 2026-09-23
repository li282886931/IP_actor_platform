import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { BrowserRouter } from 'react-router-dom'

import App from './App'
import { webLogin } from './api'

vi.mock('./api', () => ({
  createProject: vi.fn(),
  createUser: vi.fn(),
  deleteUser: vi.fn(),
  listUserGroups: vi.fn().mockResolvedValue({ data: { data: [] } }),
  listUsers: vi.fn().mockResolvedValue({ data: { data: [] } }),
  listProjects: vi.fn().mockResolvedValue({ data: { data: [] } }),
  listShows: vi.fn().mockResolvedValue({ data: { data: [] } }),
  listTasks: vi.fn().mockResolvedValue({ data: { data: [] } }),
  searchArtist: vi.fn(),
  generateAI: vi.fn(),
  getShow: vi.fn(),
  mockOrder: vi.fn(),
  webLogin: vi.fn(),
}))

describe('App workbench shell', () => {
  beforeEach(() => {
    localStorage.setItem('starhub-login', 'true')
    localStorage.setItem('starhub-role', 'B')
    localStorage.setItem('starhub-user', JSON.stringify({ account: 'root', role: 'B', group_code: 'root', can_manage_users: true }))
  })

  afterEach(() => {
    cleanup()
    localStorage.clear()
  })

  it('renders a desktop workbench without the old preview column', async () => {
    render(
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <App />
      </BrowserRouter>,
    )

    expect(screen.getByRole('navigation', { name: '主导航' })).toBeInTheDocument()
    expect(screen.getByText('工作台')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '退出' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '切换账号' })).not.toBeInTheDocument()
    expect(screen.queryByText(/Demo|MVP/i)).not.toBeInTheDocument()
    expect(document.querySelector('.showcase')).not.toBeInTheDocument()
    expect(document.querySelector('.phone-frame')).not.toBeInTheDocument()
  })

  it('keeps sidebar workspace entries clickable after login', async () => {
    render(
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <App />
      </BrowserRouter>,
    )

    expect(screen.getByRole('link', { name: /工作台/ })).toHaveAttribute('href', '/')
    expect(screen.getByRole('link', { name: /艺人智策/ })).toHaveAttribute('href', '/artist')
    expect(screen.getByRole('link', { name: /AI 宣发/ })).toHaveAttribute('href', '/generate')
    expect(screen.getByRole('link', { name: /用户管理/ })).toHaveAttribute('href', '/users')
  })

  it('uses root permissions instead of stale visitor role cache', async () => {
    localStorage.setItem('starhub-role', 'C')
    localStorage.setItem('starhub-user', JSON.stringify({ account: 'root', group_code: 'root' }))

    render(
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <App />
      </BrowserRouter>,
    )

    expect(await screen.findByRole('link', { name: /用户管理/ })).toHaveAttribute('href', '/users')
    expect(screen.getByRole('link', { name: /工作台/ })).toHaveAttribute('href', '/')
    expect(screen.queryByRole('link', { name: /演出发现/ })).not.toBeInTheDocument()
  })

  it('does not show manual role selectors after login', async () => {
    render(
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <App />
      </BrowserRouter>,
    )

    expect(screen.queryByLabelText('当前角色')).not.toBeInTheDocument()
  })

  it('clears readable cookies when logging out', async () => {
    document.cookie = 'session_token=abc123; path=/'
    document.cookie = 'tenant_id=1; path=/'
    const user = userEvent.setup()

    render(
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <App />
      </BrowserRouter>,
    )

    await user.click(screen.getByRole('button', { name: '退出' }))

    expect(document.cookie).not.toContain('session_token=')
    expect(document.cookie).not.toContain('tenant_id=')
  })

  it('authenticates through the shared backend before entering the workbench', async () => {
    localStorage.clear()
    webLogin.mockResolvedValue({
      data: {
        data: {
          token: 'dev-token-1-1',
          user: { account: 'root', role: 'B', group_code: 'root', can_manage_users: true },
          current_tenant: { id: 1, name: '锐音场默认空间' },
        },
      },
    })
    const user = userEvent.setup()

    render(
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <App />
      </BrowserRouter>,
    )

    await user.type(screen.getByPlaceholderText('输入邮箱或手机号'), 'operator@ruiyinchang.com')
    await user.type(screen.getByPlaceholderText('输入登录密码'), '123456')
    await user.click(screen.getByRole('button', { name: /登录/ }))

    expect(webLogin).toHaveBeenCalledWith({
      account: 'operator@ruiyinchang.com',
      password: '123456',
    })
    expect(await screen.findByRole('navigation', { name: '主导航' })).toBeInTheDocument()
    expect(localStorage.getItem('starhub-token')).toBe('dev-token-1-1')
  })

  it('does not expose role selection on the login screen', () => {
    localStorage.clear()

    render(
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <App />
      </BrowserRouter>,
    )

    expect(screen.queryByText('登录角色')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /品牌方/ })).not.toBeInTheDocument()
  })
})
