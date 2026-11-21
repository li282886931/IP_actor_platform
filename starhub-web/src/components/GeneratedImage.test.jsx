import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import GeneratedImage from './GeneratedImage'
import { generateAIImage, getAIImage } from '../api'

vi.mock('../api', () => ({ generateAIImage: vi.fn(), getAIImage: vi.fn() }))
const reply = (id = 3, url = 'https://images.example.com/stage.jpg') => ({
  data: { code: 0, data: { id, image_url: url, width: 2560, height: 1440, size: 12345, expires_in_seconds: 3600 } },
})
afterEach(() => { cleanup(); localStorage.clear(); vi.resetAllMocks() })

it('generates, previews and refreshes an OSS link while persisting only its record id', async () => {
  generateAIImage.mockResolvedValue(reply())
  getAIImage.mockResolvedValue(reply(3, 'https://images.example.com/stage.jpg?fresh=1'))
  render(<GeneratedImage storageKey="account-a" />)
  await userEvent.type(screen.getByLabelText('图片创作描述'), '写实蓝色灯光舞台')
  await userEvent.selectOptions(screen.getByLabelText('图片尺寸'), 'landscape_16_9')
  await userEvent.click(screen.getByRole('button', { name: '生成图片' }))
  expect(await screen.findByAltText('宣发创意图片')).toHaveAttribute('src', 'https://images.example.com/stage.jpg')
  expect(generateAIImage).toHaveBeenCalledWith(expect.objectContaining({
    prompt: '写实蓝色灯光舞台', image_size: 'landscape_16_9', generation_nonce: expect.any(String),
  }))
  expect(screen.getByRole('link', { name: '打开原图' })).toHaveAttribute('href', 'https://images.example.com/stage.jpg')
  expect(JSON.parse(localStorage.getItem('account-a:image'))).toEqual({ id: 3 })
  await userEvent.click(screen.getByRole('button', { name: '刷新链接' }))
  await waitFor(() => expect(screen.getByAltText('宣发创意图片')).toHaveAttribute('src', expect.stringContaining('fresh=1')))
  expect(screen.getByText(/2560 × 1440/)).toBeInTheDocument()
})

it('restores a fresh link instead of caching an expired signed URL', async () => {
  localStorage.setItem('account-a:image', JSON.stringify({ id: 8 }))
  getAIImage.mockResolvedValue(reply(8))
  render(<GeneratedImage storageKey="account-a" />)
  expect(await screen.findByAltText('宣发创意图片')).toBeInTheDocument()
  expect(getAIImage).toHaveBeenCalledWith(8)
})

it('preserves the description on failure and rejects non-HTTPS previews', async () => {
  generateAIImage.mockRejectedValue({ response: { data: { detail: '图片上传阿里 OSS 失败' } } })
  render(<GeneratedImage storageKey="account-a" />)
  expect(screen.getByRole('button', { name: '生成图片' })).toBeDisabled()
  await userEvent.type(screen.getByLabelText('图片创作描述'), '舞台')
  await userEvent.click(screen.getByRole('button', { name: '生成图片' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('图片上传阿里 OSS 失败')
  expect(screen.getByLabelText('图片创作描述')).toHaveValue('舞台')
  generateAIImage.mockResolvedValue(reply(1, 'oss://private/image.png'))
  await userEvent.click(screen.getByRole('button', { name: '生成图片' }))
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('未返回可访问的 HTTPS 图片链接'))
  expect(screen.queryByAltText('宣发创意图片')).not.toBeInTheDocument()
})

it('discards late generation responses after account switch', async () => {
  let finish
  generateAIImage.mockImplementation(() => new Promise(resolve => { finish = resolve }))
  const { rerender } = render(<GeneratedImage key="a" storageKey="account-a" />)
  await userEvent.type(screen.getByLabelText('图片创作描述'), '甲的舞台')
  await userEvent.click(screen.getByRole('button', { name: '生成图片' }))
  rerender(<GeneratedImage key="b" storageKey="account-b" />)
  await act(async () => finish(reply()))
  expect(screen.queryByAltText('宣发创意图片')).not.toBeInTheDocument()
  expect(localStorage.getItem('account-b:image')).toBeNull()
})

it('copies the HTTPS URL and presents image load failure without automatic retry loops', async () => {
  generateAIImage.mockResolvedValue(reply())
  const clipboard = { writeText: vi.fn().mockResolvedValue() }
  Object.defineProperty(navigator, 'clipboard', { value: clipboard, configurable: true })
  render(<GeneratedImage storageKey="account-a" />)
  fireEvent.change(screen.getByLabelText('图片创作描述'), { target: { value: '舞台' } })
  fireEvent.click(screen.getByRole('button', { name: '生成图片' }))
  fireEvent.error(await screen.findByAltText('宣发创意图片'))
  expect(screen.getByRole('alert')).toHaveTextContent('图片加载失败')
  fireEvent.click(screen.getByRole('button', { name: '复制链接' }))
  await waitFor(() => expect(clipboard.writeText).toHaveBeenCalledWith('https://images.example.com/stage.jpg'))
  expect(getAIImage).not.toHaveBeenCalled()
})
