import { useState, useRef } from 'react'
import { Link } from 'react-router-dom'

interface ProgressEvent {
  message: string
  status: 'info' | 'success' | 'error' | 'warning' | 'complete'
  progress?: number
  timestamp?: string
  image_data?: string
  filename?: string
  file_size?: number
  s3_url?: string
  request_id?: string
}

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [generatingSummary, setGeneratingSummary] = useState(false)
  const [summaryText, setSummaryText] = useState<string>('')
  const [diagramPrompt, setDiagramPrompt] = useState<string>('')
  const [showSummaryEditor, setShowSummaryEditor] = useState(false)
  const [diagramUrl, setDiagramUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [progressMessages, setProgressMessages] = useState<ProgressEvent[]>([])
  const [progressPercent, setProgressPercent] = useState(0)
  const [awsRegion, setAwsRegion] = useState('us-east-1')
  const [bedrockModelId, setBedrockModelId] = useState('arn:aws:bedrock:us-east-1:302263040839:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0')
  const eventSourceRef = useRef<EventSource | null>(null)

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

  const handleGenerateSummary = async () => {
    if (!selectedFile) {
      setError('Please select a PDF file first')
      return
    }

    setGeneratingSummary(true)
    setError(null)
    setSummaryText('')
    setShowSummaryEditor(false)

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('aws_region', awsRegion)
      formData.append('bedrock_model_id', bedrockModelId)

      const response = await fetch('http://localhost:8000/api/generate-summary', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      if (data.success && data.summary) {
        setSummaryText(data.summary)
        // Generate detailed structured prompt template emphasizing HORIZONTAL LANDSCAPE
        // Note: {readable_summary} is a PLACEHOLDER that will be replaced by the backend
        const defaultPrompt = `=== CRITICAL: HORIZONTAL LANDSCAPE LAYOUT (16:9) ===
YOU MUST CREATE A HORIZONTAL LANDSCAPE DIAGRAM.
- Canvas: 3840 pixels WIDE × 2160 pixels TALL (16:9 aspect ratio)
- Orientation: LANDSCAPE (wider than tall)
- Flow: LEFT-TO-RIGHT (not top-to-bottom)
- Graphviz rankdir: LR (if using DOT format)

Create a comprehensive AWS architecture diagram based on the following summary.

ARCHITECTURE SUMMARY:
{readable_summary}

HORIZONTAL COLUMN LAYOUT (LEFT → RIGHT):
┌─────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
│  COLUMN 1   │  COLUMN 2   │  COLUMN 3   │  COLUMN 4   │  COLUMN 5   │
│  (LEFT)     │             │  (CENTER)   │             │  (RIGHT)    │
├─────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ External &  │ Ingestion & │ Processing  │ Storage &   │ Monitoring  │
│ Sources     │ Events      │ & Compute   │ Security    │ & Output    │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘

COLUMN 1 - EXTERNAL & INGESTION (20% width):
   - External users, data sources
   - Email/API ingestion
   - S3 Input Buckets

COLUMN 2 - EVENTS & ROUTING (20% width):
   - S3 Events, Lambda triggers
   - EventBridge, SQS, SNS

COLUMN 3 - CORE PROCESSING (30% width):
   - Lambda/EC2/ECS/EKS
   - SageMaker, AI/ML services
   - Batch jobs

COLUMN 4 - DATA & SECURITY (20% width):
   - S3 Output, DynamoDB, RDS
   - ECR, KMS, Secrets Manager
   - IAM Roles

COLUMN 5 - MONITORING & INTEGRATION (10% width):
   - CloudWatch, X-Ray
   - External APIs
   - Notifications

STYLING REQUIREMENTS:
- NO COLORS: Grayscale/Black-White ONLY
- White background, black borders
- AWS icons in grayscale

LAYOUT REQUIREMENTS (MANDATORY):
1. HORIZONTAL LANDSCAPE: Width > Height
2. ASPECT RATIO: 16:9 (3840×2160 or 1920×1080)
3. FLOW: LEFT → RIGHT
4. GRAPHVIZ RANKDIR: LR (if using DOT)
5. NO VERTICAL STACKING

FORBIDDEN:
❌ NO vertical flow (top-to-bottom)
❌ NO portrait orientation
❌ NO colors`
        setDiagramPrompt(defaultPrompt)
        setShowSummaryEditor(true)
      } else {
        throw new Error('Failed to generate summary')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred while generating summary')
      console.error('Summary generation error:', err)
    } finally {
      setGeneratingSummary(false)
    }
  }

  const handleApproveAndGenerate = async () => {
    if (!summaryText.trim()) {
      setError('Summary text cannot be empty')
      return
    }

    // Close any existing EventSource
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    setUploading(true)
    setError(null)
    setDiagramUrl(null)
    setProgressMessages([])
    setProgressPercent(0)

    try {
      const formData = new FormData()
      formData.append('summary_text', summaryText)
      formData.append('diagram_prompt', diagramPrompt)
      formData.append('aws_region', awsRegion)
      formData.append('bedrock_model_id', bedrockModelId)

      const response = await fetch('http://localhost:8000/api/generate-diagram-from-summary', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      // Handle Server-Sent Events
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error('Response body is not readable')
      }

      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data: ProgressEvent = JSON.parse(line.slice(6))
              
              setProgressMessages(prev => [...prev, data])
              
              if (data.progress !== undefined) {
                setProgressPercent(data.progress)
              }

              // Handle completion
              if (data.status === 'complete' && data.image_data) {
                // Convert base64 to blob URL
                const binaryString = atob(data.image_data)
                const bytes = new Uint8Array(binaryString.length)
                for (let i = 0; i < binaryString.length; i++) {
                  bytes[i] = binaryString.charCodeAt(i)
                }
                const blob = new Blob([bytes], { type: 'image/png' })
                const url = URL.createObjectURL(blob)
                
                // Revoke old URL
                if (diagramUrl) {
                  URL.revokeObjectURL(diagramUrl)
                }
                
                setDiagramUrl(url)
                setError(null)
                setUploading(false)
              }

              // Handle errors
              if (data.status === 'error') {
                setError(data.message)
                setUploading(false)
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e)
            }
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred while processing the PDF')
      console.error('Upload error:', err)
      setUploading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: '#F9F8FC' }}>
      {/* Header */}
      <header className="bg-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex justify-between items-center">
            <div className="text-center flex-1">
              <h1 className="text-4xl font-bold mb-2" style={{ color: '#9C83C9' }}>
                Architecture Diagram Generator
              </h1>
              <p className="text-gray-600 text-lg">
                Upload a SOW PDF to generate an architecture diagram
              </p>
            </div>
            <Link
              to="/gallery"
              className="px-6 py-3 rounded-lg font-semibold text-white transition-all duration-200 hover:shadow-lg whitespace-nowrap"
              style={{ backgroundColor: '#9C83C9' }}
            >
              View Gallery →
            </Link>
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
            <label htmlFor="aws-region" className="block text-sm font-medium text-gray-700 mb-2" style={{ display: 'none' }}>
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
              style={{ display: 'none' }}
            />
          </div>

          {/* Bedrock Model ID Input */}
          <div className="mb-6">
            <label htmlFor="bedrock-model" className="block text-sm font-medium text-gray-700 mb-2" style={{ display: 'none' }}>
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
              style={{ display: 'none' }}
            />
          </div>

          {/* Generate Summary Button */}
          {!showSummaryEditor && (
            <button
              onClick={handleGenerateSummary}
              disabled={!selectedFile || generatingSummary || uploading}
              className="w-full py-4 px-6 rounded-lg font-semibold text-white text-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-lg hover:scale-[1.02] active:scale-[0.98] mb-4"
              style={{ 
                backgroundColor: '#9C83C9',
              }}
              onMouseEnter={(e) => {
                if (!generatingSummary && selectedFile) {
                  e.currentTarget.style.backgroundColor = '#8B72B8'
                }
              }}
              onMouseLeave={(e) => {
                if (!generatingSummary && selectedFile) {
                  e.currentTarget.style.backgroundColor = '#9C83C9'
                }
              }}
            >
              {generatingSummary ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Generating Summary...
                </span>
              ) : (
                'Generate Summary'
              )}
            </button>
          )}

          {/* Summary Editor */}
          {showSummaryEditor && (
            <>
              <div className="mb-6 p-4 rounded-xl border-2" style={{ borderColor: '#9C83C9', backgroundColor: '#F9F8FC' }}>
                <h3 className="text-lg font-semibold mb-3" style={{ color: '#9C83C9' }}>
                  Architecture Summary (Edit if needed)
                </h3>
                <textarea
                  value={summaryText}
                  onChange={(e) => setSummaryText(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#9C83C9] focus:border-[#9C83C9] outline-none transition-all resize-y font-mono text-sm"
                  rows={12}
                  placeholder="Architecture summary will appear here..."
                  disabled={uploading}
                />
              </div>

              <div className="mb-6 p-4 rounded-xl border-2" style={{ borderColor: '#9C83C9', backgroundColor: '#F9F8FC' }}>
                <h3 className="text-lg font-semibold mb-3" style={{ color: '#9C83C9' }}>
                  Prompt for Diagram Generation (Edit if needed)
                </h3>
                <textarea
                  value={diagramPrompt}
                  onChange={(e) => setDiagramPrompt(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#9C83C9] focus:border-[#9C83C9] outline-none transition-all resize-y font-mono text-sm"
                  rows={20}
                  placeholder="Diagram generation prompt will appear here..."
                  disabled={uploading}
                />
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3">
                <button
                  onClick={handleApproveAndGenerate}
                  disabled={!summaryText.trim() || !diagramPrompt.trim() || uploading}
                  className="flex-1 py-3 px-6 rounded-lg font-semibold text-white transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-lg hover:scale-[1.02] active:scale-[0.98]"
                  style={{ 
                    backgroundColor: '#9C83C9',
                  }}
                  onMouseEnter={(e) => {
                    if (!uploading && summaryText.trim() && diagramPrompt.trim()) {
                      e.currentTarget.style.backgroundColor = '#8B72B8'
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!uploading && summaryText.trim() && diagramPrompt.trim()) {
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
                      Generating... {progressPercent}%
                    </span>
                  ) : (
                    'Approve & Generate Diagram'
                  )}
                </button>
                <button
                  onClick={() => {
                    setShowSummaryEditor(false)
                    setSummaryText('')
                    setDiagramPrompt('')
                  }}
                  disabled={uploading}
                  className="px-6 py-3 rounded-lg font-semibold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-lg"
                  style={{ 
                    backgroundColor: '#E5E7EB',
                    color: '#374151',
                  }}
                >
                  Cancel
                </button>
              </div>
            </>
          )}

          {/* Progress Bar */}
          {uploading && progressPercent > 0 && (
            <div className="mt-4">
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div
                  className="h-2.5 rounded-full transition-all duration-300"
                  style={{
                    width: `${progressPercent}%`,
                    backgroundColor: '#9C83C9'
                  }}
                ></div>
              </div>
            </div>
          )}

          {/* Progress Messages */}
          {uploading && progressMessages.length > 0 && (
            <div className="mt-6 max-h-64 overflow-y-auto space-y-2">
              {progressMessages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg text-sm flex items-start ${
                    msg.status === 'success' ? 'bg-green-50 text-green-800 border border-green-200' :
                    msg.status === 'error' ? 'bg-red-50 text-red-800 border border-red-200' :
                    msg.status === 'warning' ? 'bg-yellow-50 text-yellow-800 border border-yellow-200' :
                    'bg-blue-50 text-blue-800 border border-blue-200'
                  }`}
                >
                  <span className="mr-2">
                    {msg.status === 'success' ? '✓' :
                     msg.status === 'error' ? '❌' :
                     msg.status === 'warning' ? '⚠️' :
                     'ℹ️'}
                  </span>
                  <span className="flex-1">{msg.message}</span>
                </div>
              ))}
            </div>
          )}

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
