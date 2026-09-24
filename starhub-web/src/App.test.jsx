import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { BrowserRouter } from 'react-router-dom'

import App from './App'
import { getAuthCaptcha, webLogin } from './api'

vi.mock('./api', () => ({
  agentChat: vi.fn(),
  createAssumption: vi.fn(),
  createEvidence: vi.fn(),
  createExternalDataJob: vi.fn(),
  createFact: vi.fn(),
  createGate: vi.fn(),
  createProject: vi.fn(),
  createRisk: vi.fn(),
  createUser: vi.fn(),
  deleteUser: vi.fn(),
  getDashboardAnalytics: vi.fn().mockResolvedValue({
    data: {
      data: {
        summary: {
          active_projects: 0,
          pending_tasks: 0,
          reservations: 0,
          on_sale_shows: 0,
          neutral_profit_total: 0,
        },
      },
    },
  }),
  getProject: vi.fn(),
  getShowRecommendations: vi.fn().mockResolvedValue({ data: { data: [] } }),
  getTicketingSummary: vi.fn().mockResolvedValue({
    data: {
      data: {
        summary: {
          total_shows: 0,
          on_sale_shows: 0,
          reservation_count: 0,
        },
        shows: [],
        orders: [],
      },
    },
  }),
  listAssumptions: vi.fn().mockResolvedValue({ data: { data: [] } }),
  listEvidences: vi.fn().mockResolvedValue({ data: { data: [] } }),
  listExternalDataJobs: vi.fn().mockResolvedValue({ data: { data: [] } }),
  listFacts: vi.fn().mockResolvedValue({ data: { data: [] } }),
  listGates: vi.fn().mockResolvedValue({ data: { data: [] } }),
  listProjectVersions: vi.fn().mockResolvedValue({ data: { data: [] } }),
  listRisks: vi.fn().mockResolvedValue({ data: { data: [] } }),
  listUserGroups: vi.fn().mockResolvedValue({ data: { data: [] } }),
  listUsers: vi.fn().mockResolvedValue({ data: { data: [] } }),
  listProjects: vi.fn().mockResolvedValue({ data: { data: [] } }),
  listShows: vi.fn().mockResolvedValue({ data: { data: [] } }),
  listTasks: vi.fn().mockResolvedValue({ data: { data: [] } }),
  searchCases: vi.fn(),
  searchArtist: vi.fn(),
  shareReport: vi.fn(),
  runExternalDataJob: vi.fn(),
  submitTask: vi.fn(),
  generateAI: vi.fn(),
  getAuthCaptcha: vi.fn().mockResolvedValue({
    data: {
      data: {
        captcha_id: 'captcha-1',
        captcha_image: 'data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22/%3E',
        expires_in_seconds: 300,
      },
    },
  }),
  getShow: vi.fn(),
  mockOrder: vi.fn(),
  updateUser: vi.fn(),
  verifyFact: vi.fn(),
  webLogin: vi.fn(),
}))

