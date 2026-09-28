export const toggleSelection = (values, value) => (
  values.includes(value) ? values.filter((item) => item !== value) : values.concat(value)
)

export const detailUrl = ({ entity_type: entityType, entity_id: entityId }) => (
  `/pages/entity-detail/index?entityType=${encodeURIComponent(entityType)}&entityId=${entityId}`
)

export const runtimeHelperSource = `const toggleSelection = (values, value) => (
  values.includes(value) ? values.filter((item) => item !== value) : values.concat(value)
)

const detailUrl = (entityType, entityId) => (
  '/pages/entity-detail/index?entityType=' + encodeURIComponent(entityType) + '&entityId=' + entityId
)
`
