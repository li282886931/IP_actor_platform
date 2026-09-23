import { Link } from 'react-router-dom'

export default function ShowCard({ show }) {
  const imagePrompt = encodeURIComponent(
    `Realistic live concert photography for ${show.artist_name || show.title}, wide stage, audience, professional lighting, editorial event poster, no text`,
  )
  const imageUrl = `https://copilot-cn.bytedance.net/api/ide/v1/text_to_image?prompt=${imagePrompt}&image_size=landscape_4_3`

  return (
    <Link to={`/show/${show.id}`} className="show-card">
      <div className="show-image-wrap">
        <img className="show-image" src={imageUrl} alt={`${show.title}现场`} />
        <span className="show-status">{show.status === 'on_sale' ? '售票中' : '即将开售'}</span>
      </div>
      <div className="show-card-body">
        <div className="show-date">{show.date || '日期待定'}</div>
        <h4>{show.title}</h4>
        <p>{show.city} · {show.venue}</p>
        <div className="show-card-footer">
          <span>{show.artist_name || '演出项目'}</span>
          <strong>¥{show.price}<small> 起</small></strong>
        </div>
      </div>
    </Link>
  )
}
