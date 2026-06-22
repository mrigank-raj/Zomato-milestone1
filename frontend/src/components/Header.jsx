import './Header.css'

export default function Header() {
  return (
    <header className="header glass">
      <div className="header-inner">
        <div className="header-brand">
          <span className="header-logo">🍽️</span>
          <h1 className="header-title">
            Zomato AI <span className="header-title-accent">Recommender</span>
          </h1>
        </div>

        <nav className="header-nav">
          <a href="#" className="header-nav-link active">Discover</a>
          <a href="#" className="header-nav-link">Favorites</a>
          <a href="#" className="header-nav-link">History</a>
        </nav>

        <div className="header-actions">
          <div className="header-avatar">
            <span>AI</span>
          </div>
        </div>
      </div>
    </header>
  )
}
