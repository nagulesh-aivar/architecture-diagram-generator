import { useState } from 'react'

interface UploadResponse {
  success: boolean
  message?: string
  summary?: string
  diagram_path?: string
}

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [diagramUrl, setDiagramUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [awsRegion, setAwsRegion] = useState('us-east-1')
  const [bedrockModelId, setBedrockModelId] = useState('anthropic.claude-3-sonnet-20240229-v1:0')

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      if (file.type === 'application/pdf') {
        setSelectedFile(file)
        setError(null)
        setDiagramUrl(null)
      } else {
        setError('Please select a PDF file')
        setSelectedFile(null)
      }
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a PDF file first')
      return
    }

    setUploading(true)
    setError(null)
    setDiagramUrl(null)

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('aws_region', awsRegion)
      formData.append('bedrock_model_id', bedrockModelId)

      const response = await fetch('http://localhost:8000/api/generate-diagram', {
        method: 'POST',
        body: formData,
        cache: 'no-store', // Prevent caching
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
      }

      // Check if response is an image
      const contentType = response.headers.get('content-type')
      console.log('Response content-type:', contentType)
      console.log('Response status:', response.status)
      
      if (contentType && contentType.startsWith('image/')) {
        // Revoke old URL to prevent memory leaks
        if (diagramUrl) {
          URL.revokeObjectURL(diagramUrl)
        }
        
        // Create blob URL for the image with cache-busting
        const blob = await response.blob()
        console.log('Blob size:', blob.size, 'bytes')
        console.log('Blob type:', blob.type)
        
        if (blob.size === 0) {
          throw new Error('Received empty image file from server')
        }
        
        const url = URL.createObjectURL(blob)
        setDiagramUrl(url)
        setError(null) // Clear any previous errors
        
        // Log the filename for debugging
        const filename = response.headers.get('X-Filename')
        const fileSize = response.headers.get('X-File-Size')
        if (filename) {
          console.log('Loaded diagram:', filename, 'Size:', fileSize, 'bytes')
        }
      } else {
        // Handle JSON response (if diagram generation failed)
        try {
          const data: UploadResponse = await response.json()
          if (data.summary) {
            // Show summary in a readable format
            setError(
              `Diagram generation unavailable (strands/mcp not installed). Architecture Summary:\n\n${data.summary.substring(0, 500)}${data.summary.length > 500 ? '...' : ''}`
            )
          } else {
            setError(data.message || 'Diagram generation failed')
          }
        } catch (jsonError) {
          setError('Failed to parse response from server')
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred while processing the PDF')
      console.error('Upload error:', err)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: '#F9F8FC' }}>
      {/* Header */}
      <header className="bg-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center">
            <h1 className="text-4xl font-bold mb-2" style={{ color: '#9C83C9' }}>
              Architecture Diagram Generator
            </h1>
            <p className="text-gray-600 text-lg">
              Upload a SOW PDF to generate an architecture diagram
            </p>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Upload Card */}
        <div className="bg-white rounded-2xl shadow-xl p-6 sm:p-8 mb-8">
          <h2 className="text-2xl font-semibold mb-6" style={{ color: '#9C83C9' }}>
            Upload PDF Document
          </h2>
          
          {/* File Upload */}
          <div className="mb-6">
            <label 
              htmlFor="file-input" 
              className="block w-full p-6 border-2 border-dashed rounded-xl cursor-pointer transition-all duration-200 hover:border-[#9C83C9] hover:bg-[#F9F8FC]"
              style={{ 
                borderColor: selectedFile ? '#9C83C9' : '#E5E7EB',
                backgroundColor: selectedFile ? '#F9F8FC' : 'transparent'
              }}
            >
              <div className="text-center">
                {selectedFile ? (
                  <div>
                    <svg className="mx-auto h-12 w-12 mb-2" style={{ color: '#9C83C9' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <p className="text-sm font-medium" style={{ color: '#9C83C9' }}>
                      {selectedFile.name}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      Click to change file
                    </p>
                  </div>
                ) : (
                  <div>
                    <svg className="mx-auto h-12 w-12 mb-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    <p className="text-sm font-medium text-gray-700">
                      Choose PDF File
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      PDF files only
                    </p>
                  </div>
                )}
              </div>
            </label>
            <input
              id="file-input"
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              className="hidden"
              disabled={uploading}
            />
          </div>

          {/* AWS Region Input */}
          <div className="mb-6">
            <label htmlFor="aws-region" className="block text-sm font-medium text-gray-700 mb-2">
              AWS Region
            </label>
            <input
              id="aws-region"
              type="text"
              value={awsRegion}
              onChange={(e) => setAwsRegion(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#9C83C9] focus:border-[#9C83C9] outline-none transition-all disabled:bg-gray-100 disabled:cursor-not-allowed"
              disabled={uploading}
              placeholder="us-east-1"
            />
          </div>

          {/* Bedrock Model ID Input */}
          <div className="mb-6">
            <label htmlFor="bedrock-model" className="block text-sm font-medium text-gray-700 mb-2">
              Bedrock Model ID
            </label>
            <input
              id="bedrock-model"
              type="text"
              value={bedrockModelId}
              onChange={(e) => setBedrockModelId(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#9C83C9] focus:border-[#9C83C9] outline-none transition-all disabled:bg-gray-100 disabled:cursor-not-allowed"
              disabled={uploading}
              placeholder="anthropic.claude-3-sonnet-20240229-v1:0"
            />
          </div>

          {/* Upload Button */}
          <button
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            className="w-full py-4 px-6 rounded-lg font-semibold text-white text-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-lg hover:scale-[1.02] active:scale-[0.98]"
            style={{ 
              backgroundColor: '#9C83C9',
            }}
            onMouseEnter={(e) => {
              if (!uploading && selectedFile) {
                e.currentTarget.style.backgroundColor = '#8B72B8'
              }
            }}
            onMouseLeave={(e) => {
              if (!uploading && selectedFile) {
                e.currentTarget.style.backgroundColor = '#9C83C9'
              }
            }}
          >
            {uploading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Processing...
              </span>
            ) : (
              'Generate Diagram'
            )}
          </button>

          {/* Error Message */}
          {error && (
            <div className="mt-6 p-4 rounded-lg" style={{ backgroundColor: '#FEF2F2', border: '1px solid #FECACA' }}>
              <div className="flex items-start">
                <svg className="h-5 w-5 text-red-500 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <div className="flex-1">
                  <p className="text-sm text-red-800 whitespace-pre-wrap break-words">{error}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Diagram Display */}
        {diagramUrl && (
          <div className="bg-white rounded-2xl shadow-xl p-6 sm:p-8">
            <h2 className="text-2xl font-semibold mb-6" style={{ color: '#9C83C9' }}>
              Generated Architecture Diagram
            </h2>
            <div className="flex flex-col items-center">
              <div className="w-full mb-6 rounded-xl overflow-hidden shadow-lg border-2" style={{ borderColor: '#9C83C9' }}>
                <img
                  src={diagramUrl}
                  alt="Generated Architecture Diagram"
                  className="w-full h-auto"
                />
              </div>
              <a
                href={diagramUrl}
                download="architecture-diagram.png"
                className="inline-flex items-center px-6 py-3 rounded-lg font-semibold text-white transition-all duration-200 hover:shadow-lg hover:scale-105 active:scale-95"
                style={{ backgroundColor: '#9C83C9' }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#8B72B8'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = '#9C83C9'
                }}
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download Diagram
              </a>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
