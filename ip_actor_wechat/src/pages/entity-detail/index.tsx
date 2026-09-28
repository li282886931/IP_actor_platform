import { useCallback, useEffect, useState } from 'react'
import { Image, ScrollView, Text, View } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'

import { BusinessList, KeyValueGrid, ScreenHeader, ScreenHero, ScreenState } from '@/components/ScreenPrimitives'
import { api, ApiError } from '@/services/api'
import type { MiniappEntityDetail, MiniappEntityRef } from '@/types/domain'
import { statusLabel } from '@/utils/status'
import styles from './index.module.scss'

type DetailState = 'loading' | 'success' | 'error'

const detailUrl = (reference: MiniappEntityRef) => (
  `/pages/entity-detail/index?entityType=${encodeURIComponent(reference.entity_type)}&entityId=${reference.entity_id}`
)

export default function EntityDetailPage() {
  const { params } = useRouter()
  const entityType = String(params.entityType || '')
  const entityId = Number(params.entityId || 0)
  const [detail, setDetail] = useState<MiniappEntityDetail | null>(null)
  const [state, setState] = useState<DetailState>('loading')
  const [message, setMessage] = useState('')

  const loadDetail = useCallback(async () => {
    if (!entityType || !entityId) {
      setDetail(null)
      setState('error')
      setMessage('详情参数不完整')
      return
    }
    setState('loading')
    setMessage('')
    try {
      const result = await api.getMiniappEntityDetail(entityType, entityId)
      setDetail(result)
      setState('success')
    } catch (error) {
      console.error('[EntityDetail] load failed', { entityType, entityId, error })
      const statusCode = error instanceof ApiError
        ? error.statusCode
        : Number((error as { statusCode?: number })?.statusCode || 0)
      setDetail(null)
      setState('error')
      setMessage(
        statusCode === 403 || statusCode === 404
          ? '详情不存在或无权查看'
          : '详情加载失败，请重试',
      )
    }
  }, [entityId, entityType])

  useEffect(() => {
    void loadDetail()
  }, [loadDetail])

  const openRelated = (reference: MiniappEntityRef) => {
    void Taro.navigateTo({ url: detailUrl(reference) })
  }

  return (
    <ScrollView className={styles.page} scrollY enhanced showScrollbar={false}>
      <View className={styles.safeTop} />
      <ScreenHeader title='业务详情' onBack={() => void Taro.navigateBack()} />

      {state === 'loading' && <ScreenState state='loading' />}
      {state === 'error' && <ScreenState state='error' message={message} onRetry={() => void loadDetail()} />}

      {state === 'success' && detail && (
        <>
          {detail.media_url && (
            <Image
              className={styles.media}
              src={detail.media_url}
              mode='aspectFill'
              lazyLoad
            />
          )}

          <ScreenHero
            group={detail.entity_type.replace(/_/g, ' ')}
            title={detail.title}
            subtitle={detail.subtitle}
            status={detail.status ? statusLabel(detail.status) : null}
          />

          {detail.fields.length > 0 && (
            <View className={styles.section}>
              <Text className={styles.sectionTitle}>关键信息</Text>
              <KeyValueGrid items={detail.fields.map((item) => ({ label: item.label, value: item.value }))} />
            </View>
          )}

          {detail.sections.map((section) => (
            <View className={styles.section} key={section.key}>
              <Text className={styles.sectionTitle}>{section.title}</Text>
              <Text className={styles.sectionContent}>{section.content}</Text>
            </View>
          ))}

          {detail.related_items.length > 0 && (
            <View className={styles.section}>
              <Text className={styles.sectionTitle}>关联记录</Text>
              <BusinessList
                items={detail.related_items.map((item) => ({
                  id: `${item.detail_ref.entity_type}-${item.detail_ref.entity_id}`,
                  title: item.title,
                  description: item.subtitle || '',
                  status: '',
                  context: {},
                  detailRef: item.detail_ref,
                }))}
                onOpenDetail={(item) => {
                  if (item.detailRef) openRelated(item.detailRef)
                }}
              />
            </View>
          )}
        </>
      )}
      <View className={styles.safeBottom} />
    </ScrollView>
  )
}
