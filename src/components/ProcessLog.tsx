import { useState, useEffect } from 'react'

interface ProcessLogEntry {
  step: string
  status: string
  details?: string
}

interface ProcessLogProps {
  entries: ProcessLogEntry[]
}

export function ProcessLog({ entries }: ProcessLogProps) {
  const [visibleEntries, setVisibleEntries] = useState<ProcessLogEntry[]>([])
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set())

  // Animate entries appearing one by one
  useEffect(() => {
    if (entries.length === 0) {
      setVisibleEntries([])
      return
    }

    setVisibleEntries([])
    entries.forEach((entry, index) => {
      setTimeout(() => {
        setVisibleEntries(prev => [...prev, entry])
      }, index * 150)
    })
  }, [entries])

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'started':
      case 'trying':
      case 'running':
        return '⏳'
      case 'success':
      case 'done':
      case 'completed':
        return '✅'
      case 'failed':
      case 'error':
      case 'miss':
        return '❌'
      case 'skipped':
      case 'warning':
        return '⏭️'
      default:
        return '🔄'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'started':
      case 'trying':
      case 'running':
        return 'text-blue-600 bg-blue-50 border-blue-200'
      case 'success':
      case 'done':
      case 'completed':
        return 'text-green-600 bg-green-50 border-green-200'
      case 'failed':
      case 'error':
      case 'miss':
        return 'text-red-600 bg-red-50 border-red-200'
      case 'skipped':
      case 'warning':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const toggleExpanded = (index: number) => {
    setExpandedSteps(prev => {
      const newSet = new Set(prev)
      if (newSet.has(index)) {
        newSet.delete(index)
      } else {
        newSet.add(index)
      }
      return newSet
    })
  }

  const formatStepName = (step: string) => {
    return step
      .replace(/_/g, ' ')
      .replace(/([A-Z])/g, ' $1')
      .replace(/^./, str => str.toUpperCase())
      .trim()
  }

  if (visibleEntries.length === 0) {
    return null
  }

  return (
    <div className="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
      <h3 className="text-sm font-medium text-gray-700 mb-4 flex items-center gap-2">
        <span>🔍</span>
        Process Log
      </h3>

      <div className="space-y-3">
        {visibleEntries.map((entry, index) => {
          const isExpanded = expandedSteps.has(index)
          const hasDetails = entry.details && entry.details.length > 0
          const statusColors = getStatusColor(entry.status)

          return (
            <div
              key={index}
              className={`
                relative animate-fade-in-up
                ${index > 0 ? 'border-l-2 border-gray-200 ml-4 pl-6' : ''}
              `}
              style={{ animationDelay: `${index * 150}ms` }}
            >
              {index > 0 && (
                <div className="absolute -left-[9px] top-0 w-4 h-4 bg-white border-2 border-gray-200 rounded-full"></div>
              )}

              <div
                className={`
                  p-3 rounded-lg border cursor-pointer transition-all duration-200
                  ${statusColors}
                  ${hasDetails ? 'hover:shadow-sm' : ''}
                `}
                onClick={() => hasDetails && toggleExpanded(index)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-lg">{getStatusIcon(entry.status)}</span>
                    <div>
                      <span className="font-medium text-sm">
                        {formatStepName(entry.step)}
                      </span>
                      <span className="ml-2 text-xs opacity-75 capitalize">
                        {entry.status}
                      </span>
                    </div>
                  </div>

                  {hasDetails && (
                    <button className="text-xs text-gray-500 hover:text-gray-700 transition-colors">
                      <svg
                        className={`w-4 h-4 transform transition-transform ${
                          isExpanded ? 'rotate-180' : ''
                        }`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                  )}
                </div>

                {hasDetails && isExpanded && (
                  <div className="mt-2 pt-2 border-t border-current border-opacity-20">
                    <div className="text-xs font-mono bg-white bg-opacity-50 p-2 rounded border">
                      {entry.details}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      <style jsx>{`
        @keyframes fade-in-up {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fade-in-up {
          animation: fade-in-up 0.3s ease-out forwards;
          opacity: 0;
        }
      `}</style>
    </div>
  )
}