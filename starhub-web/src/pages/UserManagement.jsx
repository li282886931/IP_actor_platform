import { useEffect, useState } from 'react'

import { createUser, deleteUser, listUsers, updateUser } from '../api'

const USER_GROUPS = [
  { code: 'B', name: '主办方', role: 'B', description: '项目创建、财务测算、决策推进与任务管理' },
  { code: 'Brand', name: '品牌方', role: 'Brand', description: '查看品牌合作、受众洞察与投放表现' },
  { code: 'G', name: '政府 / 文旅', role: 'G', description: '查看城市文旅、消费拉动与活动风险' },
  { code: 'C', name: '观众端', role: 'C', description: '浏览演出、查看推荐并管理预约' },
]

function canManageUsers(user) {
  return user?.can_manage_users || user?.group_code === 'root' || user?.account === 'root'
}

export default function UserManagement({ currentUser }) {
  const [users, setUsers] = useState([])
  const [selectedGroup, setSelectedGroup] = useState('B')
  const [status, setStatus] = useState('loading')
  const [submitStatus, setSubmitStatus] = useState('idle')
  const [editingUserId, setEditingUserId] = useState(null)
  const [message, setMessage] = useState('')
  const [form, setForm] = useState({
    account: '',
    name: '',
    phone: '',
    password: '',
    group_code: 'B',
  })
  const [editForm, setEditForm] = useState({
    name: '',
    phone: '',
    password: '',
    group_code: 'B',
  })
  const authorized = canManageUsers(currentUser)
  const selectedGroupMeta = USER_GROUPS.find((group) => group.code === selectedGroup) || USER_GROUPS[0]

  useEffect(() => {
    if (!authorized) {
      setStatus('forbidden')
      return
    }

    let active = true
    setStatus('loading')
    listUsers()
      .then((response) => {
        if (!active) return
        setUsers(response.data.data || [])
        setStatus('success')
      })
      .catch(() => {
        if (active) setStatus('error')
      })

    return () => {
      active = false
    }
  }, [authorized])

  const handleGroupSelect = (groupCode) => {
    setSelectedGroup(groupCode)
    setForm((current) => ({ ...current, group_code: groupCode }))
  }

  const handleFieldChange = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }))
  }

  const handleEditFieldChange = (field, value) => {
    setEditForm((current) => ({ ...current, [field]: value }))
  }

  const handleCreateUser = async (event) => {
    event.preventDefault()
    if (!form.account.trim() || !form.password.trim()) {
      setMessage('请填写账号和密码')
      return
    }

    setSubmitStatus('loading')
    setMessage('')
    try {
      const response = await createUser({
        account: form.account.trim(),
        name: form.name.trim() || form.account.trim(),
        phone: form.phone.trim(),
        password: form.password,
        group_code: form.group_code,
      })
      setUsers((current) => [...current, response.data.data])
      setForm({ account: '', name: '', phone: '', password: '', group_code: response.data.data.group_code })
      setSubmitStatus('success')
      setMessage('用户已添加')
    } catch {
      setSubmitStatus('error')
      setMessage('用户添加失败')
    }
  }

  const handleDeleteUser = async (user) => {
    await deleteUser(user.id)
    setUsers((current) => current.filter((item) => item.id !== user.id))
  }

  const startEditUser = (user) => {
    setEditingUserId(user.id)
    setEditForm({
      name: user.name || '',
      phone: user.phone || '',
      password: '',
      group_code: user.group_code || selectedGroup,
    })
  }

  const cancelEditUser = () => {
    setEditingUserId(null)
    setEditForm({ name: '', phone: '', password: '', group_code: selectedGroup })
  }

  const handleUpdateUser = async (event, user) => {
    event.preventDefault()
    const payload = {
      name: editForm.name.trim() || user.account,
      phone: editForm.phone.trim(),
      group_code: editForm.group_code,
    }
    if (editForm.password.trim()) {
      payload.password = editForm.password
    }
    const response = await updateUser(user.id, payload)
    setUsers((current) => current.map((item) => (
      item.id === user.id ? response.data.data : item
    )))
    cancelEditUser()
  }

  if (!authorized) {
    return (
      <div className="state-panel error">
        <strong>无权访问用户管理</strong>
        <span>请使用 root 账号登录。</span>
      </div>
    )
  }

  return (
    <div className="page-stack">
      <section className="page-lead">
        <div>
          <span className="eyebrow">ACCESS CONTROL</span>
          <h2>用户管理</h2>
          <p>维护平台账号，并按固定业务用户组管理页面权限。</p>
        </div>
      </section>

      <section className="user-group-grid" aria-label="用户组选择">
        {USER_GROUPS.map((group) => (
          <button
            className={`user-group-card${selectedGroup === group.code ? ' active' : ''}`}
            key={group.code}
            onClick={() => handleGroupSelect(group.code)}
            type="button"
          >
            <span>{group.code}</span>
            <strong>{group.name}</strong>
            <small>{group.description}</small>
          </button>
        ))}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">CREATE USER</span>
            <h3>添加{selectedGroupMeta.name}用户</h3>
          </div>
          <span className="section-count">{users.length} 个用户</span>
        </div>
        <form className="user-create-form" onSubmit={handleCreateUser}>
          <div className="form-grid">
            <label className="field">
              <span>用户账号</span>
              <input value={form.account} onChange={(event) => handleFieldChange('account', event.target.value)} />
            </label>
            <label className="field">
              <span>用户姓名</span>
              <input value={form.name} onChange={(event) => handleFieldChange('name', event.target.value)} />
            </label>
            <label className="field">
              <span>初始密码</span>
              <input type="password" value={form.password} onChange={(event) => handleFieldChange('password', event.target.value)} />
            </label>
            <label className="field">
              <span>手机号</span>
              <input value={form.phone} onChange={(event) => handleFieldChange('phone', event.target.value)} placeholder="用于小程序授权登录绑定" />
            </label>
            <div className="field">
              <span>用户组</span>
              <output aria-label="用户组" className="readonly-field">
                {selectedGroupMeta.name}
              </output>
            </div>
          </div>
          <button className="button button-primary" disabled={submitStatus === 'loading'} type="submit">
            {submitStatus === 'loading' ? '添加中...' : '添加用户'}
          </button>
        </form>
        {message && <div className={`inline-message ${submitStatus === 'success' ? 'success' : 'error'}`}>{message}</div>}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">USERS</span>
            <h3>全部用户</h3>
          </div>
        </div>
        {status === 'loading' && <div className="state-panel">正在加载用户数据...</div>}
        {status === 'error' && <div className="state-panel error">用户数据暂时不可用</div>}
        {status === 'success' && users.length === 0 && <div className="state-panel">暂无用户</div>}
        {status === 'success' && users.length > 0 && (
          <div className="summary-list">
            {users.map((user) => (
              <span className="user-list-row" key={user.id}>
                {editingUserId === user.id ? (
                  <form className="inline-edit-form" onSubmit={(event) => handleUpdateUser(event, user)}>
                    <strong>{user.account}</strong>
                    <label className="field">
                      <span>编辑用户姓名</span>
                      <input value={editForm.name} onChange={(event) => handleEditFieldChange('name', event.target.value)} />
                    </label>
                    <label className="field">
                      <span>新密码</span>
                      <input type="password" value={editForm.password} onChange={(event) => handleEditFieldChange('password', event.target.value)} />
                    </label>
                    <label className="field">
                      <span>编辑手机号</span>
                      <input value={editForm.phone} onChange={(event) => handleEditFieldChange('phone', event.target.value)} />
                    </label>
                    <label className="field">
                      <span>编辑用户组</span>
                      <select value={editForm.group_code} onChange={(event) => handleEditFieldChange('group_code', event.target.value)}>
                        {USER_GROUPS.map((group) => (
                          <option key={group.code} value={group.code}>{group.name}</option>
                        ))}
                      </select>
                    </label>
                    <div className="inline-actions">
                      <button className="button button-primary" type="submit">保存修改</button>
                      <button className="button button-secondary" type="button" onClick={cancelEditUser}>取消</button>
                    </div>
                  </form>
                ) : (
                  <>
                    <div className="user-list-main">
                      <b>{user.account}</b>
                      <small>{user.name}</small>
                      {user.phone ? <small>{user.phone}</small> : <small>未绑定手机号</small>}
                    </div>
                    <strong className="user-group-code">{user.group_code}</strong>
                    <div className="inline-actions user-row-actions">
                      <button className="button button-secondary" type="button" onClick={() => startEditUser(user)}>
                        修改
                      </button>
                      <button className="button button-secondary" type="button" onClick={() => handleDeleteUser(user)}>
                        删除
                      </button>
                    </div>
                  </>
                )}
              </span>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
