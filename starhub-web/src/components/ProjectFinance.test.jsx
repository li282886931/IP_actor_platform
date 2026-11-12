import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ProjectFinance from './ProjectFinance'
import { calculateShow } from '../api'

vi.mock('../api', () => ({ calculateShow: vi.fn() }))
afterEach(() => { cleanup(); vi.clearAllMocks() })

const inputs = {
  venue_capacity: 1000, expected_attendance: 800, avg_ticket_price: 100,
  artist_fee: 20000, venue_cost: 10000, marketing_cost: 5000, production_cost: 5000,
  security_cost: 0, travel_cost: 0, accommodation_cost: 0, insurance_cost: 0,
  approval_cost: 0, contingency_cost: 0, tax_fee_rate: 0.06, ticketing_fee_rate: 0.04,
}
const project = { id: 1, current_version: { id: 2, input_snapshot: { show_calculation: inputs } } }

describe('ProjectFinance', () => {
  it('restores rates as percentages and saves actual inputs, including explicit zero', async () => {
    const onSaved = vi.fn()
    calculateShow.mockResolvedValue({ data: { data: { status: 'calculated', version_id: 3 } } })
    render(<ProjectFinance project={project} onSaved={onSaved} />)
    expect(screen.getByLabelText('税费率 / %')).toHaveValue(6)
    expect(screen.getByLabelText('票务服务费率 / %')).toHaveValue(4)
    fireEvent.change(screen.getByLabelText('税费率 / %'), { target: { value: '0' } })
    fireEvent.click(screen.getByRole('button', { name: '保存并计算' }))
    await waitFor(() => expect(calculateShow).toHaveBeenCalledWith(expect.objectContaining({
      project_id: 1, tax_fee_rate: 0, ticketing_fee_rate: 0.04, security_cost: 0,
      available_funds: null,
    })))
    expect(onSaved).toHaveBeenCalled()
  })

  it('keeps missing rates empty, shows backend missing fields and retains input', async () => {
    calculateShow.mockResolvedValue({ data: { data: {
      status: 'pending_input', missing_fields: ['tax_fee_rate', 'ticketing_fee_rate'],
    } } })
    render(<ProjectFinance project={{ id: 1, expected_attendance: 800 }} onSaved={vi.fn()} />)
    expect(screen.getByLabelText('税费率 / %')).toHaveValue(null)
    fireEvent.click(screen.getByRole('button', { name: '保存并计算' }))
    expect(await screen.findByRole('status')).toHaveTextContent('待补齐：税费率、票务服务费率')
    expect(screen.getByLabelText('预计人数 / 人')).toHaveValue(800)
  })

  it('retains inputs and enables retry after failure', async () => {
    calculateShow.mockRejectedValue({ response: { status: 422 } })
    render(<ProjectFinance project={project} onSaved={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: '保存并计算' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('参数不符合要求')
    expect(screen.getByRole('button', { name: '保存并计算' })).toBeEnabled()
    expect(screen.getByLabelText('预计人数 / 人')).toHaveValue(800)
  })

  it('shows zero values and capacity warning from saved results without inventing funds', () => {
    render(<ProjectFinance project={{ ...project, current_version: {
      ...project.current_version, finance_result: {
        status: 'calculated', net_profit: 0, roi: 0, funding_gap: null,
        breakeven_attendance: 1100, breakeven_capacity_feasible: false,
        expected_occupancy_rate: 0.8,
      },
    } }} onSaved={vi.fn()} />)
    expect(screen.getByText('保本人数超过场馆容量，请调整成本、票价或收入方案。')).toBeInTheDocument()
    expect(screen.getByText('资金余额待补齐，暂不能计算资金缺口。')).toBeInTheDocument()
    expect(screen.getByText('0.00%')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('上座率调节 / %'), { target: { value: '50' } })
    expect(screen.getByLabelText('预计人数 / 人')).toHaveValue(500)
  })
})
