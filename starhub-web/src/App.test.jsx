import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { BrowserRouter } from 'react-router-dom'

import App from './App'
import { webLogin } from './api'

vi.mock('./api', () => ({
  createProject: vi.fn(),
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
    expect(screen.getByRole('link', { name: '工作台' })).toBeInTheDocument()
    expect(screen.queryByText(/Demo|MVP/i)).not.toBeInTheDocument()
    expect(document.querySelector('.showcase')).not.toBeInTheDocument()
    expect(document.querySelector('.phone-frame')).not.toBeInTheDocument()
  })

  it('updates navigation when the active role changes', async () => {
    const user = userEvent.setup()
    render(
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <App />
      </BrowserRouter>,
    )

    await user.selectOptions(screen.getByLabelText('当前角色'), 'Brand')

    expect(screen.getByRole('link', { name: '品牌概览' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'AI 品宣' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: '工作台' })).not.toBeInTheDocument()
  })

  it('authenticates through the shared backend before entering the workbench', async () => {
    localStorage.clear()
    webLogin.mockResolvedValue({
      data: {
        data: {
          token: 'dev-token-1-1',
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
    await user.click(screen.getByRole('button', { name: /登录/ }))

    expect(webLogin).toHaveBeenCalledWith({
      account: 'operator@ruiyinchang.com',
      name: 'operator@ruiyinchang.com',
    })
    expect(await screen.findByRole('navigation', { name: '主导航' })).toBeInTheDocument()
    expect(localStorage.getItem('starhub-token')).toBe('dev-token-1-1')
  })
})
