import { useCallback, useEffect, useState } from 'react'
import { Button, Image, ScrollView, Text, View } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'

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
      <View className={styles.topbar}>
        <Button className={styles.backButton} onClick={() => void Taro.navigateBack()}>
          <Text className={styles.backIcon}>‹</Text>
        </Button>
        <Text className={styles.pageTitle}>业务详情</Text>
        <View className={styles.topbarSpacer} />
      </View>

      {state === 'loading' && (
        <View className={styles.statePanel}>
          <View className={styles.loadingBar} />
          <Text className={styles.stateTitle}>正在加载详情</Text>
        </View>
      )}

      {state === 'error' && (
        <View className={styles.statePanel}>
          <Text className={styles.stateTitle}>{message}</Text>
          <Text className={styles.stateDescription}>返回上一页或重新读取最新数据。</Text>
          <View className={styles.stateActions}>
            <Button className={styles.secondaryButton} onClick={() => void Taro.navigateBack()}>返回</Button>
            <Button className={styles.primaryButton} onClick={() => void loadDetail()}>重新加载</Button>
          </View>
        </View>
      )}

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

          <View className={styles.hero}>
            <Text className={styles.entityType}>{detail.entity_type.replace(/_/g, ' ')}</Text>
            <Text className={styles.title}>{detail.title}</Text>
            {detail.subtitle && <Text className={styles.subtitle}>{detail.subtitle}</Text>}
            {detail.status && (
              <Text className={styles.status}>{statusLabel(detail.status)}</Text>
            )}
          </View>

          {detail.fields.length > 0 && (
            <View className={styles.section}>
              <Text className={styles.sectionTitle}>关键信息</Text>
              <View className={styles.fieldGrid}>
                {detail.fields.map((item) => (
                  <View className={styles.field} key={item.key}>
                    <Text className={styles.fieldLabel}>{item.label}</Text>
                    <Text className={styles.fieldValue}>{item.value}</Text>
                  </View>
                ))}
              </View>
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
              <View className={styles.relatedList}>
                {detail.related_items.map((item) => (
                  <View
                    className={styles.relatedItem}
                    key={`${item.detail_ref.entity_type}-${item.detail_ref.entity_id}`}
                    onClick={() => openRelated(item.detail_ref)}
                  >
                    <View className={styles.relatedText}>
                      <Text className={styles.relatedTitle}>{item.title}</Text>
                      {item.subtitle && <Text className={styles.relatedSubtitle}>{item.subtitle}</Text>}
                    </View>
                    <Text className={styles.chevron}>›</Text>
                  </View>
                ))}
              </View>
            </View>
          )}
        </>
      )}
      <View className={styles.safeBottom} />
    </ScrollView>
  )
}
