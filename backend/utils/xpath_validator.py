"""
XPath Validator Tool - Validates XPath syntax and provides detailed feedback
"""

import re
from typing import Dict, List, Optional, Any
from .xpath_utils import find_unmatched_chars, extract_xpath_functions, is_likely_xpath, get_xpath_complexity_score

try:
    from lxml import etree
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def validate_xpath_syntax(xpath: str) -> Dict[str, Any]:
    """
    Validate XPath syntax and structure

    Args:
        xpath: XPath expression to validate

    Returns:
        Dict with validation results
    """
    result = {
        "is_valid": False,
        "is_likely_xpath": False,
        "syntax_errors": [],
        "warnings": [],
        "suggestions": [],
        "complexity": None
    }

    # Basic checks
    if not xpath or not isinstance(xpath, str):
        result["syntax_errors"].append("XPath is empty or not a string")
        return result

    xpath = xpath.strip()
    result["is_likely_xpath"] = is_likely_xpath(xpath)

    if not result["is_likely_xpath"]:
        result["syntax_errors"].append("Text does not appear to be an XPath expression")
        result["suggestions"].append("XPath should start with / or // and contain element selectors")
        return result

    # Check for balanced characters
    char_pairs = [
        ('[', ']'),   # Brackets for predicates
        ('(', ')'),   # Parentheses for functions
        ('"', '"'),   # Double quotes
        ("'", "'"),   # Single quotes
    ]

    balance_issues = find_unmatched_chars(xpath, char_pairs)
    for issue in balance_issues:
        if issue['type'] == 'missing_closing':
            result["syntax_errors"].append(f"Missing {issue['missing_count']} closing '{issue['char']}'")
            result["suggestions"].append(f"Add {issue['missing_count']} '{issue['char']}' at the end")
        else:
            result["syntax_errors"].append(f"Extra {issue['missing_count']} '{issue['char']}' characters")
            result["suggestions"].append(f"Remove extra '{issue['char']}' characters")

    # Check for incomplete functions
    incomplete_functions = _find_incomplete_functions(xpath)
    for func_issue in incomplete_functions:
        result["syntax_errors"].append(f"Incomplete function: {func_issue['function']}")
        result["suggestions"].append(func_issue['suggestion'])

    # Check for malformed attributes
    malformed_attrs = _find_malformed_attributes(xpath)
    for attr_issue in malformed_attrs:
        result["syntax_errors"].append(f"Malformed attribute: {attr_issue['attribute']}")
        result["suggestions"].append(attr_issue['suggestion'])

    # Use lxml for detailed syntax checking if available
    if LXML_AVAILABLE and not result["syntax_errors"]:
        try:
            etree.XPath(xpath)
            result["is_valid"] = True
        except etree.XPathSyntaxError as e:
            result["syntax_errors"].append(f"XPath syntax error: {str(e)}")
            result["suggestions"].append("Check XPath syntax according to W3C XPath specification")
        except Exception as e:
            result["syntax_errors"].append(f"XPath validation error: {str(e)}")

    # If no lxml, do basic validation
    elif not LXML_AVAILABLE and not result["syntax_errors"]:
        result["is_valid"] = True
        result["warnings"].append("Advanced syntax validation unavailable (lxml not installed)")

    # Add complexity analysis
    result["complexity"] = get_xpath_complexity_score(xpath)

    # Additional warnings
    if '//' in xpath and xpath.count('//') > 3:
        result["warnings"].append("Many '//' operators may impact performance")

    if len(xpath) > 200:
        result["warnings"].append("Very long XPath may be hard to maintain")

    return result


async def test_xpath_on_page(xpath: str, url: str, timeout: int = 15000) -> Dict[str, Any]:
    """
    Test XPath against a live web page

    Args:
        xpath: XPath expression to test
        url: URL to test against
        timeout: Page load timeout in milliseconds

    Returns:
        Dict with test results
    """
    result = {
        "success": False,
        "match_count": 0,
        "elements": [],
        "error": None,
        "page_loaded": False
    }

    if not PLAYWRIGHT_AVAILABLE:
        result["error"] = "Playwright not available for live testing"
        return result

    # First validate syntax
    validation = validate_xpath_syntax(xpath)
    if not validation["is_valid"]:
        result["error"] = f"XPath syntax invalid: {validation['syntax_errors']}"
        return result

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()

            # Load page
            await page.goto(url, timeout=timeout, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)  # Brief wait for dynamic content
            result["page_loaded"] = True

            # Test XPath
            elements = await page.query_selector_all(f"xpath={xpath}")
            result["match_count"] = len(elements)

            # Get element details (limited to first 5 for performance)
            for i, element in enumerate(elements[:5]):
                try:
                    tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
                    text = await element.evaluate("el => (el.textContent || '').trim().substring(0, 100)")
                    attrs = await element.evaluate("""
                        el => {
                            const attrs = {};
                            for (const attr of el.attributes) {
                                if (['id', 'class', 'name', 'type', 'href'].includes(attr.name)) {
                                    attrs[attr.name] = attr.value.substring(0, 50);
                                }
                            }
                            return attrs;
                        }
                    """)

                    result["elements"].append({
                        "index": i,
                        "tag": tag_name,
                        "text": text,
                        "attributes": attrs
                    })
                except:
                    # Skip elements that can't be analyzed
                    continue

            result["success"] = True
            await browser.close()

        except Exception as e:
            result["error"] = str(e)
            if 'browser' in locals():
                try:
                    await browser.close()
                except:
                    pass

    return result


