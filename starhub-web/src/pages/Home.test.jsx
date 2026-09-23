import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import Home from './Home'
import { listShows } from '../api'

vi.mock('../api', () => ({
  listShows: vi.fn(),
}))

describe('Home', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('shows a visible error when show data cannot be loaded', async () => {
    listShows.mockRejectedValue(new Error('offline'))

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Home role="C" />
      </MemoryRouter>,
    )

    expect(await screen.findByText('演出数据暂时不可用')).toBeInTheDocument()
  })
})
