"""
XPath utilities for validation and fixing
"""

from .xpath_validator import validate_xpath_syntax, test_xpath_on_page, analyze_xpath_structure
from .xpath_fixer import fix_xpath, fix_truncated_xpath, balance_brackets_and_quotes

__all__ = [
    'validate_xpath_syntax',
    'test_xpath_on_page',
    'analyze_xpath_structure',
    'fix_xpath',
    'fix_truncated_xpath',
    'balance_brackets_and_quotes'
]