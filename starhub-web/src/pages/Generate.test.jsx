import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import Generate from './Generate'
import { generateAI } from '../api'

vi.mock('../api', () => ({
  generateAI: vi.fn(),
}))

describe('Generate', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders the generated copy from the API response payload', async () => {
    generateAI.mockResolvedValue({
      data: {
        code: 0,
        data: {
          result: 'Generated copy',
        },
        message: 'ok',
      },
    })

    render(<Generate />)

    await userEvent.click(screen.getByRole('button', { name: /一键生成/ }))

    await waitFor(() => {
      expect(screen.getByText('Generated copy')).toBeInTheDocument()
    })
    expect(screen.queryByText(/"code":0/)).not.toBeInTheDocument()
  })

  it('disables generation while the request is pending', async () => {
    let resolveRequest
    generateAI.mockReturnValue(new Promise((resolve) => {
      resolveRequest = resolve
    }))

    render(<Generate />)

    const button = screen.getByRole('button', { name: /一键生成/ })
    await userEvent.click(button)

    expect(screen.getByRole('button', { name: /AI 生成中/ })).toBeDisabled()

    resolveRequest({ data: { data: { result: 'Done' } } })
    await waitFor(() => expect(screen.getByText('Done')).toBeInTheDocument())
  })
})
