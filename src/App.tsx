import { useState } from 'react'
import { VersionSelector, type Version } from './components/VersionSelector'
import { ProcessLog } from './components/ProcessLog'
import { PagePreview } from './components/PagePreview'
import { TabNavigation } from './components/TabNavigation'
import { EvaluationDashboard } from './components/EvaluationDashboard'
import { ComparisonView } from './components/ComparisonView'

interface ProcessLogEntry {
  step: string
  status: string
  details?: string
}

interface RobustnessDisplay {
  icon: string
  label: string
  color: string
  description: string
}

interface GenerateResponse {
  xpath: string
  version: string
  validated: boolean
  match_count: number
  element_info: string | null
  process_log?: ProcessLogEntry[]
  robustness_display?: RobustnessDisplay
}

interface ComparisonData {
  v1: GenerateResponse
  v2: GenerateResponse
  v3: GenerateResponse
  execution_times: Record<string, number>
  summary: {
    all_xpaths_same: boolean
    unique_xpaths: number
    validated_count: number
    fastest_version: string
    slowest_version: string
    total_time: number
    xpath_differences?: Record<string, boolean>
    validation_agreement: boolean
  }
}

function App() {
  const [activeTab, setActiveTab] = useState<'generator' | 'evaluation'>('generator')
  const [url, setUrl] = useState('')
  const [instruction, setInstruction] = useState('')
  const [result, setResult] = useState<GenerateResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [selectedVersion, setSelectedVersion] = useState<Version>('v1')
  const [comparisonMode, setComparisonMode] = useState(false)
  const [comparisonData, setComparisonData] = useState<ComparisonData | null>(null)
  const [isComparingLoading, setIsComparingLoading] = useState(false)

  const handleGenerateXPath = async () => {
    if (comparisonMode) {
      setIsComparingLoading(true)
      setError(null)
      setComparisonData(null)
      setResult(null)

      try {
        const response = await fetch('http://localhost:8000/api/compare', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            url,
            instruction
          }),
        })

        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
        }

        const data: ComparisonData = await response.json()
        setComparisonData(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unexpected error occurred')
      } finally {
        setIsComparingLoading(false)
      }
    } else {
      setIsLoading(true)
      setError(null)
      setResult(null)
      setComparisonData(null)

      try {
        const response = await fetch('http://localhost:8000/api/generate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            url,
            instruction,
            version: selectedVersion
          }),
        })

        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
        }

        const data: GenerateResponse = await response.json()
        setResult(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unexpected error occurred')
      } finally {
        setIsLoading(false)
      }
    }
  }

  const handleCopyToClipboard = () => {
    if (result?.xpath) {
      navigator.clipboard.writeText(result.xpath)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleClear = () => {
    setUrl('')
    setInstruction('')
    setResult(null)
    setComparisonData(null)
    setError(null)
  }

  const getValidationStatus = () => {
    if (!result) return null
    if (result.validated && result.match_count > 0) {
      return {
        badge: '✅ Valid',
        color: 'green',
        bgColor: 'bg-green-50',
        borderColor: 'border-green-200',
        textColor: 'text-green-600'
      }
    } else if (result.validated && result.match_count === 0) {
      return {
        badge: '❌ Invalid',
        color: 'red',
        bgColor: 'bg-red-50',
        borderColor: 'border-red-200',
        textColor: 'text-red-600'
      }
    } else {
      return {
        badge: '⚠️ Unvalidated',
        color: 'yellow',
        bgColor: 'bg-yellow-50',
        borderColor: 'border-yellow-200',
        textColor: 'text-yellow-600'
      }
    }
  }

  const validationStatus = getValidationStatus()
  const showProcessLog = result?.process_log && result.process_log.length > 0 && (selectedVersion === 'v2' || selectedVersion === 'v3')
  const isLoadingAny = isLoading || isComparingLoading

  const renderGeneratorTab = () => (
    <div className="flex-1 flex overflow-hidden">
      <div className="w-2/5 bg-white border-r border-gray-200 p-6 flex flex-col space-y-6 overflow-y-auto">
        {/* Comparison Mode Toggle */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-blue-900">Compare All Versions</h3>
              <p className="text-xs text-blue-700 mt-1">Run V1, V2, and V3 side-by-side</p>
            </div>
            <button
              onClick={() => setComparisonMode(!comparisonMode)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${
                comparisonMode ? 'bg-blue-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
                  comparisonMode ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>

        {!comparisonMode && (
          <VersionSelector
            selectedVersion={selectedVersion}
            onVersionChange={setSelectedVersion}
          />
        )}

        <div className="space-y-2">
          <label htmlFor="url" className="block text-sm font-medium text-gray-700">
            Target URL
          </label>
          <input
            id="url"
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="instruction" className="block text-sm font-medium text-gray-700">
            Instruction
          </label>
          <textarea
            id="instruction"
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            placeholder="e.g., Click on 'About Us'"
            rows={4}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition resize-none"
          />
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleGenerateXPath}
            disabled={!url || !instruction || isLoadingAny}
            className="flex-1 bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition shadow-sm"
          >
            {isLoadingAny ? (
              comparisonMode ? 'Comparing...' : 'Generating...'
            ) : (
              comparisonMode ? 'Compare All Versions' : 'Generate XPath'
            )}
          </button>
          <button
            onClick={handleClear}
            className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg font-medium hover:bg-gray-300 transition shadow-sm"
          >
            Clear
          </button>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">
              <span className="font-medium">Error:</span> {error}
            </p>
          </div>
        )}

        {result && validationStatus && !comparisonMode && (
          <div className={`space-y-3 p-4 rounded-lg border ${validationStatus.bgColor} ${validationStatus.borderColor}`}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-3">
                <h3 className="text-sm font-medium text-gray-700">Generated XPath</h3>
                <span className={`text-xs font-medium px-2 py-1 rounded ${validationStatus.textColor}`}>
                  {validationStatus.badge}
                </span>
              </div>
              <button
                onClick={handleCopyToClipboard}
                className="text-sm bg-gray-200 hover:bg-gray-300 px-3 py-1 rounded-md transition flex items-center gap-1"
              >
                {copied ? (
                  <>
                    <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Copied!
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    Copy
                  </>
                )}
              </button>
            </div>

            <div className="bg-white p-3 rounded-md border border-gray-200">
              <code className="text-sm text-gray-800 font-mono break-all">
                {result.xpath}
              </code>
            </div>

            <div className="space-y-1 text-sm">
              {result.validated && result.match_count >= 0 && (
                <div className="text-gray-600">
                  <span className="font-medium">Matches:</span> {result.match_count} element{result.match_count !== 1 ? 's' : ''}
                </div>
              )}
              {result.element_info && (
                <div className="text-gray-600">
                  <span className="font-medium">Element:</span> {result.element_info}
                </div>
              )}
              {result.robustness_display && selectedVersion === 'v3' && (
                <div className="text-gray-600 flex items-center gap-2">
                  <span className="font-medium">Robustness:</span>
                  <span className="text-lg">{result.robustness_display.icon}</span>
                  <span className={`font-medium ${
                    result.robustness_display.color === 'green' ? 'text-green-600' :
                    result.robustness_display.color === 'yellow' ? 'text-yellow-600' :
                    result.robustness_display.color === 'red' ? 'text-red-600' : 'text-gray-600'
                  }`}>
                    {result.robustness_display.label}
                  </span>
                  <span className="text-xs text-gray-500">
                    {result.robustness_display.description}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {showProcessLog && !comparisonMode && (
          <ProcessLog entries={result.process_log || []} />
        )}

        {comparisonMode && (
          <div className="mt-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Comparison Mode</h3>
            <p className="text-xs text-gray-500">
              Results will show side-by-side comparison of V1 (MVP), V2 (Validated), and V3 (Enterprise) approaches with timing and difference analysis.
            </p>
          </div>
        )}
      </div>

      {comparisonMode ? (
        <div className="w-3/5 bg-gray-100 p-4">
          <div className="h-full bg-white rounded-lg shadow-sm overflow-hidden">
            <ComparisonView
              comparisonData={comparisonData}
              isLoading={isComparingLoading}
            />
          </div>
        </div>
      ) : (
        <div className="w-3/5 bg-gray-100 p-4">
          <div className="h-full bg-white rounded-lg shadow-sm overflow-hidden">
            <PagePreview
              url={url}
              xpath={result?.xpath}
              validated={result?.validated}
            />
          </div>
        </div>
      )}
    </div>
  )

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-800">
          ⛈️ Storms
        </h1>
      </header>

      <TabNavigation
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      {activeTab === 'generator' ? renderGeneratorTab() : <EvaluationDashboard />}
    </div>
  )
}

export default App