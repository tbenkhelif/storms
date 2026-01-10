import { useState, useEffect } from 'react'

interface EvaluationResult {
  test_id: string
  category: string
  url: string
  instruction: string
  version: string
  generated_xpath: string | null
  validated: boolean
  match_count: number
  element_info: string | null
  success: boolean
  error_message: string | null
  execution_time: number
}

interface EvaluationMetrics {
  total_tests: number
  successful: number
  success_rate: number
  average_time: number
  p95_time: number
  validated_xpaths: number
}

interface EvaluationData {
  version: string
  metrics: EvaluationMetrics
  results: EvaluationResult[]
  timestamp: string
}

interface CategoryStats {
  category: string
  total: number
  successful: number
  success_rate: number
}

export function EvaluationDashboard() {
  const [selectedVersions, setSelectedVersions] = useState<string[]>(['v1'])
  const [isRunning, setIsRunning] = useState(false)
  const [progress, setProgress] = useState(0)
  const [evaluationData, setEvaluationData] = useState<EvaluationData[]>([])
  const [expandedFailures, setExpandedFailures] = useState<Set<string>>(new Set())
  const [error, setError] = useState<string | null>(null)

  const availableVersions = [
    { id: 'v1', name: 'V1 (MVP)', description: 'Direct LLM call' },
    { id: 'v2', name: 'V2 (Validated)', description: 'Heuristics + validation' },
    { id: 'v3', name: 'V3 (Enterprise)', description: 'Agentic approach (coming soon)', disabled: true }
  ]

  useEffect(() => {
    const savedData = localStorage.getItem('storms-evaluation-results')
    if (savedData) {
      try {
        setEvaluationData(JSON.parse(savedData))
      } catch (e) {
        console.error('Failed to parse saved evaluation data:', e)
      }
    }
  }, [])

  const saveResults = (data: EvaluationData[]) => {
    localStorage.setItem('storms-evaluation-results', JSON.stringify(data))
    setEvaluationData(data)
  }

  const runEvaluation = async () => {
    if (selectedVersions.length === 0) {
      setError('Please select at least one version to evaluate')
      return
    }

    setIsRunning(true)
    setProgress(0)
    setError(null)

    try {
      const newResults: EvaluationData[] = []

      for (let i = 0; i < selectedVersions.length; i++) {
        const version = selectedVersions[i]
        setProgress((i / selectedVersions.length) * 50)

        const response = await fetch('http://localhost:8000/api/evaluate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ version })
        })

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          throw new Error(errorData.detail || `HTTP ${response.status}`)
        }

        const data = await response.json()
        newResults.push({
          version,
          metrics: data.metrics,
          results: data.results,
          timestamp: new Date().toISOString()
        })

        setProgress(((i + 1) / selectedVersions.length) * 100)
      }

      const updatedData = [
        ...evaluationData.filter(d => !selectedVersions.includes(d.version)),
        ...newResults
      ]

      saveResults(updatedData)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Evaluation failed')
    } finally {
      setIsRunning(false)
      setProgress(0)
    }
  }

  const toggleVersionSelection = (version: string) => {
    setSelectedVersions(prev =>
      prev.includes(version)
        ? prev.filter(v => v !== version)
        : [...prev, version]
    )
  }

  const getCategoryStats = (): CategoryStats[] => {
    if (evaluationData.length === 0) return []

    const categories = ['simple', 'contextual', 'ambiguous', 'complex']
    const stats: CategoryStats[] = []

    for (const category of categories) {
      const allResults = evaluationData.flatMap(d => d.results)
      const categoryResults = allResults.filter(r => r.category === category)

      if (categoryResults.length > 0) {
        stats.push({
          category,
          total: categoryResults.length,
          successful: categoryResults.filter(r => r.success).length,
          success_rate: categoryResults.filter(r => r.success).length / categoryResults.length
        })
      }
    }

    return stats
  }

  const getFailedCases = (): EvaluationResult[] => {
    return evaluationData
      .flatMap(d => d.results)
      .filter(r => !r.success)
      .sort((a, b) => a.test_id.localeCompare(b.test_id))
  }

  const toggleFailureExpansion = (testId: string) => {
    setExpandedFailures(prev => {
      const newSet = new Set(prev)
      if (newSet.has(testId)) {
        newSet.delete(testId)
      } else {
        newSet.add(testId)
      }
      return newSet
    })
  }

  const formatLatency = (seconds: number) => `${seconds.toFixed(2)}s`
  const formatPercentage = (rate: number) => `${(rate * 100).toFixed(1)}%`

  return (
    <div className="p-6 space-y-8 bg-gray-50 min-h-full">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Evaluation Dashboard</h2>
        <p className="text-gray-600 mt-1">
          Test XPath generation performance across different versions and categories
        </p>
      </div>

      {/* Run Evaluation Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Run Evaluation</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Versions to Evaluate
            </label>
            <div className="space-y-2">
              {availableVersions.map(version => (
                <label key={version.id} className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={selectedVersions.includes(version.id)}
                    onChange={() => toggleVersionSelection(version.id)}
                    disabled={version.disabled || isRunning}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
                  />
                  <div className="flex-1">
                    <span className="font-medium text-gray-900">{version.name}</span>
                    <span className="text-sm text-gray-500 ml-2">{version.description}</span>
                    {version.disabled && (
                      <span className="text-xs text-yellow-600 ml-2">(Not Available)</span>
                    )}
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={runEvaluation}
              disabled={isRunning || selectedVersions.length === 0}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition flex items-center gap-2"
            >
              {isRunning ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Running...
                </>
              ) : (
                'Run All Tests'
              )}
            </button>

            {selectedVersions.length > 0 && (
              <span className="text-sm text-gray-600">
                Will test {selectedVersions.length} version{selectedVersions.length !== 1 ? 's' : ''} against 18 test cases
              </span>
            )}
          </div>

          {isRunning && (
            <div className="mt-4">
              <div className="flex justify-between text-sm text-gray-600 mb-1">
                <span>Progress</span>
                <span>{progress.toFixed(0)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">
                <span className="font-medium">Error:</span> {error}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Results Summary */}
      {evaluationData.length > 0 && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="p-6 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Results Summary</h3>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Version
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Accuracy
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Avg Latency
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    P95 Latency
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Valid XPaths
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Last Run
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {evaluationData.map((data) => (
                  <tr key={data.version}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="font-medium text-gray-900">{data.version.toUpperCase()}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`font-medium ${
                        data.metrics.success_rate >= 0.8 ? 'text-green-600' :
                        data.metrics.success_rate >= 0.6 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {formatPercentage(data.metrics.success_rate)}
                      </span>
                      <span className="text-gray-500 ml-1 text-sm">
                        ({data.metrics.successful}/{data.metrics.total_tests})
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-900">
                      {formatLatency(data.metrics.average_time)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-900">
                      {formatLatency(data.metrics.p95_time)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-900">
                      {data.metrics.validated_xpaths}/{data.metrics.total_tests}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500 text-sm">
                      {new Date(data.timestamp).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Category Breakdown */}
      {evaluationData.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Category Breakdown</h3>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 font-medium text-gray-700">Category</th>
                  <th className="text-left py-2 font-medium text-gray-700">Success Rate</th>
                  <th className="text-left py-2 font-medium text-gray-700">Tests</th>
                  <th className="text-left py-2 font-medium text-gray-700">Visual</th>
                </tr>
              </thead>
              <tbody className="space-y-2">
                {getCategoryStats().map((stat) => (
                  <tr key={stat.category} className="border-b border-gray-100">
                    <td className="py-3 font-medium text-gray-900 capitalize">
                      {stat.category}
                    </td>
                    <td className="py-3">
                      <span className={`font-medium ${
                        stat.success_rate >= 0.8 ? 'text-green-600' :
                        stat.success_rate >= 0.6 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {formatPercentage(stat.success_rate)}
                      </span>
                    </td>
                    <td className="py-3 text-gray-600">
                      {stat.successful}/{stat.total}
                    </td>
                    <td className="py-3">
                      <div className="w-32 bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            stat.success_rate >= 0.8 ? 'bg-green-500' :
                            stat.success_rate >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${stat.success_rate * 100}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Failed Cases */}
      {getFailedCases().length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Failed Test Cases ({getFailedCases().length})
          </h3>

          <div className="space-y-3">
            {getFailedCases().map((result) => (
              <div key={`${result.version}-${result.test_id}`} className="border border-gray-200 rounded-lg">
                <button
                  onClick={() => toggleFailureExpansion(`${result.version}-${result.test_id}`)}
                  className="w-full p-4 text-left hover:bg-gray-50 transition-colors flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-red-600">❌</span>
                    <div>
                      <span className="font-medium text-gray-900">
                        {result.test_id} ({result.version.toUpperCase()})
                      </span>
                      <p className="text-sm text-gray-600 mt-1">
                        {result.instruction}
                      </p>
                    </div>
                  </div>
                  <svg
                    className={`w-5 h-5 text-gray-400 transform transition-transform ${
                      expandedFailures.has(`${result.version}-${result.test_id}`) ? 'rotate-180' : ''
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {expandedFailures.has(`${result.version}-${result.test_id}`) && (
                  <div className="border-t border-gray-200 p-4 bg-gray-50 space-y-3">
                    <div>
                      <span className="text-sm font-medium text-gray-700">URL:</span>
                      <p className="text-sm text-gray-600 break-all">{result.url}</p>
                    </div>

                    <div>
                      <span className="text-sm font-medium text-gray-700">Category:</span>
                      <span className="text-sm text-gray-600 ml-2 capitalize">{result.category}</span>
                    </div>

                    {result.generated_xpath && (
                      <div>
                        <span className="text-sm font-medium text-gray-700">Generated XPath:</span>
                        <code className="block text-sm text-gray-800 bg-white p-2 rounded border mt-1 break-all">
                          {result.generated_xpath}
                        </code>
                      </div>
                    )}

                    {result.error_message && (
                      <div>
                        <span className="text-sm font-medium text-red-700">Error:</span>
                        <p className="text-sm text-red-600 mt-1">{result.error_message}</p>
                      </div>
                    )}

                    <div className="text-xs text-gray-500">
                      Execution time: {formatLatency(result.execution_time)}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {evaluationData.length === 0 && !isRunning && (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <svg className="w-16 h-16 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No evaluation results</h3>
          <p className="text-gray-500">Select a version and run the evaluation to see performance metrics.</p>
        </div>
      )}
    </div>
  )
}