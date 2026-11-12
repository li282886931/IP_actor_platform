(function () {
  const flows = {
    admin: { action: '审阅并确认授权', missing: '成员、空间或职责未确定，无法授权。保留配置草稿并列出缺失项。', success: '规则预览：授权进入生效状态；保存变更记录，成员只能获得已确认范围内的权限。', denied: '规则预览：当前操作者不具备该空间管理权限，禁止授权；返回获授权的管理范围。' },
    business: { action: '发出合作邀请', missing: '接收人或项目授权范围未确定，无法发出。邀请保持草稿，先补齐关系与要求。', success: '规则预览：邀请进入已发出状态；仅向选定合作方生成待回复事项，关联当前资料版本。', denied: '规则预览：当前账号不是该项目获授权负责人，禁止发出邀请；不修改项目或对方待办。' },
    brand: { action: '提交权益验收意见', missing: '权益版本或交付证明缺失，不能验收通过。保留待验收并说明需要补齐的材料。', success: '规则预览：本项权益进入已验收状态；保留验收人、证据版本与意见，通知对应交付方。', denied: '规则预览：当前账号不属于本合作事项的品牌验收方，禁止提交；不开放其他品牌的意见。' },
    government: { action: '提交材料补件要求', missing: '缺失材料、接收责任人或属地范围未确定，不能发出补件要求。保留草稿并提示补齐。', success: '规则预览：事项进入待补件状态；通知授权责任人并保留核验记录。这不是法定审批决定。', denied: '规则预览：项目不属于当前账号授权属地或事项范围，禁止操作；城市偏好不会扩大权限。' },
    audience: { action: '确认取消本人登记', missing: '当前账号没有有效预约登记，不能取消。显示个人登记为空并提供演出发现入口。', success: '规则预览：本人登记进入已取消状态并保留历史。这不会退款，也不会修改真实票务订单。', denied: '规则预览：该登记不属于当前账号与空间，禁止操作；不能通过姓名或手机号认领。' },
    investor: { action: '提交附条件投资意见', missing: '指定版本、投资意见或要求材料未确定，不能提交。保留私人草稿，不自动补造金额。', success: '规则预览：意见进入条件待回复状态；关联指定测算版本，通知授权主办方。不代表签约或打款。', denied: '规则预览：当前账号未获本项目财务资料或意见提交授权，禁止操作；不显示其他资方私人意见。' },
    artist: { action: '回复愿意继续沟通', missing: '本人身份尚未绑定或邀请时间、要求不完整，不能确认意向。保留回复草稿并要求补齐。', success: '规则预览：邀请进入意向确认状态；保存本人回复与邀请版本，通知主办方。不锁定档期或自动签约。', denied: '规则预览：邀请不是发给本人，禁止回复；不能操作同名艺人或其他艺人的邀请。' },
  }
  document.querySelectorAll('[data-flow]').forEach((element) => {
    const key = element.dataset.flow
    const flow = flows[key]
    const controls = document.createElement('div')
    controls.className = 'preview-controls'
    const label = document.createElement('label')
    label.htmlFor = `condition-${key}`
    label.textContent = '审阅条件'
    const select = document.createElement('select')
    select.id = label.htmlFor
    for (const [value, text] of [['missing', '材料不完整'], ['success', '资料齐备且有权限'], ['denied', '无对象操作权限']]) {
      const option = document.createElement('option')
      option.value = value
      option.textContent = text
      select.append(option)
    }
    const button = document.createElement('button')
    button.type = 'button'
    button.textContent = flow.action
    const feedback = document.createElement('div')
    feedback.className = 'feedback'
    feedback.setAttribute('role', 'status')
    feedback.setAttribute('aria-live', 'polite')
    feedback.textContent = '选择审阅条件，再点击动作查看对应规则。预览不会写入业务记录。'
    select.addEventListener('change', () => {
      feedback.removeAttribute('data-status')
      feedback.textContent = '条件已切换，请点击动作查看对应规则。'
    })
    button.addEventListener('click', () => {
      feedback.dataset.status = select.value === 'success' ? 'success' : 'blocked'
      feedback.textContent = flow[select.value]
    })
    controls.append(label, select, button)
    element.append(controls, feedback)
  })
  document.getElementById('role-filter').addEventListener('change', (event) => {
    document.querySelectorAll('.role-section').forEach(section => {
      section.hidden = event.target.value !== 'all' && section.dataset.role !== event.target.value
    })
  })
  document.querySelectorAll('a[href^="#role-"]').forEach(link => {
    link.addEventListener('click', () => {
      document.getElementById('role-filter').value = 'all'
      document.querySelectorAll('.role-section').forEach(section => { section.hidden = false })
    })
  })
})()
