interface TabNavigationProps {
  activeTab: 'generator' | 'evaluation'
  onTabChange: (tab: 'generator' | 'evaluation') => void
}

export function TabNavigation({ activeTab, onTabChange }: TabNavigationProps) {
  const tabs = [
    { id: 'generator' as const, label: 'Generator', icon: '⚡' },
    { id: 'evaluation' as const, label: 'Evaluation', icon: '📊' }
  ]

  return (
    <div className="border-b border-gray-200 bg-white">
      <div className="flex space-x-8 px-6">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`
              py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors
              ${activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }
            `}
          >
            <span>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  )
}