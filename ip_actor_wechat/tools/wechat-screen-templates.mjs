const projectSearchWxml = `
    <view wx:if="{{candidateGroups.length}}" class="candidate-groups">
      <view wx:for="{{candidateGroups}}" wx:key="key" wx:for-item="group" wx:for-index="groupIndex" class="candidate-group">
        <view class="candidate-group-label">{{group.label}}</view>
        <view class="candidate-list">
          <view wx:for="{{group.items}}" wx:key="key" wx:for-item="candidate" wx:for-index="itemIndex" class="candidate-item" data-group-index="{{groupIndex}}" data-item-index="{{itemIndex}}" bindtap="onCandidateTap">
            <view class="candidate-main">
              <view class="candidate-title">{{candidate.label}}</view>
              <view wx:if="{{candidate.description}}" class="candidate-description">{{candidate.description}}</view>
            </view>
            <view class="candidate-action">选择</view>
          </view>
        </view>
      </view>
    </view>
    <view wx:if="{{candidateSearchOpen}}" class="search-dropdown">
      <view wx:if="{{candidateSearchLoading}}" class="search-state">正在搜索数据库...</view>
      <block wx:elif="{{candidateSearchGroups.length}}">
        <view wx:for="{{candidateSearchGroups}}" wx:key="key" wx:for-item="group" wx:for-index="groupIndex" class="search-group">
          <view class="search-group-label">{{group.label}}</view>
          <view wx:for="{{group.items}}" wx:key="key" wx:for-item="candidate" wx:for-index="itemIndex" class="search-suggestion" data-group-index="{{groupIndex}}" data-item-index="{{itemIndex}}" bindtap="onCandidateSearchTap">
            <view class="search-suggestion-main">
              <view class="search-suggestion-title">{{candidate.label}}</view>
              <view class="search-suggestion-description">{{candidate.description}}</view>
            </view>
            <view class="search-suggestion-action">选择</view>
          </view>
        </view>
      </block>
      <view wx:else class="search-state">未找到匹配数据</view>
    </view>`

const businessItemsWxml = `<view wx:for="{{items}}" wx:key="id" class="item" data-entity-type="{{item.detailRef.entity_type}}" data-entity-id="{{item.detailRef.entity_id}}" bindtap="onBusinessItemTap">
      <view class="item-main">
        <view class="item-title">{{item.title}}</view>
        <view class="item-desc">{{item.description}}</view>
      </view>
      <view class="badge">{{item.status}}</view>
      <view wx:if="{{item.detailRef}}" class="detail-chevron">›</view>
    </view>`

const taskItemsWxml = `<view class="task-selection">已选择 {{selectedTaskIds.length}} 项任务</view>
    <view wx:for="{{items}}" wx:key="id" class="item task-item">
      <view class="task-checkbox {{item.selected ? 'selected' : ''}}" data-id="{{item.entityId}}" catchtap="onTaskCheck">{{item.selected ? '✓' : ''}}</view>
      <view class="item-main" data-id="{{item.entityId}}" bindtap="onTaskToggleDetail">
        <view class="item-title">{{item.title}}</view>
        <view class="item-desc {{item.expanded ? 'expanded' : ''}}">{{item.description}}</view>
        <view wx:if="{{item.expanded}}" class="task-details">{{item.details || '暂无更多任务信息'}}</view>
      </view>
      <view class="badge">{{item.status}}</view>
      <view wx:if="{{item.detailRef}}" class="detail-chevron" data-entity-type="{{item.detailRef.entity_type}}" data-entity-id="{{item.detailRef.entity_id}}" catchtap="onBusinessItemTap">›</view>
    </view>`

const planItemsWxml = `<view wx:for="{{items}}" wx:key="id" class="item">
      <view class="item-main">
        <view class="item-title">{{item.title}}</view>
        <view class="item-desc">{{item.description}}</view>
        <view wx:if="{{item.context.actionability.length}}" class="item-desc">可处理：{{item.context.actionability.join(' · ')}}</view>
        <view wx:if="{{item.context.evidence_required}}" class="item-desc">需补证据</view>
      </view>
      <view class="badge">{{item.status}}</view>
    </view>`

const defaultActionsWxml = `<block wx:if="{{screen.id === 'S01'}}">
    <button class="primary" open-type="getPhoneNumber" bindgetphonenumber="onGetPhoneNumber">{{screen.primaryAction}}</button>
  </block>
  <block wx:else>
    <button class="primary" bindtap="onPrimaryTap">{{screen.primaryAction}}</button>
  </block>`

