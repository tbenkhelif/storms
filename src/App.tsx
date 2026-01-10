import { useState } from 'react'

function App() {
  const [url, setUrl] = useState('')
  const [instruction, setInstruction] = useState('')
  const [generatedXPath, setGeneratedXPath] = useState('')
  const [copied, setCopied] = useState(false)

  const handleGenerateXPath = () => {
    setGeneratedXPath("//button[@id='placeholder']")
  }

  const handleCopyToClipboard = () => {
    navigator.clipboard.writeText(generatedXPath)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-800">
          ⛈️ Storms
        </h1>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-2/5 bg-white border-r border-gray-200 p-6 flex flex-col space-y-6 overflow-y-auto">
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

          <button
            onClick={handleGenerateXPath}
            disabled={!url || !instruction}
            className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition shadow-sm"
          >
            Generate XPath
          </button>

          {generatedXPath && (
            <div className="space-y-3 p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-gray-700">Generated XPath:</h3>
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
                  {generatedXPath}
                </code>
              </div>
            </div>
          )}
        </div>

        <div className="w-3/5 bg-gray-100 p-4">
          <div className="h-full bg-white rounded-lg shadow-sm overflow-hidden">
            {url ? (
              <iframe
                src={url}
                className="w-full h-full border-0"
                title="Target Website"
                sandbox="allow-same-origin allow-scripts"
              />
            ) : (
              <div className="h-full flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <svg className="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                  </svg>
                  <p className="text-lg">Enter a URL to preview the website</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App