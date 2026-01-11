"""
XPath Fixer Tool - Automatically fixes common XPath syntax errors
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from .xpath_utils import find_unmatched_chars, extract_xpath_functions, is_likely_xpath
from .xpath_validator import validate_xpath_syntax


def fix_xpath(broken_xpath: str, instruction: str = None) -> Dict[str, Any]:
    """
    Attempt to fix a broken XPath expression

    Args:
        broken_xpath: The potentially broken XPath
        instruction: Original instruction for context (optional)

    Returns:
        Dict with fix results
    """
    result = {
        "original_xpath": broken_xpath,
        "fixed_xpath": broken_xpath,
        "changes_made": [],
        "confidence": 0.0,
        "is_fixed": False,
        "suggestions": []
    }

    if not broken_xpath or not isinstance(broken_xpath, str):
        result["suggestions"].append("Provide a valid XPath string")
        return result

    working_xpath = broken_xpath.strip()

    # Apply fixes in order of confidence
    fixes_applied = []

    # 1. Fix obvious truncation (highest confidence)
    truncation_fix = _fix_truncation(working_xpath, instruction)
    if truncation_fix["fixed"]:
        working_xpath = truncation_fix["result"]
        fixes_applied.extend(truncation_fix["changes"])

    # 2. Balance brackets and parentheses
    balance_fix = _fix_balance_issues(working_xpath)
    if balance_fix["fixed"]:
        working_xpath = balance_fix["result"]
        fixes_applied.extend(balance_fix["changes"])

    # 3. Fix quote issues
    quote_fix = _fix_quote_issues(working_xpath)
    if quote_fix["fixed"]:
        working_xpath = quote_fix["result"]
        fixes_applied.extend(quote_fix["changes"])

    # 4. Fix malformed attributes
    attr_fix = _fix_attribute_issues(working_xpath)
    if attr_fix["fixed"]:
        working_xpath = attr_fix["result"]
        fixes_applied.extend(attr_fix["changes"])

    # 5. Complete incomplete functions
    function_fix = _fix_function_issues(working_xpath, instruction)
    if function_fix["fixed"]:
        working_xpath = function_fix["result"]
        fixes_applied.extend(function_fix["changes"])

    # Update result
    result["fixed_xpath"] = working_xpath
    result["changes_made"] = fixes_applied

    # Calculate confidence based on fixes applied and validation
    confidence = _calculate_confidence(broken_xpath, working_xpath, fixes_applied)
    result["confidence"] = confidence

    # Validate the result
    validation = validate_xpath_syntax(working_xpath)
    result["is_fixed"] = validation["is_valid"]

    if not result["is_fixed"] and validation["syntax_errors"]:
        result["suggestions"] = validation["suggestions"]

    return result


def fix_truncated_xpath(partial_xpath: str) -> List[str]:
    """
    Generate possible completions for truncated XPath expressions

    Args:
        partial_xpath: Incomplete XPath

    Returns:
        List of possible completed XPaths
    """
    completions = []

    if not partial_xpath:
        return completions

    # Common truncation patterns and their fixes
    patterns = [
        # Function truncations
        (r'//\w+\[contains\(text\(\)$', lambda m: m.group(0) + ', "text")]'),
        (r'//\w+\[contains\(text\($', lambda m: m.group(0) + ', "text")]'),
        (r'//\w+\[contains\($', lambda m: m.group(0) + 'text(), "value")]'),
        (r'//\w+\[text\(\)$', lambda m: m.group(0)),  # text() is complete

        # Attribute truncations
        (r'//\w+\[@\w+$', lambda m: m.group(0) + '="value"]'),
        (r'//\w+\[@\w+=$', lambda m: m.group(0) + '"value"]'),
        (r'//\w+\[@\w+=[\'"]\w*$', lambda m: m.group(0) + '"]' if '"' in m.group(0) else m.group(0) + "']"),

        # General bracket completion
        (r'//\w+\[[^\]]*$', lambda m: m.group(0) + ']'),

        # Element completion
        (r'^//\w*$', lambda m: m.group(0) if len(m.group(0)) > 3 else '//input'),
    ]

    for pattern, completion_func in patterns:
        match = re.search(pattern, partial_xpath)
        if match:
            try:
                completed = completion_func(match)
                if completed and completed != partial_xpath:
                    completions.append(completed)
            except:
                continue

    # Add some generic fallback completions
    if partial_xpath.startswith('//') and len(partial_xpath) < 10:
        generic_completions = [
            partial_xpath + "input",
            partial_xpath + "button",
            partial_xpath + "a",
            partial_xpath + "*"
        ]
        completions.extend(generic_completions)

    return list(set(completions))  # Remove duplicates


def balance_brackets_and_quotes(xpath: str) -> str:
    """
    Fix unbalanced brackets, parentheses, and quotes

    Args:
        xpath: XPath with potential balance issues

    Returns:
        XPath with balanced characters
    """
    working_xpath = xpath

    # Fix unbalanced brackets and parentheses
    char_pairs = [('[', ']'), ('(', ')')]

    for open_char, close_char in char_pairs:
        balance_issues = find_unmatched_chars(working_xpath, [(open_char, close_char)])

        for issue in balance_issues:
            if issue['type'] == 'missing_closing':
                # Add missing closing characters at the end
                working_xpath += close_char * issue['missing_count']
            elif issue['type'] == 'missing_opening':
                # Remove extra closing characters from the end
                for _ in range(issue['missing_count']):
                    working_xpath = working_xpath.rstrip(close_char)

    # Fix quote issues (more complex due to matching pairs)
    working_xpath = _balance_quotes(working_xpath)

    return working_xpath


def _fix_truncation(xpath: str, instruction: str = None) -> Dict[str, Any]:
    """Fix obvious truncation patterns"""
    result = {"fixed": False, "result": xpath, "changes": []}

    working_xpath = xpath

    # Handle specific truncation patterns manually (avoid complex regex)
    if working_xpath.endswith('contains(text()'):
        working_xpath = working_xpath + ', "")'
        result["fixed"] = True
        result["changes"].append("Completed truncated contains() function")
    elif working_xpath.endswith('contains(text('):
        working_xpath = working_xpath + '(), "")'
        result["fixed"] = True
        result["changes"].append("Completed truncated contains() function")
    elif working_xpath.endswith('contains('):
        working_xpath = working_xpath + 'text(), "")'
        result["fixed"] = True
        result["changes"].append("Completed truncated contains() function")
    elif working_xpath.endswith('text('):
        working_xpath = working_xpath + ')'
        result["fixed"] = True
        result["changes"].append("Completed truncated text() function")

    # Handle attribute truncations
    elif re.search(r'@\w+$', working_xpath):
        working_xpath = working_xpath + '=""'
        result["fixed"] = True
        result["changes"].append("Added missing attribute value")
    elif working_xpath.endswith('='):
        working_xpath = working_xpath + '""'
        result["fixed"] = True
        result["changes"].append("Added missing quoted attribute value")

    # Try to extract meaningful text from instruction for contains()
    if instruction and 'contains(text(), "")' in working_xpath:
        search_term = _extract_search_term_from_instruction(instruction)
        if search_term:
            working_xpath = working_xpath.replace('contains(text(), "")', f'contains(text(), "{search_term}")')
            result["fixed"] = True
            result["changes"].append(f"Added search term '{search_term}' from instruction")

    result["result"] = working_xpath
    return result


def _fix_balance_issues(xpath: str) -> Dict[str, Any]:
    """Fix unbalanced brackets and parentheses"""
    result = {"fixed": False, "result": xpath, "changes": []}

    working_xpath = xpath
    changes = []

    # Check and fix balance issues
    char_pairs = [('[', ']'), ('(', ')')]

    for open_char, close_char in char_pairs:
        balance_issues = find_unmatched_chars(working_xpath, [(open_char, close_char)])

        for issue in balance_issues:
            if issue['type'] == 'missing_closing':
                working_xpath += close_char * issue['missing_count']
                changes.append(f"Added {issue['missing_count']} missing '{close_char}'")
                result["fixed"] = True
            elif issue['type'] == 'missing_opening':
                # Remove extra closing characters from the end
                for _ in range(issue['missing_count']):
                    if working_xpath.endswith(close_char):
                        working_xpath = working_xpath[:-1]
                        changes.append(f"Removed extra '{close_char}'")
                        result["fixed"] = True

    result["result"] = working_xpath
    result["changes"] = changes
    return result


def _fix_quote_issues(xpath: str) -> Dict[str, Any]:
    """Fix quote-related issues"""
    result = {"fixed": False, "result": xpath, "changes": []}

    working_xpath = xpath
    changes = []

    # Fix mismatched quotes in attribute values
    # Pattern: @attr="value' or @attr='value"
    mismatch_pattern = r'(@\w+\s*=\s*)(["\'])([^"\']*?)(["\'])'

    def fix_quote_mismatch(match):
        attr_part = match.group(1)
        start_quote = match.group(2)
        value = match.group(3)
        end_quote = match.group(4)

        if start_quote != end_quote:
            # Use the start quote type for consistency
            return f"{attr_part}{start_quote}{value}{start_quote}"
        return match.group(0)

    new_xpath = re.sub(mismatch_pattern, fix_quote_mismatch, working_xpath)
    if new_xpath != working_xpath:
        result["fixed"] = True
        result["result"] = new_xpath
        result["changes"].append("Fixed mismatched quotes in attribute values")
        working_xpath = new_xpath

    # Add missing quotes around attribute values
    unquoted_pattern = r'(@\w+\s*=\s*)([^"\'\s\]]+)'

    def add_quotes(match):
        attr_part = match.group(1)
        value = match.group(2)
        return f'{attr_part}"{value}"'

    new_xpath = re.sub(unquoted_pattern, add_quotes, working_xpath)
    if new_xpath != working_xpath:
        result["fixed"] = True
        result["result"] = new_xpath
        result["changes"].append("Added missing quotes around attribute values")

    return result


def _fix_attribute_issues(xpath: str) -> Dict[str, Any]:
    """Fix malformed attribute references"""
    result = {"fixed": False, "result": xpath, "changes": []}

    working_xpath = xpath
    changes = []

    # Fix incomplete attribute assignments (@attr=)
    incomplete_attr = r'(@\w+\s*=\s*)(?=[\]\s]|$)'
    if re.search(incomplete_attr, working_xpath):
        working_xpath = re.sub(incomplete_attr, r'\1""', working_xpath)
        changes.append("Added missing attribute value")
        result["fixed"] = True

    # Fix attributes missing @ symbol
    missing_at = r'\b(\w+)\s*=\s*["\'][\w\s]*["\']'
    # Be careful not to match contains() functions or other valid patterns
    if re.search(missing_at, working_xpath) and 'contains(' not in working_xpath:
        # This is a complex fix that could break things, so be conservative
        pass

    result["result"] = working_xpath
    result["changes"] = changes
    return result


def _fix_function_issues(xpath: str, instruction: str = None) -> Dict[str, Any]:
    """Fix incomplete function calls"""
    result = {"fixed": False, "result": xpath, "changes": []}

    working_xpath = xpath
    changes = []

    # Fix common incomplete functions
    function_fixes = [
        # contains() function fixes
        (r'contains\(\s*text\(\)\s*$', 'contains(text(), "")', "Completed contains() function"),
        (r'contains\(\s*text\(\)\s*,\s*$', 'contains(text(), "")', "Added missing contains() argument"),
        (r'contains\(\s*@\w+\s*$', r'contains(@\w+, "")', "Completed contains() function with attribute"),
        (r'contains\(\s*@\w+\s*,\s*$', r'contains(@\w+, "")', "Added missing contains() argument"),

        # Other function fixes
        (r'text\(\s*$', 'text()', "Completed text() function"),
        (r'position\(\s*$', 'position()', "Completed position() function"),
        (r'last\(\s*$', 'last()', "Completed last() function"),
    ]

    for pattern, replacement, description in function_fixes:
        if re.search(pattern, working_xpath):
            new_xpath = re.sub(pattern, replacement, working_xpath)
            if new_xpath != working_xpath:
                working_xpath = new_xpath
                changes.append(description)
                result["fixed"] = True

    # Special case: if we have instruction context, try to fill in contains() values
    if instruction and 'contains(text(), "")' in working_xpath:
        search_term = _extract_search_term_from_instruction(instruction)
        if search_term:
            working_xpath = working_xpath.replace('contains(text(), "")', f'contains(text(), "{search_term}")')
            changes.append(f"Added search term '{search_term}' from instruction")
            result["fixed"] = True

    result["result"] = working_xpath
    result["changes"] = changes
    return result


def _balance_quotes(xpath: str) -> str:
    """Balance quotes in XPath expression"""
    # This is a simplified quote balancer
    # Count unmatched quotes and add them at the end

    double_quotes = xpath.count('"')
    single_quotes = xpath.count("'")

    # If odd number of quotes, add one at the end
    if double_quotes % 2 == 1:
        xpath += '"'
    if single_quotes % 2 == 1:
        xpath += "'"

    return xpath


def _extract_search_term_from_instruction(instruction: str) -> Optional[str]:
    """Extract likely search term from instruction"""
    if not instruction:
        return None

    instruction_lower = instruction.lower()

    # Patterns to extract search terms
    search_patterns = [
        r'search for (["\']?)([^"\']+)\1',  # "search for something"
        r'find (["\']?)([^"\']+)\1',        # "find something"
        r'look for (["\']?)([^"\']+)\1',    # "look for something"
        r'click on (["\']?)([^"\']+)\1',    # "click on something"
    ]

    for pattern in search_patterns:
        match = re.search(pattern, instruction_lower)
        if match:
            term = match.group(2).strip()
            # Clean up common words
            if term and len(term) > 2 and term not in ['the', 'a', 'an', 'and', 'or', 'but']:
                return term

    return None


def _calculate_confidence(original: str, fixed: str, changes: List[str]) -> float:
    """Calculate confidence score for the fix"""
    if original == fixed:
        return 1.0  # No changes needed

    confidence = 0.0

    # Base confidence based on types of changes
    change_scores = {
        'missing closing': 0.9,   # High confidence - obvious fix
        'missing quotes': 0.8,    # High confidence
        'truncated': 0.8,         # High confidence
        'unbalanced': 0.7,        # Good confidence
        'malformed': 0.6,         # Medium confidence
        'incomplete': 0.5,        # Lower confidence
    }

    # Calculate weighted average based on change types
    total_weight = 0
    weighted_score = 0

    for change in changes:
        for change_type, score in change_scores.items():
            if change_type in change.lower():
                weighted_score += score
                total_weight += 1
                break
        else:
            # Unknown change type - medium confidence
            weighted_score += 0.6
            total_weight += 1

    if total_weight > 0:
        confidence = weighted_score / total_weight
    else:
        confidence = 0.5  # Default medium confidence

    # Reduce confidence if too many changes were needed
    if len(changes) > 3:
        confidence *= 0.8

    # Ensure confidence is in valid range
    return max(0.0, min(1.0, confidence))