describe('App workbench shell', () => {
  beforeEach(() => {
    vi.clearAllMocks()
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

  it('registers the platform favicon in the browser tab', () => {
    render(
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <App />
      </BrowserRouter>,
    )

    const favicon = document.head.querySelector('link[rel="icon"]')
    expect(favicon).toBeInTheDocument()
    expect(favicon?.getAttribute('href')).toBe('/favicon.svg')
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

  it('keeps audience users away from the AI generation workspace', async () => {
    localStorage.setItem('starhub-role', 'C')
    localStorage.setItem('starhub-user', JSON.stringify({ account: 'c_user', role: 'C', group_code: 'C', phone: '13800000000' }))
    window.history.pushState({}, '', '/generate')

    render(
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <App />
      </BrowserRouter>,
    )

    expect(screen.getByRole('link', { name: /演出发现/ })).toHaveAttribute('href', '/')
    expect(screen.queryByRole('link', { name: /AI 推荐|AI 宣发/ })).not.toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: '发现值得到场的演出' })).toBeInTheDocument()
    expect(screen.queryByText('AI 宣发内容生成')).not.toBeInTheDocument()
  })

  it('returns to the main workbench when logging in with a non-root account after leaving user management', async () => {
    window.history.pushState({}, '', '/users')
    webLogin.mockResolvedValue({
      data: {
        data: {
          token: 'dev-token-2-1',
          user: { account: 'b_user', name: '主办方用户', role: 'B', group_code: 'B', can_manage_users: false },
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

    expect(await screen.findByText('维护平台账号，并按固定业务用户组管理页面权限。')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '退出' }))
    expect(screen.getByRole('heading', { name: '登录工作台' })).toBeInTheDocument()

    await user.type(screen.getByPlaceholderText('输入邮箱或手机号'), 'b_user')
    await user.type(screen.getByPlaceholderText('输入登录密码'), '123456')
    await user.type(screen.getByPlaceholderText('输入图形验证码'), 'AB12')
    await user.click(screen.getByRole('button', { name: /登录/ }))

    expect(await screen.findByRole('heading', { name: '项目决策工作台' })).toBeInTheDocument()
    expect(screen.queryByText('无权访问用户管理')).not.toBeInTheDocument()
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

    expect(await screen.findByRole('img', { name: '登录验证码' })).toBeInTheDocument()
    await user.type(screen.getByPlaceholderText('输入邮箱或手机号'), 'operator@ruiyinchang.com')
    await user.type(screen.getByPlaceholderText('输入登录密码'), '123456')
    await user.type(screen.getByPlaceholderText('输入图形验证码'), 'AB12')
    await user.click(screen.getByRole('button', { name: /登录/ }))

    expect(webLogin).toHaveBeenCalledWith({
      account: 'operator@ruiyinchang.com',
      password: '123456',
      captcha_id: 'captcha-1',
      captcha_code: 'AB12',
    })
    expect(await screen.findByRole('navigation', { name: '主导航' })).toBeInTheDocument()
    expect(localStorage.getItem('starhub-token')).toBe('dev-token-1-1')
  })

  it('loads and refreshes backend captcha on the login screen', async () => {
    localStorage.clear()
    const user = userEvent.setup()

    render(
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <App />
      </BrowserRouter>,
    )

    expect(await screen.findByRole('img', { name: '登录验证码' })).toBeInTheDocument()
    expect(getAuthCaptcha).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('button', { name: '换一张验证码' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '点击刷新验证码' }))

    expect(getAuthCaptcha).toHaveBeenCalledTimes(2)
  })

  it('refreshes the captcha after logging out to the login screen', async () => {
    const user = userEvent.setup()

    render(
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <App />
      </BrowserRouter>,
    )

    expect(screen.getByRole('button', { name: '退出' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '退出' }))

    expect(await screen.findByRole('img', { name: '登录验证码' })).toBeInTheDocument()
    await waitFor(() => {
      expect(getAuthCaptcha).toHaveBeenCalledTimes(1)
    })
  })

  it('shows the backend captcha error when login verification fails', async () => {
    localStorage.clear()
    webLogin.mockRejectedValue({
      response: {
        data: {
          detail: 'Invalid captcha',
        },
      },
    })
    const user = userEvent.setup()

    render(
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <App />
      </BrowserRouter>,
    )

    expect(await screen.findByRole('img', { name: '登录验证码' })).toBeInTheDocument()
    await user.type(screen.getByPlaceholderText('输入邮箱或手机号'), 'root')
    await user.type(screen.getByPlaceholderText('输入登录密码'), '123456')
    await user.type(screen.getByPlaceholderText('输入图形验证码'), 'AB12')
    await user.click(screen.getByRole('button', { name: /登录/ }))

    expect(await screen.findByText('验证码错误，请重新输入。')).toBeInTheDocument()
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
