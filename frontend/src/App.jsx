import { useState, useEffect } from 'react'
import './App.css'
import Header from './components/Header'
import PreferenceForm from './components/PreferenceForm'
import ResultsPanel from './components/ResultsPanel'

const API_BASE = 'http://localhost:8000'

function App() {
  const [metadata, setMetadata] = useState({ locations: [], cuisines: [] })
  const [recommendations, setRecommendations] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [summary, setSummary] = useState(null)

  // Fetch dropdown metadata on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/metadata`)
      .then(res => {
        if (!res.ok) throw new Error('Failed to load metadata')
        return res.json()
      })
      .then(data => setMetadata(data))
      .catch(err => {
        console.error('Metadata fetch error:', err)
        setError('Could not connect to the server. Make sure the backend is running on port 8000.')
      })
  }, [])

  const handleSubmit = async (prefs) => {
    setLoading(true)
    setError(null)
    setRecommendations(null)
    setSummary(null)

    try {
      const res = await fetch(`${API_BASE}/api/recommendations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(prefs),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        const detail = body.detail
        if (Array.isArray(detail)) {
          throw new Error(detail.join('\n'))
        }
        throw new Error(detail || `Server error (${res.status})`)
      }

      const data = await res.json()
      setRecommendations(data)

      // Extract summary from first recommendation
      if (data.length > 0 && data[0].summary) {
        setSummary(data[0].summary)
      }
    } catch (err) {
      console.error('Recommendation error:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <Header />
      <main className="app-main">
        <aside className="app-sidebar">
          <PreferenceForm
            locations={metadata.locations}
            cuisines={metadata.cuisines}
            onSubmit={handleSubmit}
            loading={loading}
          />
        </aside>
        <section className="app-results">
          <ResultsPanel
            recommendations={recommendations}
            loading={loading}
            error={error}
            summary={summary}
          />
        </section>
      </main>
    </div>
  )
}

export default App
