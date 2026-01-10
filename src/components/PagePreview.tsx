import { useState, useRef, useEffect } from 'react'

interface PagePreviewProps {
  url: string
  xpath?: string
  validated?: boolean
}

function isExternalUrl(url: string): boolean {
  try {
    const urlObj = new URL(url)
    const isLocal = urlObj.hostname === 'localhost' ||
                   urlObj.hostname === '127.0.0.1' ||
                   urlObj.hostname === window.location.hostname
    return !isLocal
  } catch {
    return false
  }
}

export function PagePreview({ url, xpath, validated }: PagePreviewProps) {
  const [highlightEnabled, setHighlightEnabled] = useState(false)
  const [showSnippet, setShowSnippet] = useState(false)
  const [snippetCopied, setSnippetCopied] = useState(false)
  const [useProxy, setUseProxy] = useState(false)
  const iframeRef = useRef<HTMLIFrameElement>(null)

  // Determine URLs
  const isExternal = isExternalUrl(url)
  const directUrl = url
  const proxyUrl = `http://localhost:8000/api/proxy?url=${encodeURIComponent(url)}`
  const iframeUrl = (useProxy && isExternal) ? proxyUrl : directUrl

  const generateHighlightScript = (xpathExpression: string) => {
    // Properly escape the XPath for JavaScript string
    const escapedXPath = xpathExpression.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/'/g, "\\'");
    const safeXPath = JSON.stringify(xpathExpression); // Use JSON.stringify for proper escaping

    return `(function() {
  try {
    var xpath = ${safeXPath};
    console.log('🔍 Storms: Looking for XPath:', xpath);

    // Remove any existing highlights first
    var existing = document.querySelectorAll('.storms-highlight');
    existing.forEach(function(e) {
      e.classList.remove('storms-highlight');
      e.style.removeProperty('outline');
      e.style.removeProperty('background-color');
      e.style.removeProperty('animation');
      e.style.removeProperty('box-shadow');
    });

    // Remove existing tooltips
    var existingTooltips = document.querySelectorAll('.storms-tooltip');
    existingTooltips.forEach(function(t) { t.remove(); });

    // Evaluate XPath
    var result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
    var el = result.singleNodeValue;

    if (el) {
      // Multiple highlighting methods for maximum visibility
      el.style.setProperty('outline', '5px solid #ff0000', 'important');
      el.style.setProperty('outline-offset', '2px', 'important');
      el.style.setProperty('background-color', 'rgba(255, 0, 0, 0.3)', 'important');
      el.style.setProperty('box-shadow', '0 0 20px rgba(255, 0, 0, 0.8), inset 0 0 20px rgba(255, 0, 0, 0.3)', 'important');
      el.style.setProperty('border', '3px dashed #ff0000', 'important');
      el.style.setProperty('position', 'relative', 'important');
      el.classList.add('storms-highlight');

      // Add pulsing animation
      el.style.setProperty('animation', 'storms-pulse 1s infinite alternate', 'important');

      // Add animation keyframes to document
      var styleEl = document.getElementById('storms-animation-style');
      if (!styleEl) {
        styleEl = document.createElement('style');
        styleEl.id = 'storms-animation-style';
        styleEl.textContent = \`
          @keyframes storms-pulse {
            0% {
              outline-color: #ff0000;
              box-shadow: 0 0 20px rgba(255, 0, 0, 0.8), inset 0 0 20px rgba(255, 0, 0, 0.3);
            }
            100% {
              outline-color: #ff6666;
              box-shadow: 0 0 30px rgba(255, 0, 0, 1), inset 0 0 30px rgba(255, 0, 0, 0.5);
            }
          }
        \`;
        document.head.appendChild(styleEl);
      }

      // Scroll to element first
      el.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });

      // Wait a bit then show tooltip near the element
      setTimeout(function() {
        var rect = el.getBoundingClientRect();
        var scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        var scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;

        var tooltip = document.createElement('div');
        tooltip.className = 'storms-tooltip';
        tooltip.innerHTML = '🎯 STORMS: Element Found!<br>' +
                            'Tag: ' + el.tagName.toLowerCase() +
                            (el.id ? '<br>ID: ' + el.id : '') +
                            (el.className ? '<br>Class: ' + el.className : '');

        // Position tooltip above the element, or below if not enough space
        var tooltipTop = rect.top + scrollTop - 60; // Above element
        if (tooltipTop < 10) {
          tooltipTop = rect.bottom + scrollTop + 10; // Below element if no space above
        }

        tooltip.style.cssText = 'position: absolute; ' +
                               'top: ' + tooltipTop + 'px; ' +
                               'left: ' + (rect.left + scrollLeft) + 'px; ' +
                               'background: #ff0000; color: white; padding: 12px; ' +
                               'border-radius: 8px; font-size: 14px; font-weight: bold; ' +
                               'z-index: 999999; box-shadow: 0 4px 20px rgba(0,0,0,0.5); ' +
                               'max-width: 300px; line-height: 1.4; ' +
                               'border: 2px solid white; pointer-events: none;';

        document.body.appendChild(tooltip);

        // Auto-remove tooltip after 5 seconds
        setTimeout(function() {
          if (tooltip && tooltip.parentNode) {
            tooltip.remove();
          }
        }, 5000);
      }, 500);

      console.log('✅ Storms: Element highlighted successfully', el);
      console.log('Element info:', {
        tag: el.tagName,
        id: el.id,
        className: el.className,
        text: el.textContent ? el.textContent.substring(0, 100) : 'No text'
      });

      return el;
    } else {
      console.log('❌ Storms: No element found for XPath:', xpath);

      // Show error tooltip
      var errorTooltip = document.createElement('div');
      errorTooltip.className = 'storms-tooltip';
      errorTooltip.innerHTML = '❌ No element found<br>XPath: ' + xpath.substring(0, 50) + (xpath.length > 50 ? '...' : '');
      errorTooltip.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #d32f2f; color: white; padding: 12px; border-radius: 6px; font-size: 12px; z-index: 999999; box-shadow: 0 4px 12px rgba(0,0,0,0.3); max-width: 300px;';
      document.body.appendChild(errorTooltip);
      setTimeout(function() {
        if (errorTooltip.parentNode) errorTooltip.remove();
      }, 3000);

      return null;
    }
  } catch (e) {
    console.error('❌ Storms: Error highlighting element:', e);

    // Show error tooltip
    var errorTooltip = document.createElement('div');
    errorTooltip.className = 'storms-tooltip';
    errorTooltip.innerHTML = '❌ Script Error<br>' + e.message;
    errorTooltip.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #d32f2f; color: white; padding: 12px; border-radius: 6px; font-size: 12px; z-index: 999999; box-shadow: 0 4px 12px rgba(0,0,0,0.3); max-width: 300px;';
    document.body.appendChild(errorTooltip);
    setTimeout(function() {
      if (errorTooltip.parentNode) errorTooltip.remove();
    }, 3000);

    return null;
  }
})();`
  }

  const tryInjectHighlight = async () => {
    if (!xpath || !validated || !iframeRef.current) return

    const iframe = iframeRef.current
    const script = generateHighlightScript(xpath)

    try {
      // First try direct DOM access (same-origin)
      const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document

      if (iframeDoc) {
        console.log('✅ Same-origin iframe detected - injecting highlight script')

        // Remove any existing scripts
        const existingScripts = iframeDoc.querySelectorAll('script[data-storms-highlight]')
        existingScripts.forEach(s => s.remove())

        // Inject the highlighting script
        const scriptElement = iframeDoc.createElement('script')
        scriptElement.setAttribute('data-storms-highlight', 'true')
        scriptElement.textContent = script

        if (iframeDoc.readyState === 'complete') {
          iframeDoc.head.appendChild(scriptElement)
        } else {
          iframe.addEventListener('load', () => {
            iframeDoc.head.appendChild(scriptElement)
          })
        }

        return true
      } else {
        throw new Error('Cannot access iframe content')
      }
    } catch (error) {
      // Try postMessage approach (for proxied content)
      if (useProxy && isExternal) {
        console.log('🔄 Trying postMessage approach for proxied content')

        try {
          iframe.contentWindow?.postMessage({
            type: 'INJECT_HIGHLIGHT_SCRIPT',
            script: script
          }, '*')

          return true
        } catch (e) {
          console.log('❌ PostMessage failed:', e)
        }
      }

      console.log('❌ Cross-origin iframe detected, cannot inject highlight script')

      // Show user-friendly message with proxy option
      const container = iframe.parentElement
      if (container) {
        const overlay = document.createElement('div')
        overlay.style.cssText = `
          position: absolute;
          top: 10px;
          left: 10px;
          background: rgba(255, 165, 0, 0.9);
          color: white;
          padding: 8px 12px;
          border-radius: 4px;
          font-size: 12px;
          z-index: 1000;
          pointer-events: auto;
          cursor: pointer;
        `
        overlay.innerHTML = isExternal ?
          '⚠️ Cross-origin site - <strong>Click to try proxy</strong>' :
          '⚠️ Cross-origin site - use "Highlight in New Tab"'

        container.style.position = 'relative'

        if (isExternal && !useProxy) {
          overlay.addEventListener('click', () => {
            setUseProxy(true)
            overlay.remove()
          })
        }

        container.appendChild(overlay)

        setTimeout(() => {
          if (overlay.parentElement) overlay.remove()
        }, 5000)
      }

      return false
    }
  }

  const copySnippet = async () => {
    if (!xpath) return

    const script = generateHighlightScript(xpath)
    await navigator.clipboard.writeText(script)
    setSnippetCopied(true)
    setTimeout(() => setSnippetCopied(false), 2000)
  }

  const openInNewTab = () => {
    if (!xpath || !url) return

    // Open URL in new tab with hash parameter containing the highlighting script
    const script = generateHighlightScript(xpath)
    const encodedScript = encodeURIComponent(script)

    // Create a simple bookmarklet
    const bookmarklet = `javascript:${script}`

    // Open in new tab and show instructions
    const newWindow = window.open(url, '_blank')

    // Show instructions to user
    setTimeout(() => {
      alert(`To highlight the element:
1. Wait for the page to load
2. Open browser console (F12)
3. Paste the copied script and press Enter

The script has been copied to your clipboard.`)
    }, 1000)

    // Copy script to clipboard
    copySnippet()
  }

  useEffect(() => {
    if (highlightEnabled && xpath && validated) {
      // Try to inject after iframe loads
      setTimeout(() => {
        tryInjectHighlight()
      }, 2000)
    }
  }, [highlightEnabled, xpath, validated, url])

  // Auto-enable highlighting for same-origin or when XPath changes
  useEffect(() => {
    if (xpath && validated && url) {
      // Try to determine if it might be same-origin
      try {
        const urlObj = new URL(url)
        const isLocalhost = urlObj.hostname === 'localhost' || urlObj.hostname === '127.0.0.1'
        if (isLocalhost) {
          setHighlightEnabled(true)
        }
      } catch (e) {
        // Invalid URL, keep highlighting off
      }
    }
  }, [xpath, validated, url])

  if (!url) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        <div className="text-center">
          <svg className="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s-1.343-9 3-9m-9 9a9 9 0 019-9" />
          </svg>
          <p className="text-lg">Enter a URL to preview the website</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Control bar */}
      {xpath && validated && (
        <div className="bg-gray-100 border-b border-gray-200 p-3 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={highlightEnabled}
                  onChange={(e) => setHighlightEnabled(e.target.checked)}
                  className="rounded"
                />
                Try auto-highlight (same-origin only)
              </label>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => {
                  // Test the script on current page (for debugging)
                  const script = generateHighlightScript(xpath || '//body')
                  eval(script)
                }}
                className="text-xs bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700 transition"
                title="Test highlight on this page"
              >
                Test Here
              </button>
              <button
                onClick={openInNewTab}
                className="text-xs bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 transition"
              >
                Highlight in New Tab
              </button>
              <button
                onClick={() => setShowSnippet(!showSnippet)}
                className="text-xs bg-gray-600 text-white px-3 py-1 rounded hover:bg-gray-700 transition"
              >
                {showSnippet ? 'Hide' : 'Show'} Script
              </button>
            </div>
          </div>

          {/* Script snippet */}
          {showSnippet && xpath && (
            <div className="bg-white border border-gray-300 rounded p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-gray-700">
                  Paste in browser console to highlight element:
                </span>
                <button
                  onClick={copySnippet}
                  className="text-xs bg-gray-200 hover:bg-gray-300 px-2 py-1 rounded transition"
                >
                  {snippetCopied ? '✅ Copied' : 'Copy'}
                </button>
              </div>
              <div className="bg-gray-50 p-2 rounded text-xs font-mono max-h-24 overflow-y-auto border">
                {generateHighlightScript(xpath)}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Open browser console (F12), paste this script, and press Enter to highlight the matched element.
              </p>
            </div>
          )}

          {!validated && (
            <div className="text-xs text-yellow-600 bg-yellow-50 p-2 rounded border border-yellow-200">
              ⚠️ XPath not validated - highlighting may not work
            </div>
          )}
        </div>
      )}

      {/* Iframe */}
      <div className="flex-1 overflow-hidden relative">
        {useProxy && isExternal && (
          <div className="absolute top-2 right-2 bg-blue-600 text-white text-xs px-2 py-1 rounded z-10">
            📡 Proxied
          </div>
        )}
        <iframe
          ref={iframeRef}
          src={iframeUrl}
          className="w-full h-full border-0"
          title="Target Website"
          sandbox="allow-same-origin allow-scripts allow-forms allow-top-navigation"
          onLoad={() => {
            if (highlightEnabled) {
              setTimeout(tryInjectHighlight, 500)
            }
          }}
        />
      </div>
    </div>
  )
}