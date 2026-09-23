import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import Artist from './Artist'
import { searchArtist } from '../api'

vi.mock('../api', () => ({
  searchArtist: vi.fn(),
}))

describe('Artist', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('shows a visible error when artist search fails', async () => {
    searchArtist.mockRejectedValue(new Error('offline'))
    const user = userEvent.setup()

    render(<Artist />)

    await user.type(screen.getByPlaceholderText(/周杰伦/), '周杰伦')
    await user.click(screen.getByRole('button', { name: /查询热度/ }))

    expect(await screen.findByText('艺人数据查询失败')).toBeInTheDocument()
  })
})
