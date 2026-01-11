"""
Common XPath utilities and helper functions
"""

import re
from typing import Dict, List, Tuple


def count_balanced_chars(text: str, open_char: str, close_char: str) -> Tuple[int, int, bool]:
    """
    Count opening and closing characters and check if balanced

    Returns:
        (open_count, close_count, is_balanced)
    """
    open_count = text.count(open_char)
    close_count = text.count(close_char)
    is_balanced = open_count == close_count

    return open_count, close_count, is_balanced


def find_unmatched_chars(text: str, pairs: List[Tuple[str, str]]) -> List[Dict]:
    """
    Find unmatched opening/closing characters

    Args:
        text: Text to analyze
        pairs: List of (open_char, close_char) tuples

    Returns:
        List of issues found
    """
    issues = []

    for open_char, close_char in pairs:
        open_count, close_count, is_balanced = count_balanced_chars(text, open_char, close_char)

        if not is_balanced:
            if open_count > close_count:
                issues.append({
                    'type': 'missing_closing',
                    'char': close_char,
                    'missing_count': open_count - close_count
                })
            else:
                issues.append({
                    'type': 'missing_opening',
                    'char': open_char,
                    'missing_count': close_count - open_count
                })

    return issues


def extract_xpath_functions(xpath: str) -> List[str]:
    """Extract XPath function calls from expression"""
    # Find function patterns like contains(, text(, position(
    function_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
    functions = re.findall(function_pattern, xpath)
    return functions


def is_likely_xpath(text: str) -> bool:
    """Check if text looks like an XPath expression"""
    text = text.strip()

    # Must start with / or //
    if not (text.startswith('/') or text.startswith('//')):
        return False

    # Should have some XPath-like patterns
    xpath_indicators = [
        r'@\w+',  # Attributes like @id, @class
        r'\[\d+\]',  # Position selectors like [1], [2]
        r'\[[^\]]+\]',  # Any predicate in brackets
        r'/\w+',  # Element names
        r'//\w+',  # Descendant selectors
        'text()',
        'contains(',
        'position(',
        'last()'
    ]

    for pattern in xpath_indicators:
        if re.search(pattern, text):
            return True

    return False


def get_xpath_complexity_score(xpath: str) -> Dict:
    """Analyze XPath complexity and return score with breakdown"""

    score = 0
    factors = []

    # Count different complexity factors
    slash_count = xpath.count('/')
    predicate_count = xpath.count('[')
    function_count = len(extract_xpath_functions(xpath))
    axis_count = len(re.findall(r'::', xpath))  # child::, descendant::, etc.

    # Simple scoring system
    if slash_count <= 3:
        score += 1
        factors.append("Simple path depth")
    elif slash_count <= 6:
        score += 2
        factors.append("Moderate path depth")
    else:
        score += 3
        factors.append("Deep path nesting")

    if predicate_count == 0:
        score += 1
        factors.append("No predicates")
    elif predicate_count <= 2:
        score += 2
        factors.append("Few predicates")
    else:
        score += 3
        factors.append("Many predicates")

    if function_count == 0:
        score += 1
        factors.append("No functions")
    elif function_count <= 2:
        score += 2
        factors.append("Some functions")
    else:
        score += 3
        factors.append("Many functions")

    # Determine complexity level
    if score <= 3:
        complexity = "Simple"
    elif score <= 6:
        complexity = "Moderate"
    else:
        complexity = "Complex"

    return {
        "score": score,
        "complexity": complexity,
        "factors": factors,
        "details": {
            "path_depth": slash_count,
            "predicates": predicate_count,
            "functions": function_count,
            "axes": axis_count
        }
    }