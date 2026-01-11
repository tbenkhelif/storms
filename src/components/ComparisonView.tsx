import { useState } from 'react'

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

interface GenerateResult {
  xpath: string
  version: string
  validated: boolean
  match_count: number
  element_info: string | null
  process_log?: ProcessLogEntry[]
  robustness_display?: RobustnessDisplay
}

interface ComparisonData {
  v1: GenerateResult
  v2: GenerateResult
  v3: GenerateResult
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

interface ComparisonViewProps {
  comparisonData: ComparisonData | null
  isLoading: boolean
}

export function ComparisonView({ comparisonData, isLoading }: ComparisonViewProps) {
  const [expandedVersions, setExpandedVersions] = useState<Set<string>>(new Set())
  const [copiedVersion, setCopiedVersion] = useState<string | null>(null)

  const toggleExpanded = (version: string) => {
    setExpandedVersions(prev => {
      const newSet = new Set(prev)
      if (newSet.has(version)) {
        newSet.delete(version)
      } else {
        newSet.add(version)
      }
      return newSet
    })
  }

  const copyToClipboard = async (xpath: string, version: string) => {
    // Wrap XPath in $x() for easy console testing
    const consoleReadyXPath = `$x("${xpath}")`
    await navigator.clipboard.writeText(consoleReadyXPath)
    setCopiedVersion(version)
    setTimeout(() => setCopiedVersion(null), 2000)
  }

  const getVersionInfo = (version: string) => {
    const info = {
      v1: { name: 'MVP', icon: '⚡', description: 'Direct LLM call' },
      v2: { name: 'Validated', icon: '🔍', description: 'Heuristics + validation' },
      v3: { name: 'Enterprise', icon: '🧠', description: 'Claude tool use + robustness' }
    }
    return info[version as keyof typeof info]
  }

  const getValidationStatus = (result: GenerateResult) => {
    if (!result.validated) {
      return { badge: '❓ Unvalidated', color: 'text-yellow-600', bgColor: 'bg-yellow-50' }
    } else if (result.match_count === 0) {
      return { badge: '❌ Invalid', color: 'text-red-600', bgColor: 'bg-red-50' }
    } else {
      return { badge: `✅ Valid (${result.match_count})`, color: 'text-green-600', bgColor: 'bg-green-50' }
    }
  }

  const getXPathDifference = (currentXPath: string, allXPaths: string[]) => {
    const uniqueXPaths = [...new Set(allXPaths)]
    if (uniqueXPaths.length === 1) {
      return 'same' // All XPaths are the same
    }

    const otherXPaths = allXPaths.filter(xpath => xpath !== currentXPath)
    if (otherXPaths.some(xpath => xpath === currentXPath)) {
      return 'partial' // Some other version has same XPath
    }
    return 'unique' // This XPath is unique
  }

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-center space-x-2">
          <svg className="w-6 h-6 animate-spin text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span className="text-lg font-medium text-gray-700">Comparing all versions...</span>
        </div>
        <div className="mt-4 text-sm text-gray-500 text-center">
          Running V1, V2, and V3 in parallel
        </div>
      </div>
    )
  }

  if (!comparisonData) {
    return (
      <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500">
        <svg className="w-12 h-12 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <p>Enable "Compare All Versions" and generate an XPath to see side-by-side comparison</p>
      </div>
    )
  }

  const allXPaths = [comparisonData.v1.xpath, comparisonData.v2.xpath, comparisonData.v3.xpath]
  const results = [comparisonData.v1, comparisonData.v2, comparisonData.v3]

  return (
    <div className="space-y-6">
      {/* Summary Card */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
          <span>📊</span>
          Comparison Summary
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Unique XPaths:</span>
            <span className={`ml-2 font-medium ${comparisonData.summary.unique_xpaths === 1 ? 'text-green-600' : 'text-yellow-600'}`}>
              {comparisonData.summary.unique_xpaths}
            </span>
          </div>
          <div>
            <span className="text-gray-500">Validated:</span>
            <span className="ml-2 font-medium text-blue-600">
              {comparisonData.summary.validated_count}/3
            </span>
          </div>
          <div>
            <span className="text-gray-500">Fastest:</span>
            <span className="ml-2 font-medium text-green-600">
              {comparisonData.summary.fastest_version.toUpperCase()}
              ({comparisonData.execution_times[comparisonData.summary.fastest_version].toFixed(2)}s)
            </span>
          </div>
          <div>
            <span className="text-gray-500">Total Time:</span>
            <span className="ml-2 font-medium text-gray-700">
              {comparisonData.summary.total_time.toFixed(2)}s
            </span>
          </div>
        </div>

        {/* Insights */}
        <div className="mt-3 pt-3 border-t border-gray-200">
          <div className="flex flex-wrap gap-2">
            {comparisonData.summary.all_xpaths_same && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                ✅ All versions agree
              </span>
            )}
            {!comparisonData.summary.validation_agreement && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                ⚠️ Validation differs
              </span>
            )}
            {comparisonData.summary.unique_xpaths > 1 && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                📝 Different approaches
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Three-column comparison */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {results.map((result) => {
          const versionInfo = getVersionInfo(result.version)
          const validationStatus = getValidationStatus(result)
          const xpathDifference = getXPathDifference(result.xpath, allXPaths)
          const executionTime = comparisonData.execution_times[result.version]
          const isExpanded = expandedVersions.has(result.version)
          const isCopied = copiedVersion === result.version

          return (
            <div key={result.version} className="bg-white rounded-lg shadow border">
              {/* Header */}
              <div className="p-4 border-b border-gray-200">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{versionInfo?.icon}</span>
                    <span className="font-semibold text-gray-900">
                      {result.version.toUpperCase()} ({versionInfo?.name})
                    </span>
                  </div>
                  <span className={`text-sm font-medium px-2 py-1 rounded ${
                    result.version === comparisonData.summary.fastest_version
                      ? 'bg-green-100 text-green-800'
                      : result.version === comparisonData.summary.slowest_version
                      ? 'bg-red-100 text-red-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}>
                    ⏱️ {executionTime.toFixed(2)}s
                  </span>
                </div>
                <p className="text-xs text-gray-500">{versionInfo?.description}</p>
              </div>

              {/* XPath Display */}
              <div className="p-4">
                <div className="mb-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700">Generated XPath</span>
                    <button
                      onClick={() => copyToClipboard(result.xpath, result.version)}
                      className="text-xs bg-gray-100 hover:bg-gray-200 px-2 py-1 rounded transition flex items-center gap-1"
                    >
                      {isCopied ? (
                        <>
                          <svg className="w-3 h-3 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          Copied
                        </>
                      ) : (
                        <>
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                          Copy
                        </>
                      )}
                    </button>
                  </div>

                  <div className={`p-3 rounded border ${
                    xpathDifference === 'same' ? 'border-green-200 bg-green-50' :
                    xpathDifference === 'partial' ? 'border-yellow-200 bg-yellow-50' :
                    'border-blue-200 bg-blue-50'
                  }`}>
                    <code className="text-sm font-mono break-all text-gray-800">
                      {result.xpath}
                    </code>
                    {xpathDifference === 'unique' && (
                      <div className="mt-2 text-xs text-blue-700">
                        🔵 Unique approach
                      </div>
                    )}
                    {xpathDifference === 'partial' && (
                      <div className="mt-2 text-xs text-yellow-700">
                        🟡 Matches other version(s)
                      </div>
                    )}
                  </div>
                </div>

                {/* Status and Info */}
                <div className="space-y-2">
                  <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${validationStatus.bgColor} ${validationStatus.color}`}>
                    {validationStatus.badge}
                  </div>

                  {result.element_info && (
                    <div className="text-sm text-gray-600">
                      <span className="font-medium">Element:</span> {result.element_info}
                    </div>
                  )}

                  {/* V3 Robustness */}
                  {result.robustness_display && (
                    <div className="text-sm text-gray-600 flex items-center gap-2">
                      <span className="font-medium">Robustness:</span>
                      <span className="text-lg">{result.robustness_display.icon}</span>
                      <span className={`font-medium ${
                        result.robustness_display.color === 'green' ? 'text-green-600' :
                        result.robustness_display.color === 'yellow' ? 'text-yellow-600' :
                        result.robustness_display.color === 'red' ? 'text-red-600' : 'text-gray-600'
                      }`}>
                        {result.robustness_display.label}
                      </span>
                    </div>
                  )}
                </div>

                {/* Process Log Toggle */}
                {result.process_log && result.process_log.length > 0 && (
                  <button
                    onClick={() => toggleExpanded(result.version)}
                    className="mt-3 text-xs text-blue-600 hover:text-blue-800 transition flex items-center gap-1"
                  >
                    <svg className={`w-3 h-3 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                         fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                    {isExpanded ? 'Hide' : 'Show'} process log ({result.process_log.length} steps)
                  </button>
                )}

                {/* Expanded Process Log */}
                {isExpanded && result.process_log && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <div className="space-y-1 max-h-32 overflow-y-auto">
                      {result.process_log.slice(-5).map((entry, index) => (
                        <div key={index} className="text-xs flex items-center gap-2">
                          <span className={`w-2 h-2 rounded-full ${
                            entry.status === 'success' ? 'bg-green-500' :
                            entry.status === 'failed' || entry.status === 'error' ? 'bg-red-500' :
                            'bg-yellow-500'
                          }`} />
                          <span className="font-medium">{entry.step}:</span>
                          <span className="text-gray-600">{entry.status}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}