const taskActionsWxml = `<view class="task-actions">
    <button class="primary" data-action="accept" disabled="{{loadState === 'loading' || !selectedTaskIds.length}}" bindtap="onBatchTaskAction">接受选中</button>
    <button class="reject" data-action="reject" disabled="{{loadState === 'loading' || !selectedTaskIds.length}}" bindtap="onBatchTaskAction">拒绝接单</button>
  </view>`

const valueEvidenceWxml = `
  <view wx:if="{{options.value_evidence.length}}" class="panel">
    <view class="panel-title">价值证据</view>
    <view wx:for="{{options.value_evidence}}" wx:key="title" class="item">
      <view class="item-main"><view class="item-title">{{item.title}}</view><view class="item-desc">{{item.source_label}}</view></view>
      <view class="badge">{{item.metric}}</view>
    </view>
  </view>`

const cockpitWxml = `
  <view wx:if="{{options.cockpit}}" class="panel">
    <view class="panel-title">项目收益边界</view>
    <view class="item"><view class="item-main"><view class="item-title">中性利润</view></view><view class="badge">{{options.cockpit.neutral_profit}}</view></view>
    <view class="item"><view class="item-main"><view class="item-title">保本人数</view></view><view class="badge">{{options.cockpit.breakeven_attendance}}</view></view>
  </view>`

const workBriefingWxml = `
  <view wx:if="{{options.work_briefing}}" class="panel">
    <view class="panel-title">今日变化 {{options.work_briefing.today_change_count}} 项</view>
    <view wx:if="{{options.work_briefing.top_task}}" class="item"><view class="item-title">{{options.work_briefing.top_task.title}}</view></view>
  </view>`

const projectWorkWxml = `
  <view wx:if="{{options.project_work}}" class="panel">
    <view class="panel-title">项目工作</view>
    <view class="item"><view class="item-main"><view class="item-title">计划 V{{options.project_work.plan_version}}</view><view class="item-desc">{{options.project_work.recommendation}}</view><view class="item-desc">{{options.project_work.human_gate}}</view></view><view class="badge">待处理预警 {{options.project_work.open_alert_count}} 项</view></view>
  </view>`

const calibrationWxml = `
  <view wx:if="{{options.calibration_loop}}" class="panel">
    <view class="panel-title">预测与实际差异</view>
    <view class="item"><view class="item-main"><view class="item-title">预测利润</view></view><view class="badge">{{options.calibration_loop.forecast_profit}}</view></view>
    <view class="item"><view class="item-main"><view class="item-title">实际利润</view></view><view class="badge">{{options.calibration_loop.actual_profit}}</view></view>
  </view>`

export const buildScreenWxml = (screenId, { includeBack = false } = {}) => {
  const projectSearch = ['S13', 'S14', 'S15', 'S16'].includes(screenId) ? projectSearchWxml : ''
  const taskScreen = screenId === 'S56'
  const planScreen = screenId === 'S53'
  const pptV2 = screenId === 'S04' ? valueEvidenceWxml
    : ['S11', 'S25'].includes(screenId) ? cockpitWxml
    : screenId === 'S52' ? workBriefingWxml
    : screenId === 'S53' ? projectWorkWxml
    : screenId === 'S66' ? calibrationWxml
    : ''
  const pptSection = pptV2 ? `\n${pptV2}` : ''
  return `<view class="page">${includeBack ? '\n  <button class="home-button" bindtap="onBackTap">‹</button>' : ''}
  <view class="hero">
    <view class="eyebrow">{{screen.group}} · {{screen.id}}</view>
    <view class="title">{{screen.title}}</view>
    <view class="subtitle">{{screen.subtitle}}</view>
    <view class="highlight">{{screen.highlight}}</view>
  </view>${pptSection}
  <view wx:if="{{isForm}}" class="panel">
    <view class="panel-title">输入与联调</view>
    <input class="input" value="{{keyword}}" bindinput="onInput" placeholder="{{placeholder}}" />${projectSearch}
  </view>
  <view class="panel">
    <view class="panel-head">
      <view class="panel-title">业务记录</view>
      <view class="state {{loadState}}">{{loadState}}</view>
    </view>
    ${taskScreen ? taskItemsWxml : planScreen ? planItemsWxml : businessItemsWxml}
  </view>
  <view class="message" wx:if="{{message}}">{{message}}</view>
  ${taskScreen ? taskActionsWxml : defaultActionsWxml}
</view>
`
}

export const pageStyleFragments = {
  home: `.home-button { min-width: 88rpx; height: 64rpx; }`,
  candidates: `.candidate-groups { margin-top: 24rpx; } .search-dropdown { max-height: 560rpx; }`,
  tasks: `.task-selection { padding: 20rpx 0 4rpx; } .task-actions { display: grid; grid-template-columns: 1fr 1fr; }`,
}
