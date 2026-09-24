import { View } from '@tarojs/components'

import BlueprintScreen from '@/components/BlueprintScreen'
import styles from './index.module.scss'

export default function S76Page() {
  return (
    <View className={styles.page}>
      <BlueprintScreen screenId='S76' />
    </View>
  )
}
