import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import ShowDetail from './ShowDetail'
import { mockOrder } from '../api'
vi.mock('../api', () => ({
  getShow: vi.fn(async () => ({ data: { data: { id: 1, title: '真实演出', city: '上海', venue: '剧院', date: '待定', price: '', status: 'on_sale' } } })),
  mockOrder: vi.fn(async () => ({ data: { data: { order_id: 1 } } })),
}))
afterEach(() => { cleanup(); vi.clearAllMocks() })
const mount = role => render(<MemoryRouter initialEntries={['/show/1']}><Routes><Route path="/show/:id" element={<ShowDetail role={role} />} /></Routes></MemoryRouter>)
it('registers interest and makes the reservation boundary explicit', async () => {
  mount('C')
  await screen.findByText('真实演出')
  await userEvent.type(screen.getByLabelText('姓名'), '观众')
  await userEvent.type(screen.getByLabelText('手机号'), '13800000000')
  await userEvent.click(screen.getByRole('button', { name: '立即预约' }))
  expect(await screen.findByText(/预约登记成功/)).toBeInTheDocument()
  expect(mockOrder).toHaveBeenCalledWith('1', { name: '观众', phone: '13800000000' })
  expect(screen.queryByText(/通过手机号同步/)).not.toBeInTheDocument()
})
it('uses real show fields without inventing project risk or material counts', async () => {
  mount('Investor')
  await screen.findByText('真实演出')
  expect(screen.queryByText('6 项')).not.toBeInTheDocument()
  expect(screen.queryByText('风险等级')).not.toBeInTheDocument()
  expect(screen.queryByRole('link', { name: '生成宣发内容' })).not.toBeInTheDocument()
})
