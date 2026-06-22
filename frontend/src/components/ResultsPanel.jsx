import RecommendationCard from './RecommendationCard'
import './ResultsPanel.css'

function SkeletonCard() {
  return (
    <div className="skeleton-card glass">
      <div className="skeleton skeleton-image" />
      <div className="skeleton-body">
        <div className="skeleton skeleton-title" />
        <div className="skeleton skeleton-meta" />
        <div className="skeleton-tags-row">
          <div className="skeleton skeleton-tag" />
          <div className="skeleton skeleton-tag" />
          <div className="skeleton skeleton-tag" />
        </div>
        <div className="skeleton skeleton-text" />
        <div className="skeleton skeleton-text short" />
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="results-empty fade-in-up">
      <div className="empty-icon">🍽️</div>
      <h3>No restaurants match your criteria</h3>
      <p>Try relaxing your filters — lower the minimum rating, change the budget, or pick a different cuisine.</p>
    </div>
  )
}

function ErrorBanner({ message }) {
  return (
    <div className="results-error fade-in-up">
      <span className="error-icon">⚠️</span>
      <div className="error-content">
        <strong>Something went wrong</strong>
        <p>{message}</p>
      </div>
    </div>
  )
}

function WelcomeState() {
  return (
    <div className="results-welcome fade-in-up">
      <div className="welcome-visual">
        <div className="welcome-ring ring-1" />
        <div className="welcome-ring ring-2" />
        <div className="welcome-ring ring-3" />
        <span className="welcome-icon">🔍</span>
      </div>
      <h3>Discover your next favourite restaurant</h3>
      <p>Fill in your preferences on the left and let our AI find the perfect match for you.</p>
    </div>
  )
}

export default function ResultsPanel({ recommendations, loading, error, summary }) {
  // Loading state
  if (loading) {
    return (
      <div className="results-panel">
        <div className="results-header">
          <h2 className="results-title">
            <span className="results-title-icon">🎯</span>
            Finding your top picks...
          </h2>
        </div>
        <div className="results-list">
          {[0, 1, 2, 3, 4].map((i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="results-panel">
        <ErrorBanner message={error} />
      </div>
    )
  }

  // No search yet
  if (recommendations === null) {
    return (
      <div className="results-panel">
        <WelcomeState />
      </div>
    )
  }

  // Empty results
  if (recommendations.length === 0) {
    return (
      <div className="results-panel">
        <EmptyState />
      </div>
    )
  }

  // Results
  return (
    <div className="results-panel">
      <div className="results-header fade-in-up">
        <div className="results-header-top">
          <h2 className="results-title">
            <span className="results-title-icon">🎯</span>
            Top Picks for You
          </h2>
          <span className="results-badge">Scored by AI Match Score</span>
        </div>
        {summary && (
          <div className="results-summary">
            <span className="summary-icon">💡</span>
            <p>{summary}</p>
          </div>
        )}
      </div>

      <div className="results-list">
        {recommendations.map((rec, index) => (
          <RecommendationCard key={rec.restaurant.id} recommendation={rec} index={index} />
        ))}
      </div>

      <div className="results-footer fade-in-up">
        <p>Showing {recommendations.length} AI-curated recommendation{recommendations.length !== 1 ? 's' : ''}</p>
      </div>
    </div>
  )
}
