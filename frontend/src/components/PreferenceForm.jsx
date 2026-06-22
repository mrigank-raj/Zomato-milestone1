import { useState } from 'react'
import './PreferenceForm.css'

const BUDGET_OPTIONS = ['low', 'medium', 'high']

export default function PreferenceForm({ locations, cuisines, onSubmit, loading }) {
  const [location, setLocation] = useState('')
  const [budget, setBudget] = useState('medium')
  const [cuisine, setCuisine] = useState('')
  const [minRating, setMinRating] = useState(3.5)
  const [additional, setAdditional] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit({
      location,
      budget,
      cuisine,
      min_rating: parseFloat(minRating),
      additional: additional.trim() || null,
      top_n: 5,
    })
  }

  return (
    <div className="pref-form glass">
      <div className="pref-form-header">
        <h2 className="pref-form-title">Find Your Perfect Restaurant</h2>
        <p className="pref-form-subtitle">
          Our AI analyzes thousands of data points to predict your next craving.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="pref-form-fields">
        {/* Location */}
        <div className="form-group">
          <label htmlFor="location">📍 Location</label>
          <select
            id="location"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            required
          >
            <option value="" disabled>Select a location...</option>
            {locations.map((loc) => (
              <option key={loc} value={loc}>{loc}</option>
            ))}
          </select>
        </div>

        {/* Budget */}
        <div className="form-group">
          <label>💰 Budget Range</label>
          <div className="budget-toggle">
            {BUDGET_OPTIONS.map((opt) => (
              <button
                key={opt}
                type="button"
                className={`budget-btn ${budget === opt ? 'active' : ''}`}
                onClick={() => setBudget(opt)}
              >
                {opt.charAt(0).toUpperCase() + opt.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Cuisine */}
        <div className="form-group">
          <label htmlFor="cuisine">🍕 Cuisine Type</label>
          <select
            id="cuisine"
            value={cuisine}
            onChange={(e) => setCuisine(e.target.value)}
            required
          >
            <option value="" disabled>Select a cuisine...</option>
            {cuisines.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        {/* Min Rating */}
        <div className="form-group">
          <label htmlFor="minRating">⭐ Minimum Rating</label>
          <div className="rating-slider">
            <input
              id="minRating"
              type="range"
              min="0"
              max="5"
              step="0.1"
              value={minRating}
              onChange={(e) => setMinRating(e.target.value)}
            />
            <span className="rating-value">{parseFloat(minRating).toFixed(1)}</span>
          </div>
        </div>

        {/* Additional */}
        <div className="form-group">
          <label htmlFor="additional">📝 Additional Preferences</label>
          <textarea
            id="additional"
            placeholder="e.g. family-friendly, rooftop seating, live music..."
            value={additional}
            onChange={(e) => setAdditional(e.target.value)}
            rows={3}
          />
        </div>

        {/* Submit */}
        <button
          type="submit"
          className="submit-btn"
          disabled={loading || !location || !cuisine}
        >
          {loading ? (
            <>
              <span className="spinner" />
              Analyzing...
            </>
          ) : (
            <>
              <span className="submit-icon">✨</span>
              Get Recommendations
            </>
          )}
        </button>
      </form>
    </div>
  )
}
