import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { screenDataMap } from '@/data/screenDataMap'
import { api, ApiError } from '@/services/api'
import type { DisplayItem, MiniappScreenContext, MiniappScreenData } from '@/types/domain'
import { statusLabel } from '@/utils/status'

type LoadState = 'idle' | 'loading' | 'success' | 'empty' | 'error'

interface UseMiniappScreenDataOptions {
  screenId: string
  context: MiniappScreenContext
  onRedirect?: (screenId: string) => void
  onLoaded?: (data: MiniappScreenData) => void
  fetchScreen?: (screenId: string, context: MiniappScreenContext) => Promise<MiniappScreenData>
}

const normalizeItems = (data: MiniappScreenData): DisplayItem[] => data.items.map((item) => ({
  id: item.id,
  title: item.title,
  description: item.description || '',
  status: statusLabel(item.status || ''),
  value: item.value || '',
  details: item.details || '',
  context: item.context,
  detailRef: item.detail_ref,
}))

export function useMiniappScreenData({
  screenId,
  context,
  onRedirect,
  onLoaded,
  fetchScreen = api.getMiniappScreen,
}: UseMiniappScreenDataOptions) {
  const [data, setData] = useState<MiniappScreenData | null>(null)
  const [items, setItems] = useState<DisplayItem[]>([])
  const [state, setState] = useState<LoadState>('idle')
  const [message, setMessage] = useState('')
  const contextKey = JSON.stringify(context)
  const onRedirectRef = useRef(onRedirect)
  const onLoadedRef = useRef(onLoaded)

  useEffect(() => {
    onRedirectRef.current = onRedirect
    onLoadedRef.current = onLoaded
  }, [onLoaded, onRedirect])

  const requestContext = useMemo(() => {
    const required = screenDataMap[screenId]?.requiredContext || []
    return Object.fromEntries(
      Object.entries(context).filter(([key, value]) => required.includes(key as never) && value !== undefined && value !== 0 && value !== ''),
    ) as MiniappScreenContext
  }, [contextKey, screenId])

  const load = useCallback(async () => {
    setItems([])
    setData(null)
    setMessage('')
    setState('loading')
    try {
      const response = await fetchScreen(screenId, requestContext)
      setData(response)
      setItems(normalizeItems(response))
      setState(response.items.length ? 'success' : 'empty')
      onLoadedRef.current?.(response)
    } catch (error) {
      const statusCode = error instanceof ApiError
        ? error.statusCode
        : Number((error as { statusCode?: number })?.statusCode || 0)
      const redirectTarget = statusCode === 401 ? 'S81' : statusCode === 403 ? 'S77' : statusCode === 409 ? 'S78' : ''
      if (redirectTarget && redirectTarget !== screenId) {
        onRedirectRef.current?.(redirectTarget)
        return
      }
      setState('error')
      setMessage(statusCode === 422
        ? '缺少打开当前页面所需的项目、版本或任务信息。'
        : '页面数据加载失败，请重试。')
    }
  }, [fetchScreen, requestContext, screenId])

  useEffect(() => {
    void load()
  }, [screenId])

  return {
    data,
    items,
    state,
    message,
    reload: load,
    setState,
    setMessage,
  }
}
