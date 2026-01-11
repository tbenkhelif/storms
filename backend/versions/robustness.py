"""
Robustness testing module for XPath selectors.

Tests XPath selectors against various page mutations to assess their robustness
in real-world scenarios where pages might change slightly.
"""

import asyncio
import random
import re
from typing import Dict, List, Any, Tuple
from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup, NavigableString
import string

class RobustnessTester:
    def __init__(self):
        self.mutations = {
            'whitespace': self.mutate_whitespace,
            'classes': self.mutate_classes,
            'siblings': self.mutate_siblings,
            'wrappers': self.mutate_wrappers,
            'ids': self.mutate_ids,
            'attributes': self.mutate_attributes
        }

    def mutate_whitespace(self, html: str) -> str:
        """Add/remove random whitespace and newlines"""
        soup = BeautifulSoup(html, 'html.parser')

        # Find all text nodes and randomly modify whitespace
        for element in soup.find_all(string=True):
            if isinstance(element, NavigableString):
                original_text = str(element)

                # Skip if it's just whitespace
                if not original_text.strip():
                    continue

                # Randomly add extra spaces, tabs, or newlines
                mutations = []
                if random.random() < 0.3:  # 30% chance to add leading whitespace
                    mutations.append(random.choice([' ', '\t', '\n']) * random.randint(1, 3))

                mutations.append(original_text.strip())

                if random.random() < 0.3:  # 30% chance to add trailing whitespace
                    mutations.append(random.choice([' ', '\t', '\n']) * random.randint(1, 3))

                new_text = ''.join(mutations)
                element.replace_with(new_text)

        return str(soup)

    def mutate_classes(self, html: str) -> str:
        """Rename CSS classes to different names"""
        soup = BeautifulSoup(html, 'html.parser')

        # Collect all existing classes
        all_classes = set()
        for element in soup.find_all(attrs={'class': True}):
            if isinstance(element.get('class'), list):
                all_classes.update(element['class'])
            else:
                all_classes.add(element['class'])

        # Create mapping of old classes to new classes
        class_mapping = {}
        for cls in all_classes:
            # Generate a new random class name
            new_class = 'rnd_' + ''.join(random.choices(string.ascii_lowercase, k=6))
            class_mapping[cls] = new_class

        # Apply the mapping
        for element in soup.find_all(attrs={'class': True}):
            if isinstance(element.get('class'), list):
                element['class'] = [class_mapping.get(cls, cls) for cls in element['class']]
            else:
                element['class'] = class_mapping.get(element['class'], element['class'])

        return str(soup)

    def mutate_siblings(self, html: str) -> str:
        """Reorder sibling elements randomly"""
        soup = BeautifulSoup(html, 'html.parser')

        # Find elements that have multiple children
        for parent in soup.find_all():
            children = [child for child in parent.children if hasattr(child, 'name')]

            if len(children) > 2:  # Only reorder if there are multiple children
                # Randomly shuffle some siblings (not all, to maintain some structure)
                if random.random() < 0.3:  # 30% chance to reorder
                    # Extract children
                    extracted = []
                    for child in children:
                        extracted.append(child.extract())

                    # Shuffle and re-insert
                    random.shuffle(extracted)
                    for child in extracted:
                        parent.append(child)

        return str(soup)

    def mutate_wrappers(self, html: str) -> str:
        """Add wrapper divs around random elements"""
        soup = BeautifulSoup(html, 'html.parser')

        # Find elements to potentially wrap (avoid wrapping critical elements)
        wrappable_elements = []
        for element in soup.find_all(['p', 'span', 'a', 'button', 'input', 'img']):
            if element.parent and element.parent.name not in ['script', 'style', 'head']:
                wrappable_elements.append(element)

        # Randomly wrap some elements
        num_to_wrap = min(3, len(wrappable_elements) // 3)  # Wrap up to 1/3 of elements, max 3
        elements_to_wrap = random.sample(wrappable_elements, num_to_wrap)

        for element in elements_to_wrap:
            if element.parent:  # Make sure element still has a parent
                # Create wrapper div with random attributes
                wrapper = soup.new_tag('div')
                wrapper['class'] = f'wrapper_{random.randint(1000, 9999)}'

                if random.random() < 0.5:  # 50% chance to add data attributes
                    wrapper[f'data-wrapper'] = 'true'

                # Insert wrapper and move element into it
                element.insert_before(wrapper)
                element.extract()
                wrapper.append(element)

        return str(soup)

    def mutate_ids(self, html: str) -> str:
        """Change ID attributes to different values"""
        soup = BeautifulSoup(html, 'html.parser')

        # Find all elements with IDs
        for element in soup.find_all(attrs={'id': True}):
            original_id = element['id']

            # Only change some IDs (not all, to maintain some structure)
            if random.random() < 0.4:  # 40% chance to change
                new_id = f"new_{original_id}_{random.randint(100, 999)}"
                element['id'] = new_id

        return str(soup)

    def mutate_attributes(self, html: str) -> str:
        """Add random data attributes and modify non-critical attributes"""
        soup = BeautifulSoup(html, 'html.parser')

        # Add random data attributes to some elements
        for element in soup.find_all():
            if random.random() < 0.2:  # 20% chance to add data attribute
                data_attr = f'data-test-{random.randint(1000, 9999)}'
                element[data_attr] = f'value_{random.randint(1, 100)}'

            # Modify style attributes (if present)
            if element.get('style') and random.random() < 0.3:
                current_style = element['style']
                extra_style = f'margin: {random.randint(0, 5)}px;'
                element['style'] = f'{current_style}; {extra_style}'

        return str(soup)

    async def test_xpath_on_html(self, xpath: str, html: str) -> Tuple[bool, int, str]:
        """Test if XPath works on given HTML. Returns (success, match_count, error_msg)"""
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                # Set content directly
                await page.set_content(html, wait_until='domcontentloaded')

                # Test the XPath
                elements = await page.query_selector_all(f"xpath={xpath}")
                match_count = len(elements)

                await browser.close()
                return True, match_count, None

            except Exception as e:
                if 'browser' in locals():
                    await browser.close()
                return False, 0, str(e)

async def test_robustness(xpath: str, original_html: str, url: str) -> Dict[str, Any]:
    """
    Test XPath against mutated versions of the page.
    Returns robustness score and detailed results.
    """
    tester = RobustnessTester()

    # First, test on original HTML to get baseline
    original_success, original_count, original_error = await tester.test_xpath_on_html(xpath, original_html)

    if not original_success or original_count == 0:
        return {
            "score": 0.0,
            "passed": [],
            "failed": list(tester.mutations.keys()),
            "details": {
                "error": "XPath failed on original HTML",
                "original_error": original_error
            }
        }

    results = {}
    passed = []
    failed = []

    # Test each mutation type
    for mutation_name, mutation_func in tester.mutations.items():
        try:
            # Apply mutation
            mutated_html = mutation_func(original_html)

            # Test XPath on mutated HTML
            success, count, error = await tester.test_xpath_on_html(xpath, mutated_html)

            # Consider it a pass if it still finds at least one element
            mutation_passed = success and count > 0

            if mutation_passed:
                passed.append(mutation_name)
            else:
                failed.append(mutation_name)

            results[mutation_name] = {
                "passed": mutation_passed,
                "match_count": count,
                "error": error,
                "original_count": original_count
            }

        except Exception as e:
            failed.append(mutation_name)
            results[mutation_name] = {
                "passed": False,
                "match_count": 0,
                "error": f"Mutation failed: {str(e)}",
                "original_count": original_count
            }

    # Calculate overall robustness score
    total_tests = len(tester.mutations)
    passed_tests = len(passed)
    score = passed_tests / total_tests if total_tests > 0 else 0.0

    # Provide detailed analysis
    details = {
        "total_mutations": total_tests,
        "passed_mutations": passed_tests,
        "original_match_count": original_count,
        "mutation_results": results,
        "analysis": _analyze_robustness_results(passed, failed, results)
    }

    return {
        "score": score,
        "passed": passed,
        "failed": failed,
        "details": details
    }

def _analyze_robustness_results(passed: List[str], failed: List[str], results: Dict[str, Any]) -> Dict[str, str]:
    """Analyze robustness test results and provide insights"""
    analysis = {}

    # Overall assessment
    pass_rate = len(passed) / (len(passed) + len(failed)) * 100
    if pass_rate >= 90:
        analysis["overall"] = "Highly robust - survives most page changes"
    elif pass_rate >= 70:
        analysis["overall"] = "Moderately robust - handles common changes well"
    elif pass_rate >= 50:
        analysis["overall"] = "Somewhat fragile - vulnerable to structural changes"
    else:
        analysis["overall"] = "Fragile - likely to break with page modifications"

    # Specific insights
    insights = []

    if "whitespace" in failed:
        insights.append("Sensitive to whitespace changes - may use text() matching")

    if "classes" in failed:
        insights.append("Relies on CSS classes - vulnerable to styling changes")

    if "siblings" in failed:
        insights.append("Uses positional selectors - fragile to content reordering")

    if "wrappers" in failed:
        insights.append("Sensitive to DOM structure - may break with layout changes")

    if "ids" in failed:
        insights.append("Depends on ID attributes - vulnerable if IDs change")

    if "attributes" in failed:
        insights.append("Sensitive to attribute changes")

    # Positive insights
    if "whitespace" in passed:
        insights.append("Handles whitespace changes well")

    if "siblings" in passed:
        insights.append("Robust against element reordering")

    if "wrappers" in passed:
        insights.append("Survives structural DOM changes")

    if not insights:
        insights.append("No specific vulnerabilities identified")

    analysis["insights"] = "; ".join(insights)

    return analysis

def get_robustness_display(score: float) -> Dict[str, str]:
    """Get display information for robustness score"""
    percentage = score * 100

    if percentage >= 90:
        return {
            "icon": "🛡️🛡️🛡️",
            "label": "Highly Robust",
            "color": "green",
            "description": f"Survives {percentage:.0f}% of page changes"
        }
    elif percentage >= 70:
        return {
            "icon": "🛡️🛡️",
            "label": "Moderately Robust",
            "color": "yellow",
            "description": f"Survives {percentage:.0f}% of page changes"
        }
    else:
        return {
            "icon": "🛡️",
            "label": "Fragile",
            "color": "red",
            "description": f"Survives only {percentage:.0f}% of page changes"
        }