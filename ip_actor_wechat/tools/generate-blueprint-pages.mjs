import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { routeFor, screens, tabScreens } from './blueprint-manifest.mjs'

const root = resolve(import.meta.dirname, '..')

const escapeText = (value) => value.replaceAll('\\', '\\\\').replaceAll("'", "\\'")

const screenSource = `export interface ScreenDefinition {
  id: string
  title: string
  subtitle: string
  group: string
  primaryAction: string
  highlight: string
}

export const screenDefinitions: Record<string, ScreenDefinition> = {
${screens.map(([id, title, subtitle, group, primaryAction, highlight]) => `  ${id}: {
    id: '${id}',
    title: '${escapeText(title)}',
    subtitle: '${escapeText(subtitle)}',
    group: '${escapeText(group)}',
    primaryAction: '${escapeText(primaryAction)}',
    highlight: '${escapeText(highlight)}',
  },`).join('\n')}
}
`

mkdirSync(resolve(root, 'src/data'), { recursive: true })
writeFileSync(resolve(root, 'src/data/screens.ts'), screenSource)

for (const [id, title] of screens) {
  const slug = id.toLowerCase()
  const componentName = `${id}Page`
  const pageDir = resolve(root, `src/pages/${slug}`)
  mkdirSync(pageDir, { recursive: true })
  writeFileSync(resolve(pageDir, 'index.config.ts'), `export default definePageConfig({
  navigationBarTitleText: '${escapeText(title)}',
})
`)
  writeFileSync(resolve(pageDir, 'index.module.scss'), `@use '@/styles/variables.scss' as *;

.page {
  min-height: 100vh;
}
`)
  writeFileSync(resolve(pageDir, 'index.tsx'), `import { View } from '@tarojs/components'

import BlueprintScreen from '@/components/BlueprintScreen'
import styles from './index.module.scss'

export default function ${componentName}() {
  return (
    <View className={styles.page}>
      <BlueprintScreen screenId='${id}' />
    </View>
  )
}
`)
}

const allRoutes = screens.map(([id]) => `    '${routeFor(id).slice(1)}',`).join('\n')
const tabItems = [
  ['S04', '发现', 'discover'],
  ['S10', '项目', 'project'],
  ['S52', 'Agent', 'agent'],
  ['S67', '我的', 'profile'],
].map(([id, text, icon]) => `      {
        pagePath: '${routeFor(id).slice(1)}',
        text: '${text}',
        iconPath: 'assets/tabbar/${icon}.svg',
        selectedIconPath: 'assets/tabbar/${icon}-selected.svg',
      },`).join('\n')

writeFileSync(resolve(root, 'src/app.config.ts'), `export default defineAppConfig({
  pages: [
${allRoutes}
  ],
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#ffffff',
    navigationBarTitleText: '锐音场',
    navigationBarTextStyle: 'black',
  },
  tabBar: {
    color: '#86909c',
    selectedColor: '#2864dc',
    backgroundColor: '#ffffff',
    borderStyle: 'white',
    list: [
${tabItems}
    ],
  },
})
`)

const icons = {
  discover: '<circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2.2 4.8-4.8 2.2 2.2-4.8 4.8-2.2Z"/>',
  project: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
  agent: '<path d="M12 3v3M7 5l1.5 2M17 5l-1.5 2"/><rect x="4" y="7" width="16" height="13" rx="4"/><circle cx="9" cy="13" r="1"/><circle cx="15" cy="13" r="1"/><path d="M9 17h6"/>',
  profile: '<circle cx="12" cy="8" r="4"/><path d="M4.5 21c.8-4.2 3.3-6 7.5-6s6.7 1.8 7.5 6"/>',
}

const iconDir = resolve(root, 'src/assets/tabbar')
mkdirSync(iconDir, { recursive: true })
for (const [name, body] of Object.entries(icons)) {
  for (const selected of [false, true]) {
    const color = selected ? '#2864dc' : '#999999'
    const width = selected ? '2' : '1.5'
    const suffix = selected ? '-selected' : ''
    writeFileSync(resolve(iconDir, `${name}${suffix}.svg`), `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round">${body}</svg>
`)
  }
}

console.log(`Generated ${screens.length} screens and ${tabScreens.length} tab pages.`)

