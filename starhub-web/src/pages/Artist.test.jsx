import { cleanup, render, screen, waitFor } from '@testing-library/react'
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

  it('shows fuzzy artist suggestions and selects one from the dropdown', async () => {
    searchArtist.mockResolvedValue({
      data: {
        data: [
          { id: 1, name: '周杰伦', tags: '华语流行', heat_score: 96, fan_count: '9000万', risk_level: 1 },
          { id: 2, name: '周深', tags: 'OST', heat_score: 88, fan_count: '3000万', risk_level: 1 },
        ],
      },
    })
    const user = userEvent.setup()

    render(<Artist />)

    await user.type(screen.getByPlaceholderText(/周杰伦/), '周')

    expect(await screen.findByRole('listbox', { name: '艺人搜索建议' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '选择 周杰伦' }))

    await waitFor(() => {
      expect(screen.getByDisplayValue('周杰伦')).toBeInTheDocument()
    })
    expect(screen.getByText('华语流行')).toBeInTheDocument()
    expect(screen.queryByRole('listbox', { name: '艺人搜索建议' })).not.toBeInTheDocument()
  })
})
