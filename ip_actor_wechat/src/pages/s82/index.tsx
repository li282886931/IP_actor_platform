import { View } from '@tarojs/components'

import BlueprintScreen from '@/components/BlueprintScreen'
import styles from './index.module.scss'

export default function S82Page() {
  return (
    <View className={styles.page}>
      <BlueprintScreen screenId='S82' />
    </View>
  )
}