def analyze_xpath_structure(xpath: str) -> Dict[str, Any]:
    """
    Analyze XPath structure and provide detailed breakdown

    Args:
        xpath: XPath expression to analyze

    Returns:
        Dict with structural analysis
    """
    result = {
        "is_absolute": xpath.startswith('/') and not xpath.startswith('//'),
        "is_relative": xpath.startswith('//'),
        "steps": [],
        "functions": [],
        "attributes": [],
        "predicates": [],
        "complexity": None
    }

    # Extract path steps
    if xpath.startswith('//'):
        # Remove leading // and split by / or //
        path_parts = re.split(r'/+', xpath[2:])
        result["steps"] = [part for part in path_parts if part]
    elif xpath.startswith('/'):
        path_parts = xpath[1:].split('/')
        result["steps"] = [part for part in path_parts if part]

    # Extract functions
    result["functions"] = extract_xpath_functions(xpath)

    # Extract attributes
    attr_pattern = r'@([a-zA-Z_][a-zA-Z0-9_-]*)'
    result["attributes"] = re.findall(attr_pattern, xpath)

    # Extract predicates (content in square brackets)
    predicate_pattern = r'\[([^\]]+)\]'
    result["predicates"] = re.findall(predicate_pattern, xpath)

    # Add complexity analysis
    result["complexity"] = get_xpath_complexity_score(xpath)

    return result


def _find_incomplete_functions(xpath: str) -> List[Dict[str, str]]:
    """Find incomplete function calls in XPath"""
    issues = []

    # Common XPath functions and their expected patterns (fixed regex)
    function_patterns = {
        'contains': r'contains\s*\(\s*[^,)]+\s*,\s*[^)]+\s*\)',
        'text': r'text\s*\(\s*\)',
        'position': r'position\s*\(\s*\)',
        'last': r'last\s*\(\s*\)',
        'normalize-space': r'normalize-space\s*\(\s*[^)]*\s*\)'
    }

    # Find function calls that don't match complete patterns
    function_starts = re.finditer(r'([a-zA-Z-]+)\s*\(', xpath)

    for match in function_starts:
        func_name = match.group(1)
        start_pos = match.start()

        # Check if this function is complete
        remaining_text = xpath[start_pos:]

        if func_name in function_patterns:
            # Test the specific function pattern against the remaining text
            if not re.search(function_patterns[func_name], remaining_text):
                # Only flag as incomplete if it's clearly truncated
                if (remaining_text.endswith(func_name + '(') or
                    remaining_text.endswith(func_name + '()') or
                    re.search(rf'{func_name}\s*\([^)]*$', remaining_text)):

                    issues.append({
                        'function': func_name,
                        'position': start_pos,
                        'suggestion': f"Complete the {func_name}() function call"
                    })

        # Check for obviously truncated functions (ending with just opening paren)
        if (remaining_text.endswith(func_name + '(') or
            remaining_text.endswith(func_name + '()') and func_name != 'text'):

            if func_name == 'contains':
                issues.append({
                    'function': func_name,
                    'position': start_pos,
                    'suggestion': f"Add arguments: {func_name}(text(), 'value')"
                })
            else:
                issues.append({
                    'function': func_name,
                    'position': start_pos,
                    'suggestion': f"Complete the {func_name}() function"
                })

    return issues


def _find_malformed_attributes(xpath: str) -> List[Dict[str, str]]:
    """Find malformed attribute references in XPath"""
    issues = []

    # Find attribute patterns that look incomplete
    incomplete_patterns = [
        (r'@\w+\s*=\s*$', "Attribute assignment without value"),
        (r'@\w+\s*=[^"\'\]\s]', "Attribute value should be quoted"),
        (r'@\w+\s*=\s*["\'][^"\']*$', "Unterminated quoted attribute value"),
    ]

    for pattern, description in incomplete_patterns:
        matches = re.finditer(pattern, xpath)
        for match in matches:
            issues.append({
                'attribute': match.group(0),
                'position': match.start(),
                'suggestion': description
            })

    return issues