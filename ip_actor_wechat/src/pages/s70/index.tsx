import { View } from '@tarojs/components'

import BlueprintScreen from '@/components/BlueprintScreen'
import styles from './index.module.scss'

export default function S70Page() {
  return (
    <View className={styles.page}>
      <BlueprintScreen screenId='S70' />
    </View>
  )
}
