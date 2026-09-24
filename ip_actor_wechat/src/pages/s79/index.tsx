import { View } from '@tarojs/components'

import BlueprintScreen from '@/components/BlueprintScreen'
import styles from './index.module.scss'

export default function S79Page() {
  return (
    <View className={styles.page}>
      <BlueprintScreen screenId='S79' />
    </View>
  )
}
