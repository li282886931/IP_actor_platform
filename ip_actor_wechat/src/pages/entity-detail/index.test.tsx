import React from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { MiniappEntityDetail } from '@/types/domain'

const mocks = vi.hoisted(() => ({
  getDetail: vi.fn(),
  navigateBack: vi.fn(),
  navigateTo: vi.fn(),
  params: {
    entityType: 'show',
    entityId: '3',
  },
}))

vi.mock('@tarojs/components', () => ({
  Button: ({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) => <button {...props}>{children}</button>,
  Image: ({ src }: React.ImgHTMLAttributes<HTMLImageElement>) => <img src={src} />,
  ScrollView: ({ children }: React.HTMLAttributes<HTMLDivElement>) => <div>{children}</div>,
  Text: ({ children, ...props }: React.HTMLAttributes<HTMLSpanElement>) => <span {...props}>{children}</span>,
  View: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => <div {...props}>{children}</div>,
}))

vi.mock('@tarojs/taro', () => ({
  default: {
    navigateBack: mocks.navigateBack,
    navigateTo: mocks.navigateTo,
  },
  useRouter: () => ({ params: mocks.params }),
}))

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api')
  return {
    ...actual,
    api: {
      ...actual.api,
      getMiniappEntityDetail: mocks.getDetail,
    },
  }
})

import EntityDetailPage from './index'

const detail: MiniappEntityDetail = {
  entity_type: 'show',
  entity_id: 3,
  title: '林俊杰小巨蛋特别场',
  subtitle: '林俊杰 · 台北 · 2026-10-05',
  status: 'on_sale',
  media_url: 'https://assets.example.com/show.jpg',
  fields: [
    { key: 'venue', label: '场馆', value: '台北小巨蛋' },
    { key: 'price', label: '票价', value: '420-980' },
  ],
  sections: [
    { key: 'description', title: '演出介绍', content: '林俊杰抒情特别场' },
  ],
  related_items: [{
    title: '林俊杰',
    subtitle: '关联艺人',
    detail_ref: { entity_type: 'artist', entity_id: 3 },
  }],
  actions: [],
}

describe('EntityDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.params = { entityType: 'show', entityId: '3' }
  })

  it('renders media, localized status, fields, sections and related records', async () => {
    mocks.getDetail.mockResolvedValue(detail)

    render(<EntityDetailPage />)

    expect(await screen.findByText('林俊杰小巨蛋特别场')).toBeInTheDocument()
    expect(screen.getByText('售票中')).toBeInTheDocument()
    expect(screen.getByRole('img')).toHaveAttribute('src', detail.media_url)
    expect(screen.getByText('台北小巨蛋')).toBeInTheDocument()
    expect(screen.getByText('林俊杰抒情特别场')).toBeInTheDocument()

    fireEvent.click(screen.getByText('林俊杰'))
    expect(mocks.navigateTo).toHaveBeenCalledWith({
      url: '/pages/entity-detail/index?entityType=artist&entityId=3',
    })
  })

  it('shows a specific missing detail state and retries', async () => {
    mocks.getDetail
      .mockRejectedValueOnce({ statusCode: 404 })
      .mockResolvedValueOnce(detail)

    render(<EntityDetailPage />)

    expect(await screen.findByText('详情不存在或无权查看')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '重新加载' }))
    expect(await screen.findByText('林俊杰小巨蛋特别场')).toBeInTheDocument()
    expect(mocks.getDetail).toHaveBeenCalledTimes(2)
  })
})
