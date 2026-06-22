import './RecommendationCard.css'

/* Curated food images for visual variety */
const FOOD_IMAGES = [
  'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=400&h=300&fit=crop',
  'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=400&h=300&fit=crop',
  'https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=400&h=300&fit=crop',
  'https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=400&h=300&fit=crop',
  'https://images.unsplash.com/photo-1482049016688-2d3e1b311543?w=400&h=300&fit=crop',
  'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=400&h=300&fit=crop',
  'https://images.unsplash.com/photo-1476224203421-9ac39bcb3327?w=400&h=300&fit=crop',
  'https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=400&h=300&fit=crop',
]

function StarRating({ rating }) {
  const fullStars = Math.floor(rating)
  const hasHalf = rating - fullStars >= 0.3
  const emptyStars = 5 - fullStars - (hasHalf ? 1 : 0)

  return (
    <span className="star-rating" aria-label={`${rating} out of 5 stars`}>
      {'★'.repeat(fullStars)}
      {hasHalf && <span className="star-half">★</span>}
      {'☆'.repeat(Math.max(0, emptyStars))}
    </span>
  )
}

export default function RecommendationCard({ recommendation, index }) {
  const { rank, restaurant, explanation } = recommendation
  const { name, location, cuisines, rating, cost_for_two, address, votes } = restaurant

  const imgSrc = FOOD_IMAGES[index % FOOD_IMAGES.length]

  return (
    <article
      className="rec-card glass fade-in-up"
      style={{ animationDelay: `${index * 80}ms` }}
    >
      {/* Image */}
      <div className="rec-card-image">
        <img src={imgSrc} alt={name} loading="lazy" />
        <div className="rec-card-rank">#{rank}</div>
      </div>

      {/* Content */}
      <div className="rec-card-body">
        <div className="rec-card-header">
          <h3 className="rec-card-name">{name}</h3>
          <div className="rec-card-rating-badge">
            <span className="rating-star">★</span>
            <span>{rating.toFixed(1)}</span>
          </div>
        </div>

        <div className="rec-card-meta">
          <span className="rec-card-location">📍 {location}</span>
          {cost_for_two && (
            <span className="rec-card-cost">💰 ₹{cost_for_two.toLocaleString()} for two</span>
          )}
        </div>

        {/* Cuisine tags */}
        <div className="rec-card-tags">
          {cuisines.slice(0, 4).map((c) => (
            <span key={c} className="cuisine-tag">{c}</span>
          ))}
        </div>

        {/* AI Explanation */}
        <blockquote className="rec-card-explanation">
          <span className="explanation-icon">✨</span>
          <p>"{explanation}"</p>
        </blockquote>

        {/* Footer meta */}
        {(votes || address) && (
          <div className="rec-card-footer">
            {votes != null && votes > 0 && (
              <span className="rec-card-votes">👍 {votes.toLocaleString()} votes</span>
            )}
            {address && (
              <span className="rec-card-address" title={address}>🏠 {address}</span>
            )}
          </div>
        )}
      </div>
    </article>
  )
}
