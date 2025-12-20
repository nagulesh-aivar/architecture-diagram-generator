import { useState, useEffect } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'

interface ComponentItem {
  name: string
  type: string
  description: string
  relationships: string[]
}

interface ComponentCategory {
  category: string
  components: ComponentItem[]
}

interface ComponentListData {
  project_name: string
  summary: string
  categories: ComponentCategory[]
  total_components: number
}

function ComponentList() {
  const { requestId } = useParams<{ requestId: string }>()
  const navigate = useNavigate()
  const [data, setData] = useState<ComponentListData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (!requestId) {
      setError('No request ID provided')
      setLoading(false)
      return
    }

    fetchComponentList()
  }, [requestId])

  const fetchComponentList = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch(`http://localhost:8000/api/component-list/${requestId}`)
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
      }

      const componentData = await response.json()
      setData(componentData)
      
      // Expand all categories by default
      const allCategories = new Set(componentData.categories.map((cat: ComponentCategory) => cat.category))
      setExpandedCategories(allCategories)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => {
      const newSet = new Set(prev)
      if (newSet.has(category)) {
        newSet.delete(category)
      } else {
        newSet.add(category)
      }
      return newSet
    })
  }

  const getTypeColor = (type: string): string => {
    const colors: Record<string, string> = {
      compute: '#FF9900',      // Orange
      storage: '#3B48CC',       // Blue
      database: '#3B48CC',      // Blue
      network: '#7AA116',       // Green
      security: '#DD344C',      // Red
      monitoring: '#146EB4',    // Dark Blue
      integration: '#9C83C9',   // Purple
      error: '#DC2626'          // Error red
    }
    return colors[type.toLowerCase()] || '#6B7280' // Default gray
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: '#F9F8FC' }}>
      {/* Header */}
      <header className="bg-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex justify-between items-center">
            <div className="flex-1">
              <h1 className="text-4xl font-bold mb-2" style={{ color: '#9C83C9' }}>
                Component List
              </h1>
              <p className="text-gray-600 text-lg">
                Structured architecture components and relationships
              </p>
            </div>
            <Link
              to="/"
              className="px-6 py-3 rounded-lg font-semibold text-white transition-all duration-200 hover:shadow-lg flex items-center gap-2"
              style={{ backgroundColor: '#9C83C9' }}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              Home
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading && (
          <div className="text-center py-12">
            <svg 
              className="animate-spin h-12 w-12 mx-auto mb-4" 
              style={{ color: '#9C83C9' }} 
              xmlns="http://www.w3.org/2000/svg" 
              fill="none" 
              viewBox="0 0 24 24"
            >
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <p className="text-gray-600">Generating component list...</p>
          </div>
        )}

        {error && !loading && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <div className="flex items-start">
              <svg className="h-6 w-6 text-red-500 mr-3 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-red-800 mb-2">Error Loading Component List</h3>
                <p className="text-red-700">{error}</p>
              </div>
            </div>
            <div className="mt-6 flex gap-3">
              <button
                onClick={() => navigate('/gallery')}
                className="px-6 py-2 rounded-lg font-semibold text-white transition-all duration-200 hover:shadow-lg"
                style={{ backgroundColor: '#9C83C9' }}
              >
                Back to Gallery
              </button>
              <button
                onClick={fetchComponentList}
                className="px-6 py-2 rounded-lg font-semibold border-2 transition-all duration-200 hover:shadow-lg"
                style={{ borderColor: '#9C83C9', color: '#9C83C9' }}
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {!loading && !error && data && (
          <div className="space-y-6">
            {/* Project Overview */}
            <div className="bg-white rounded-2xl shadow-xl p-6 sm:p-8">
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#9C83C9' }}>
                {data.project_name}
              </h2>
              <p className="text-gray-700 text-lg mb-4">{data.summary}</p>
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
                <span className="font-semibold">{data.total_components}</span> total components
              </div>
            </div>

            {/* Component Categories */}
            {data.categories.map((category, categoryIndex) => (
              <div key={categoryIndex} className="bg-white rounded-2xl shadow-xl overflow-hidden">
                {/* Category Header */}
                <button
                  onClick={() => toggleCategory(category.category)}
                  className="w-full px-6 sm:px-8 py-6 flex items-center justify-between hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div 
                      className="w-3 h-3 rounded-full" 
                      style={{ backgroundColor: '#9C83C9' }}
                    ></div>
                    <h3 className="text-xl font-bold text-gray-800">
                      {category.category}
                    </h3>
                    <span className="text-sm text-gray-500 font-medium">
                      ({category.components.length})
                    </span>
                  </div>
                  <svg
                    className={`w-6 h-6 text-gray-500 transition-transform ${
                      expandedCategories.has(category.category) ? 'transform rotate-180' : ''
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {/* Components List */}
                {expandedCategories.has(category.category) && (
                  <div className="px-6 sm:px-8 pb-6 space-y-4">
                    {category.components.map((component, componentIndex) => (
                      <div
                        key={componentIndex}
                        className="border-l-4 pl-6 py-4 bg-gray-50 rounded-r-lg hover:bg-gray-100 transition-colors"
                        style={{ borderColor: getTypeColor(component.type) }}
                      >
                        {/* Component Header */}
                        <div className="flex items-start justify-between mb-3">
                          <h4 className="text-lg font-semibold text-gray-800">
                            {component.name}
                          </h4>
                          <span
                            className="px-3 py-1 rounded-full text-xs font-semibold text-white"
                            style={{ backgroundColor: getTypeColor(component.type) }}
                          >
                            {component.type}
                          </span>
                        </div>

                        {/* Component Description */}
                        <p className="text-gray-700 mb-3">{component.description}</p>

                        {/* Relationships */}
                        {component.relationships.length > 0 && (
                          <div className="mt-3">
                            <p className="text-sm font-semibold text-gray-600 mb-2">
                              Relationships:
                            </p>
                            <div className="flex flex-wrap gap-2">
                              {component.relationships.map((relationship, relIndex) => (
                                <span
                                  key={relIndex}
                                  className="px-3 py-1 bg-white border border-gray-300 rounded-full text-sm text-gray-700"
                                >
                                  → {relationship}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {/* Action Buttons */}
            <div className="bg-white rounded-2xl shadow-xl p-6 sm:p-8">
              <div className="flex flex-col sm:flex-row gap-4">
                <Link
                  to="/gallery"
                  className="flex-1 text-center px-6 py-3 rounded-lg font-semibold text-white transition-all duration-200 hover:shadow-lg"
                  style={{ backgroundColor: '#9C83C9' }}
                >
                  Back to Gallery
                </Link>
                <Link
                  to={`/pseudo-diagram/${requestId}`}
                  className="flex-1 text-center px-6 py-3 rounded-lg font-semibold border-2 transition-all duration-200 hover:shadow-lg"
                  style={{ borderColor: '#9C83C9', color: '#9C83C9' }}
                >
                  View Pseudo Diagram →
                </Link>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default ComponentList

