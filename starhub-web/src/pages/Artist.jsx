import { useState } from 'react'

import { searchArtist } from '../api'

export default function Artist({ role = 'B' }) {
  const [query, setQuery] = useState('')
  const [artist, setArtist] = useState(null)
  const [status, setStatus] = useState('idle')
  const [suggestions, setSuggestions] = useState([])
  const [isSuggestionOpen, setIsSuggestionOpen] = useState(false)

  const handleQueryChange = async (event) => {
    const value = event.target.value
    const keyword = value.trim()
    setQuery(value)

    if (!keyword) {
      setSuggestions([])
      setIsSuggestionOpen(false)
      setArtist(null)
      setStatus('idle')
      return
    }

    try {
      const response = await searchArtist(keyword)
      setSuggestions(response.data.data || [])
      setIsSuggestionOpen(true)
    } catch {
      setSuggestions([])
      setIsSuggestionOpen(false)
    }
  }

  const handleSearch = async (event) => {
    event?.preventDefault()
    if (!query.trim()) return

    setStatus('loading')
    try {
      const response = await searchArtist(query.trim())
      const result = response.data.data?.[0] || null
      setArtist(result)
      setStatus(result ? 'success' : 'empty')
    } catch {
      setArtist(null)
      setStatus('error')
    }
  }

  const handleSelectSuggestion = (selectedArtist) => {
    setQuery(selectedArtist.name)
    setArtist(selectedArtist)
    setStatus('success')
    setSuggestions([])
    setIsSuggestionOpen(false)
  }

  return (
    <div className="page-stack">
      <section className="page-lead">
        <div>
          <span className="eyebrow">ARTIST INTELLIGENCE</span>
          <h2>{role === 'C' ? '查找你关注的艺人' : '艺人热度与风险洞察'}</h2>
          <p>通过公开热度、粉丝规模和风险等级辅助演出与合作决策。</p>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">QUICK SEARCH</span>
            <h3>艺人查询</h3>
          </div>
          <span className="panel-note">支持艺人名称模糊搜索</span>
        </div>
        <form className="search-form" onSubmit={handleSearch}>
          <label className="field grow suggestion-field">
            <span>艺人名称</span>
            <input
              value={query}
              onChange={handleQueryChange}
              onFocus={() => setIsSuggestionOpen(suggestions.length > 0)}
              placeholder="输入艺人名字，如：周杰伦"
            />
            {isSuggestionOpen && suggestions.length > 0 && (
              <div className="suggestion-list" role="listbox" aria-label="艺人搜索建议">
                {suggestions.map((item) => (
                  <button
                    className="suggestion-option"
                    key={item.id}
                    type="button"
                    aria-label={`选择 ${item.name}`}
                    onClick={() => handleSelectSuggestion(item)}
                  >
                    <span>
                      <strong>{item.name}</strong>
                      <small>{item.tags || '暂无标签'}</small>
                    </span>
                    <em>热度 {item.heat_score}</em>
                  </button>
                ))}
              </div>
            )}
          </label>
          <button className="button button-primary" disabled={status === 'loading'} type="submit">
            {status === 'loading' ? '查询中...' : '查询热度'}
          </button>
        </form>
      </section>

      {status === 'error' && (
        <div className="state-panel error">
          <strong>艺人数据查询失败</strong>
          <span>请确认后端服务状态后重试。</span>
        </div>
      )}

      {status === 'empty' && (
        <div className="state-panel">
          <strong>未找到匹配艺人</strong>
          <span>请尝试输入更完整的艺人名称。</span>
        </div>
      )}

      {artist && (
        <section className="artist-overview">
          <article className="panel artist-profile">
            <div className="artist-identity">
              <div className="artist-avatar" aria-hidden="true">{artist.name?.[0]}</div>
              <div>
                <span className="status-badge positive">数据已更新</span>
                <h3>{artist.name}</h3>
                <p>{artist.tags || '暂无标签'}</p>
              </div>
            </div>
            <dl className="artist-facts">
              <div><dt>综合热度</dt><dd>{artist.heat_score}</dd></div>
              <div><dt>全网粉丝</dt><dd>{artist.fan_count}</dd></div>
              <div><dt>风险等级</dt><dd className={artist.risk_level > 2 ? 'text-danger' : ''}>{artist.risk_level} / 5</dd></div>
            </dl>
          </article>

          <article className="panel insight-panel">
            <div className="panel-heading">
              <div>
                <span className="eyebrow">AI INSIGHT</span>
                <h3>演出建议</h3>
              </div>
            </div>
            <p>该艺人当前关注度较高，建议优先评估一线及新一线城市的大型场馆档期。</p>
            <div className="recommendation-list">
              <span>推荐档期<strong>暑期 / 国庆</strong></span>
              <span>建议场馆<strong>大型体育场</strong></span>
              <span>传播重点<strong>经典作品与现场感</strong></span>
            </div>
          </article>
        </section>
      )}

      {status === 'idle' && (
        <div className="state-panel">
          <strong>开始一次艺人分析</strong>
          <span>输入艺人名称后即可查看热度、粉丝量和风险信息。</span>
        </div>
      )}
    </div>
  )
}
