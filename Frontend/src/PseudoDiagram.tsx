import { useState, useEffect, useRef } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'

interface PseudoDiagramData {
  project_name: string
  diagram_type: string
  description: string
  syntax: string
}

function PseudoDiagram() {
  const { requestId } = useParams<{ requestId: string }>()
  const navigate = useNavigate()
  const [data, setData] = useState<PseudoDiagramData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!requestId) {
      setError('No request ID provided')
      setLoading(false)
      return
    }

    fetchPseudoDiagram()
  }, [requestId])

  const fetchPseudoDiagram = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch(`http://localhost:8000/api/pseudo-diagram/${requestId}`)
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
      }

      const diagramData = await response.json()
      setData(diagramData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = async () => {
    if (!data) return

    try {
      await navigator.clipboard.writeText(data.syntax)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      // Fallback: select text
      if (textareaRef.current) {
        textareaRef.current.select()
        document.execCommand('copy')
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      }
    }
  }

  const handleDownload = () => {
    if (!data) return

    const blob = new Blob([data.syntax], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${data.project_name.replace(/\s+/g, '_')}_diagram.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: '#F9F8FC' }}>
      {/* Header */}
      <header className="bg-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex justify-between items-center">
            <div className="flex-1">
              <h1 className="text-4xl font-bold mb-2" style={{ color: '#9C83C9' }}>
                Pseudo Diagram Description
              </h1>
              <p className="text-gray-600 text-lg">
                Text-based diagram syntax for visualization tools
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
            <p className="text-gray-600">Generating pseudo diagram...</p>
          </div>
        )}

        {error && !loading && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <div className="flex items-start">
              <svg className="h-6 w-6 text-red-500 mr-3 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-red-800 mb-2">Error Loading Pseudo Diagram</h3>
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
                onClick={fetchPseudoDiagram}
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
              <p className="text-gray-700 text-lg mb-4">{data.description}</p>
              <div className="flex items-center gap-2">
                <span 
                  className="px-4 py-2 rounded-lg text-sm font-semibold text-white"
                  style={{ backgroundColor: '#9C83C9' }}
                >
                  {data.diagram_type.toUpperCase()}
                </span>
                <span className="text-sm text-gray-600">
                  Copy-paste ready for visualization tools
                </span>
              </div>
            </div>

            {/* Diagram Syntax */}
            <div className="bg-white rounded-2xl shadow-xl p-6 sm:p-8">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold text-gray-800">Diagram Syntax</h3>
                <div className="flex gap-2">
                  <button
                    onClick={handleCopy}
                    className="px-4 py-2 rounded-lg font-semibold text-white transition-all duration-200 hover:shadow-lg flex items-center gap-2"
                    style={{ backgroundColor: copied ? '#10B981' : '#9C83C9' }}
                  >
                    {copied ? (
                      <>
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        Copied!
                      </>
                    ) : (
                      <>
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                        Copy
                      </>
                    )}
                  </button>
                  <button
                    onClick={handleDownload}
                    className="px-4 py-2 rounded-lg font-semibold border-2 transition-all duration-200 hover:shadow-lg flex items-center gap-2"
                    style={{ borderColor: '#9C83C9', color: '#9C83C9' }}
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Download
                  </button>
                </div>
              </div>

              <div className="relative">
                <textarea
                  ref={textareaRef}
                  value={data.syntax}
                  readOnly
                  className="w-full h-96 p-4 font-mono text-sm bg-gray-900 text-green-400 rounded-lg border-2 border-gray-700 focus:outline-none focus:border-purple-500 resize-none overflow-auto"
                  style={{ lineHeight: '1.5' }}
                />
              </div>

              {/* Usage Instructions */}
              <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <h4 className="text-sm font-semibold text-blue-800 mb-2">How to use:</h4>
                <ul className="text-sm text-blue-700 space-y-1 list-disc list-inside">
                  <li>Copy the syntax above using the "Copy" button</li>
                  <li>Open your preferred diagramming tool (Mermaid Live Editor, draw.io, etc.)</li>
                  <li>Paste the syntax into the tool</li>
                  <li>The diagram will be automatically rendered</li>
                  <li>Customize colors, layout, and styling as needed</li>
                </ul>
              </div>

              {/* Recommended Tools */}
              <div className="mt-4 p-4 bg-purple-50 border border-purple-200 rounded-lg">
                <h4 className="text-sm font-semibold text-purple-800 mb-3">Recommended Tools:</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <a
                    href="https://mermaid.live"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 bg-white border-2 border-purple-300 rounded-lg text-center font-medium text-purple-700 hover:bg-purple-100 transition-colors"
                  >
                    Mermaid Live →
                  </a>
                  <a
                    href="https://app.diagrams.net"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 bg-white border-2 border-purple-300 rounded-lg text-center font-medium text-purple-700 hover:bg-purple-100 transition-colors"
                  >
                    draw.io →
                  </a>
                </div>
              </div>
            </div>

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
                  to={`/component-list/${requestId}`}
                  className="flex-1 text-center px-6 py-3 rounded-lg font-semibold border-2 transition-all duration-200 hover:shadow-lg"
                  style={{ borderColor: '#9C83C9', color: '#9C83C9' }}
                >
                  View Component List →
                </Link>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default PseudoDiagram

