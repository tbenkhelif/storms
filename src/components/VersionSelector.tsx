import { useState } from 'react'

export type Version = 'v1' | 'v2' | 'v3'

interface VersionInfo {
  name: string
  description: string
  features: string[]
  limitations: string[]
  time: string
}

const versionData: Record<Version, VersionInfo> = {
  v1: {
    name: 'MVP',
    description: 'Direct LLM call, proof of concept',
    features: ['Basic XPath generation', 'Fast response'],
    limitations: ['No validation', 'May hallucinate', 'Context limits'],
    time: '1h'
  },
  v2: {
    name: 'Validated',
    description: 'Multi-candidate generation with validation',
    features: ['XPath validation', 'Retry logic', 'Process visibility'],
    limitations: ['No robustness testing', 'Higher latency'],
    time: '5h'
  },
  v3: {
    name: 'Enterprise',
    description: 'Agentic approach with tools',
    features: ['Tool-augmented LLM', 'Robustness scoring', 'Self-correction'],
    limitations: ['Highest latency', 'More API costs'],
    time: '10h'
  }
}

interface VersionSelectorProps {
  selectedVersion: Version
  onVersionChange: (version: Version) => void
}

export function VersionSelector({ selectedVersion, onVersionChange }: VersionSelectorProps) {
  const [isInfoOpen, setIsInfoOpen] = useState(false)
  const currentVersionInfo = versionData[selectedVersion]

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">Version</label>
        <div className="grid grid-cols-3 gap-2">
          {(Object.keys(versionData) as Version[]).map((version) => {
            const info = versionData[version]
            const isSelected = selectedVersion === version
            return (
              <button
                key={version}
                onClick={() => onVersionChange(version)}
                className={`
                  px-3 py-2 rounded-lg text-center transition-colors
                  ${isSelected
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }
                `}
              >
                <div className="font-medium">{version}</div>
                <div className="text-xs mt-0.5 opacity-80">({info.time})</div>
              </button>
            )
          })}
        </div>
      </div>

      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <button
          onClick={() => setIsInfoOpen(!isInfoOpen)}
          className="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors flex items-center justify-between text-left"
        >
          <div>
            <span className="text-sm font-medium text-gray-700">Version Info: </span>
            <span className="text-sm text-gray-600">{currentVersionInfo.name}</span>
          </div>
          <svg
            className={`w-5 h-5 text-gray-400 transform transition-transform ${
              isInfoOpen ? 'rotate-180' : ''
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {isInfoOpen && (
          <div className="p-4 space-y-3 bg-white">
            <p className="text-sm text-gray-600">{currentVersionInfo.description}</p>

            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wider">Features</h4>
              <ul className="space-y-1">
                {currentVersionInfo.features.map((feature, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm">
                    <svg className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    <span className="text-gray-700">{feature}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wider">Limitations</h4>
              <ul className="space-y-1">
                {currentVersionInfo.limitations.map((limitation, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm">
                    <svg className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <span className="text-gray-700">{limitation}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}