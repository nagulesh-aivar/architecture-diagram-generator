import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

interface Diagram {
  filename: string
  size: number
  created: number
  modified: number
  url: string
}

function Gallery() {
  const [diagrams, setDiagrams] = useState<Diagram[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchDiagrams()
    // Refresh every 10 seconds
    const interval = setInterval(fetchDiagrams, 10000)
    return () => clearInterval(interval)
  }, [])

  const fetchDiagrams = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/diagrams')
      if (!response.ok) {
        throw new Error('Failed to fetch diagrams')
      }
      const data = await response.json()
      setDiagrams(data.diagrams || [])
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString()
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: '#F9F8FC' }}>
      {/* Header */}
      <header className="bg-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-4xl font-bold mb-2" style={{ color: '#9C83C9' }}>
                Diagram Gallery
              </h1>
              <p className="text-gray-600 text-lg">
                View all generated architecture diagrams
              </p>
            </div>
            <Link
              to="/"
              className="px-6 py-3 rounded-lg font-semibold text-white transition-all duration-200 hover:shadow-lg"
              style={{ backgroundColor: '#9C83C9' }}
            >
              ← Back to Generator
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading && (
          <div className="text-center py-12">
            <svg className="animate-spin h-12 w-12 mx-auto mb-4" style={{ color: '#9C83C9' }} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <p className="text-gray-600">Loading diagrams...</p>
          </div>
        )}

        {error && !loading && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-800">Error: {error}</p>
          </div>
        )}

        {!loading && !error && diagrams.length === 0 && (
          <div className="text-center py-12">
            <svg className="mx-auto h-24 w-24 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <h3 className="text-xl font-semibold text-gray-700 mb-2">No diagrams yet</h3>
            <p className="text-gray-600 mb-6">Generate your first diagram to see it here</p>
            <Link
              to="/"
              className="inline-block px-6 py-3 rounded-lg font-semibold text-white transition-all duration-200 hover:shadow-lg"
              style={{ backgroundColor: '#9C83C9' }}
            >
              Generate Diagram
            </Link>
          </div>
        )}

        {!loading && !error && diagrams.length > 0 && (
          <>
            <div className="mb-6 text-center">
              <p className="text-gray-600">
                Showing {diagrams.length} diagram{diagrams.length !== 1 ? 's' : ''}
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {diagrams.map((diagram) => (
                <div
                  key={diagram.filename}
                  className="bg-white rounded-2xl shadow-xl overflow-hidden transition-all duration-200 hover:shadow-2xl hover:scale-[1.02]"
                >
                  <div className="aspect-video bg-gray-100 relative">
                    <img
                      src={`http://localhost:8000${diagram.url}`}
                      alt={diagram.filename}
                      className="w-full h-full object-contain"
                      loading="lazy"
                    />
                  </div>
                  <div className="p-4">
                    <h3 className="text-sm font-semibold mb-2 truncate" title={diagram.filename}>
                      {diagram.filename}
                    </h3>
                    <div className="text-xs text-gray-600 space-y-1 mb-4">
                      <p>Size: {formatSize(diagram.size)}</p>
                      <p>Created: {formatDate(diagram.created)}</p>
                    </div>
                    <div className="flex gap-2">
                      <a
                        href={`http://localhost:8000${diagram.url}`}
                        download={diagram.filename}
                        className="flex-1 text-center px-4 py-2 rounded-lg font-semibold text-white transition-all duration-200 hover:shadow-lg"
                        style={{ backgroundColor: '#9C83C9' }}
                      >
                        Download
                      </a>
                      <a
                        href={`http://localhost:8000${diagram.url}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 text-center px-4 py-2 rounded-lg font-semibold border-2 transition-all duration-200 hover:shadow-lg"
                        style={{ borderColor: '#9C83C9', color: '#9C83C9' }}
                      >
                        View
                      </a>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  )
}

export default Gallery

