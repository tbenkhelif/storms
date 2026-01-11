"""
V3 Enterprise: Agentic XPath generation with Claude tool use and self-correction
"""

import asyncio
import json
import re
from typing import Dict, List, Any, Optional, Tuple
import os
from dotenv import load_dotenv

load_dotenv()

try:
    from playwright.async_api import async_playwright, Browser, Page
    import anthropic
    from bs4 import BeautifulSoup
    from .robustness import test_robustness, get_robustness_display

    # Initialize Claude client
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    V3_AVAILABLE = True
except ImportError as e:
    print(f"V3 dependencies not available: {e}")
    V3_AVAILABLE = False
    client = None

async def execute_tool(name: str, input_data: dict, page: Page, soup: BeautifulSoup) -> str:
    """Execute a tool function and return string result for Claude"""

    try:
        if name == "inspect_page":
            return await inspect_page_tool(input_data, page, soup)
        elif name == "validate_xpath":
            return await validate_xpath_tool(input_data, page)
        elif name == "get_context":
            return await get_context_tool(input_data, page, soup)
        else:
            return f"Error: Unknown tool '{name}'"
    except Exception as e:
        return f"Error executing {name}: {str(e)}"

async def inspect_page_tool(input_data: dict, page: Page, soup: BeautifulSoup) -> str:
    """Tool to inspect page elements based on different criteria"""

    selector_type = input_data.get("selector_type", "text")
    query = input_data.get("query", "")

    if not query:
        return "Error: query parameter is required"

    results = []

    try:
        if selector_type == "text":
            # Find elements containing specific text
            elements = soup.find_all(string=re.compile(re.escape(query), re.I))
            for element in elements[:10]:  # Limit to first 10
                parent = element.parent if element.parent else element
                xpath = generate_xpath_for_element(parent, soup)
                results.append({
                    "text": element.strip() if hasattr(element, 'strip') else str(element),
                    "tag": parent.name if parent else "text",
                    "xpath": xpath,
                    "attributes": dict(parent.attrs) if parent and hasattr(parent, 'attrs') else {}
                })

        elif selector_type == "tag":
            # Find elements by tag name
            elements = soup.find_all(query.lower())
            for element in elements[:10]:  # Limit to first 10
                xpath = generate_xpath_for_element(element, soup)
                text = element.get_text(strip=True)[:100]  # First 100 chars
                results.append({
                    "tag": element.name,
                    "text": text,
                    "xpath": xpath,
                    "attributes": dict(element.attrs) if hasattr(element, 'attrs') else {}
                })

        elif selector_type == "attribute":
            # Find elements with specific attribute values
            attr_name, attr_value = query.split("=", 1) if "=" in query else (query, None)
            if attr_value:
                elements = soup.find_all(attrs={attr_name: re.compile(re.escape(attr_value), re.I)})
            else:
                elements = soup.find_all(attrs={attr_name: True})

            for element in elements[:10]:  # Limit to first 10
                xpath = generate_xpath_for_element(element, soup)
                text = element.get_text(strip=True)[:50]
                results.append({
                    "tag": element.name,
                    "text": text,
                    "xpath": xpath,
                    "attributes": dict(element.attrs) if hasattr(element, 'attrs') else {}
                })

    except Exception as e:
        return f"Error during inspection: {str(e)}"

    if not results:
        return f"No elements found for {selector_type} query: '{query}'"

    return json.dumps({
        "found": len(results),
        "elements": results
    }, indent=2)

async def validate_xpath_tool(input_data: dict, page: Page) -> str:
    """Tool to validate an XPath and return details about matches"""

    xpath = input_data.get("xpath", "")
    if not xpath:
        return "Error: xpath parameter is required"

    try:
        # Use Playwright to evaluate the XPath
        elements = await page.query_selector_all(f"xpath={xpath}")

        if not elements:
            return json.dumps({
                "valid": False,
                "count": 0,
                "element_preview": None,
                "message": "XPath matches no elements"
            })

        # Get details about the first matching element
        first_element = elements[0]
        tag_name = await first_element.evaluate("el => el.tagName.toLowerCase()")
        text_content = await first_element.evaluate("el => el.textContent?.trim().substring(0, 100) || ''")
        outer_html = await first_element.evaluate("el => el.outerHTML.substring(0, 200)")

        # Get attributes
        attributes = await first_element.evaluate("""
            el => {
                const attrs = {};
                for (let attr of el.attributes) {
                    attrs[attr.name] = attr.value;
                }
                return attrs;
            }
        """)

        result = {
            "valid": True,
            "count": len(elements),
            "element_preview": {
                "tag": tag_name,
                "text": text_content,
                "attributes": attributes,
                "html_preview": outer_html
            }
        }

        if len(elements) > 1:
            result["warning"] = f"XPath matches {len(elements)} elements - may be too broad"

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({
            "valid": False,
            "count": 0,
            "element_preview": None,
            "error": str(e)
        })

async def get_context_tool(input_data: dict, page: Page, soup: BeautifulSoup) -> str:
    """Tool to get surrounding context for an element"""

    xpath = input_data.get("xpath", "")
    if not xpath:
        return "Error: xpath parameter is required"

    try:
        # Find the element using the XPath
        element = await page.query_selector(f"xpath={xpath}")
        if not element:
            return "Error: XPath does not match any element"

        # Get parent and sibling information
        context_info = await element.evaluate("""
            el => {
                const parent = el.parentElement;
                const siblings = parent ? Array.from(parent.children) : [];
                const elementIndex = siblings.indexOf(el);

                return {
                    parent: parent ? {
                        tag: parent.tagName.toLowerCase(),
                        attributes: Object.fromEntries(Array.from(parent.attributes).map(attr => [attr.name, attr.value])),
                        text: parent.textContent?.trim().substring(0, 100) || ''
                    } : null,
                    siblings_count: siblings.length,
                    element_index: elementIndex,
                    previous_sibling: elementIndex > 0 ? {
                        tag: siblings[elementIndex - 1].tagName.toLowerCase(),
                        text: siblings[elementIndex - 1].textContent?.trim().substring(0, 50) || ''
                    } : null,
                    next_sibling: elementIndex < siblings.length - 1 ? {
                        tag: siblings[elementIndex + 1].tagName.toLowerCase(),
                        text: siblings[elementIndex + 1].textContent?.trim().substring(0, 50) || ''
                    } : null
                }
            }
        """)

        return json.dumps(context_info, indent=2)

    except Exception as e:
        return f"Error getting context: {str(e)}"

def generate_xpath_for_element(element, soup: BeautifulSoup) -> str:
    """Generate a basic XPath for a BeautifulSoup element"""

    if not element or not hasattr(element, 'name'):
        return "//text()"

    # Start with tag name
    path_parts = []
    current = element

    # Walk up the tree to build XPath
    while current and hasattr(current, 'name'):
        tag = current.name

        # Add position predicate if there are siblings with same tag
        if current.parent:
            siblings = [s for s in current.parent.children if hasattr(s, 'name') and s.name == tag]
            if len(siblings) > 1:
                position = siblings.index(current) + 1
                path_parts.append(f"{tag}[{position}]")
            else:
                path_parts.append(tag)
        else:
            path_parts.append(tag)

        current = current.parent

        # Don't go beyond reasonable depth
        if len(path_parts) > 8:
            break

    # Reverse to get root-to-element order
    path_parts.reverse()

    # Build XPath
    if path_parts:
        return "//" + "/".join(path_parts)
    else:
        return "//body"

def calculate_robustness_score(xpath: str, element_info: dict) -> Tuple[int, List[str]]:
    """Calculate robustness score for an XPath"""

    score = 0
    reasons = []

    # Text content usage
    if "text()" in xpath or "contains(" in xpath:
        score += 2
        reasons.append("+2: Uses text content (stable)")

    # Aria-label usage
    if "aria-label" in xpath:
        score += 2
        reasons.append("+2: Uses aria-label (accessible)")

    # ID usage
    if "@id" in xpath and not xpath.count("[") > 2:
        score += 1
        reasons.append("+1: Uses ID attribute")

    # Class-only selector (neutral)
    if "@class" in xpath and "@id" not in xpath and "text()" not in xpath:
        reasons.append("0: Uses class attribute (moderate stability)")

    # Position/index usage (fragile)
    if re.search(r'\[\d+\]', xpath):
        score -= 1
        reasons.append("-1: Uses positional selectors (fragile)")

    # Multiple predicates (complex but potentially brittle)
    predicate_count = xpath.count("[")
    if predicate_count > 3:
        score -= 1
        reasons.append("-1: Complex selector with many conditions")

    # Check if it's overly specific
    if xpath.count("/") > 6:
        score -= 1
        reasons.append("-1: Very deep/specific path")

    return max(0, score), reasons

async def v3_generate(url: str, instruction: str) -> Dict[str, Any]:
    """
    V3 Enterprise: Generate XPath using Claude with tool use for self-correction
    """

    if not V3_AVAILABLE:
        return {
            "xpath": "//body",
            "validated": False,
            "match_count": 0,
            "element_info": "V3 dependencies not available (anthropic, playwright, beautifulsoup4)",
            "process_log": [{"step": "dependency_check", "status": "failed", "details": "Missing required packages"}],
            "robustness_score": 0,
            "score_reasons": ["Dependencies not available"]
        }

    if not client:
        return {
            "xpath": "//body",
            "validated": False,
            "match_count": 0,
            "element_info": "ANTHROPIC_API_KEY not configured",
            "process_log": [{"step": "api_key_check", "status": "failed", "details": "Missing API key"}],
            "robustness_score": 0,
            "score_reasons": ["API key not configured"]
        }

    process_log = []

    def log_step(step: str, status: str, details: str = None):
        entry = {"step": step, "status": status}
        if details:
            entry["details"] = details
        process_log.append(entry)

    log_step("initialize", "started", "Starting V3 Enterprise generation with Claude tool use")

    async with async_playwright() as p:
        try:
            # Launch browser
            log_step("browser_launch", "running", "Launching headless browser")
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Navigate to URL
            log_step("page_load", "running", f"Loading page: {url}")
            await page.goto(url, timeout=15000)
            await page.wait_for_load_state('networkidle', timeout=10000)

            # Get page content for parsing
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            log_step("page_load", "success", "Page loaded successfully")
            log_step("claude_analysis", "running", "Starting Claude analysis with tool use")

            # System prompt for Claude
            system_prompt = """You are an expert at generating robust XPath selectors for web automation. You have access to tools that let you inspect the page and validate your XPath attempts.

Your goal: Find a ROBUST XPath that will work even if the page changes slightly.

Available tools:
1. inspect_page: Find elements by text, tag, or attribute
2. validate_xpath: Test if an XPath works and get element details
3. get_context: Get surrounding HTML context for an element

KEY PRINCIPLES:
- Focus on the user's intent, not literal words
- ALWAYS validate your XPath before finalizing it
- If validation returns 0 matches, you MUST try a different approach
- Use multiple inspect_page calls with different search terms if needed

Process:
1. Inspect the page to understand what elements exist
2. Generate an XPath based on your findings
3. Validate it to ensure it matches elements (REQUIRED)
4. If no matches, revise your approach and try again
5. Prefer stable selectors (text content, IDs, aria-labels)
6. Avoid position-based or deeply nested selectors

Only return an XPath that you have validated and confirmed works."""

            user_prompt = f"""The instruction is: "{instruction}"

Please find a robust XPath selector for this instruction.
Start by inspecting the page to understand what elements are available.
IMPORTANT: You MUST validate your XPath to ensure it actually matches elements on the page before finalizing it.
If your XPath doesn't match any elements, try a different approach."""

            # Claude conversation with tools
            conversation_history = []
            max_iterations = 10
            iteration = 0
            final_xpath = None
            tool_use_count = 0

            while iteration < max_iterations:
                iteration += 1
                log_step("claude_iteration", "running", f"Claude iteration {iteration}")

                try:
                    # Prepare messages
                    messages = conversation_history.copy()
                    if not messages:
                        messages.append({
                            "role": "user",
                            "content": user_prompt
                        })

                    # After several tool uses, encourage validation and final answer
                    if tool_use_count >= 4 and tool_use_count < 7:
                        messages.append({
                            "role": "user",
                            "content": "Please validate your XPath to ensure it matches elements. If it doesn't match, try a different approach. If it does match, provide your final XPath."
                        })
                    elif tool_use_count >= 7:
                        messages.append({
                            "role": "user",
                            "content": "You've investigated enough. Please provide your best XPath now based on what you've learned."
                        })

                    # Define available tools for Claude
                    tools = [
                        {
                            "name": "inspect_page",
                            "description": "Inspect page elements by text content, tag name, or attributes",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "selector_type": {
                                        "type": "string",
                                        "enum": ["text", "tag", "attribute"],
                                        "description": "Type of search to perform"
                                    },
                                    "query": {
                                        "type": "string",
                                        "description": "Search query (text to find, tag name, or attribute=value)"
                                    }
                                },
                                "required": ["selector_type", "query"]
                            }
                        },
                        {
                            "name": "validate_xpath",
                            "description": "Validate an XPath selector and get details about matching elements",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "xpath": {
                                        "type": "string",
                                        "description": "XPath expression to validate"
                                    }
                                },
                                "required": ["xpath"]
                            }
                        },
                        {
                            "name": "get_context",
                            "description": "Get surrounding HTML context for an element",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "xpath": {
                                        "type": "string",
                                        "description": "XPath of element to get context for"
                                    }
                                },
                                "required": ["xpath"]
                            }
                        }
                    ]

                    # Call Claude with tools (or force no tools after enough usage)
                    tool_choice = {"type": "none"} if tool_use_count >= 7 else {"type": "auto"}

                    response = client.messages.create(
                        model="claude-sonnet-4-5-20250929",
                        system=system_prompt,
                        messages=messages,
                        tools=tools if tool_use_count < 7 else [],
                        tool_choice=tool_choice,
                        max_tokens=4000
                    )

                    # Add Claude's response to conversation
                    conversation_history.append({
                        "role": "assistant",
                        "content": response.content
                    })

                    # Process tool calls
                    tool_results = []
                    has_tool_calls = False

                    for content_block in response.content:
                        if content_block.type == "tool_use":
                            has_tool_calls = True
                            tool_use_count += 1  # Track tool usage
                            tool_name = content_block.name
                            tool_input = content_block.input
                            tool_id = content_block.id

                            log_step("tool_execution", "running", f"Executing {tool_name}: {tool_input}")

                            # Execute the tool
                            tool_result = await execute_tool(tool_name, tool_input, page, soup)

                            tool_results.append({
                                "tool_use_id": tool_id,
                                "content": tool_result
                            })

                            log_step("tool_execution", "success", f"{tool_name} completed")

                    # If Claude used tools, send results back
                    if has_tool_calls:
                        conversation_history.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": result["tool_use_id"],
                                    "content": result["content"]
                                }
                                for result in tool_results
                            ]
                        })
                    else:
                        # No tools used, Claude provided final answer
                        final_response = ""
                        for content_block in response.content:
                            if content_block.type == "text":
                                final_response += content_block.text

                        # Extract XPath from Claude's response - improved extraction
                        # Look for XPath patterns in the response
                        xpath_patterns = [
                            r'(?:xpath|XPath|selector)[:\s]*[`"\'](//[^`"\']+?)[`"\']',  # xpath: "//path"
                            r'^\s*(//[^\n\r]+?)\s*$',  # Standalone XPath on its own line
                            r'(?:final|result|answer)[:\s]*[`"\'](//[^`"\']+?)[`"\']',  # final: "//path"
                            r'```(?:xpath)?\s*(//.*?)\s*```',  # Code blocks with XPath
                            r'`(//[^`]+?)`',  # Single backticks around XPath
                            r'(//\w+[^\\n\\r]*)',  # Any reasonable //path - simplified
                        ]

                        final_xpath = None
                        for i, pattern in enumerate(xpath_patterns):
                            match = re.search(pattern, final_response, re.IGNORECASE | re.MULTILINE)
                            if match:
                                raw_xpath = match.group(1)

                                # Clean up the XPath more carefully
                                final_xpath = raw_xpath.strip()

                                # Only remove quotes/backticks from start/end, not everywhere
                                while final_xpath and final_xpath[0] in '"\'`':
                                    final_xpath = final_xpath[1:]
                                while final_xpath and final_xpath[-1] in '"\'`,':
                                    final_xpath = final_xpath[:-1]

                                final_xpath = final_xpath.strip()

                                if len(final_xpath) > 5 and final_xpath.startswith('//'):  # Reasonable XPath
                                    log_step("xpath_extracted", "success", f"Final XPath: {final_xpath}")
                                    break

                        if final_xpath:
                            break
                        else:
                            # Log more details for debugging
                            log_step("xpath_extraction", "failed", f"Could not extract XPath. Response length: {len(final_response)}. Content preview: {final_response[:300]}")
                            continue

                except Exception as e:
                    error_msg = f"Error in iteration {iteration}: {str(e)}"
                    log_step("claude_iteration", "error", error_msg)

                    # If it's an API key issue, fail fast
                    if "api" in str(e).lower() or "auth" in str(e).lower():
                        log_step("claude_analysis", "failed", f"API authentication failed: {str(e)}")
                        break
                    continue

            if not final_xpath:
                log_step("claude_analysis", "failed", "Could not generate XPath after all iterations")
                await browser.close()
                return {
                    "xpath": "//body",
                    "validated": False,
                    "match_count": 0,
                    "element_info": "Failed to generate XPath",
                    "process_log": process_log,
                    "robustness_score": 0,
                    "score_reasons": ["Failed to generate XPath"]
                }

            # Validation with retry logic
            log_step("final_validation", "running", f"Validating XPath: {final_xpath}")

            validation_attempts = 0
            max_validation_retries = 3
            validated_xpath = None

            while validation_attempts < max_validation_retries:
                validation_attempts += 1

                try:
                    elements = await page.query_selector_all(f"xpath={final_xpath}")
                    match_count = len(elements)

                    if match_count > 0:
                        # Success - XPath matches elements
                        validated_xpath = final_xpath
                        break
                    else:
                        # XPath doesn't match - need to retry
                        log_step("validation_retry", "warning", f"XPath matches 0 elements (attempt {validation_attempts}/{max_validation_retries})")

                        if validation_attempts < max_validation_retries:
                            # Ask Claude to try again with feedback
                            retry_prompt = f"""Your XPath '{final_xpath}' doesn't match any elements on the page.

The original instruction was: {instruction}

Please provide an alternative XPath that will actually match elements. Consider:
                            - Using less specific selectors
                            - Trying different attributes or text patterns
                            - Looking for common UI patterns (buttons, links, inputs)

Provide just the XPath, nothing else."""

                            retry_response = client.messages.create(
                                model="claude-sonnet-4-5-20250929",
                                system="You are an XPath expert. Generate a working XPath selector.",
                                messages=[{"role": "user", "content": retry_prompt}],
                                max_tokens=500
                            )

                            # Extract new XPath from retry response
                            retry_text = retry_response.content[0].text if retry_response.content else ""

                            # Try to extract XPath from retry response
                            xpath_patterns = [
                                r'(//[^\n\r"\'"`]+)',  # Direct XPath
                                r'[`"\']+(//[^`"\'"`]+)[`"\']+',  # Quoted XPath
                            ]

                            for pattern in xpath_patterns:
                                match = re.search(pattern, retry_text, re.IGNORECASE)
                                if match:
                                    final_xpath = match.group(1).strip()
                                    log_step("xpath_retry", "success", f"New XPath to try: {final_xpath}")
                                    break
                            else:
                                log_step("xpath_retry", "failed", "Could not extract alternative XPath")
                                break

                except Exception as e:
                    log_step("validation_error", "error", f"Validation error: {str(e)}")
                    break

            # Check if we found a valid XPath
            if validated_xpath:
                final_xpath = validated_xpath
                elements = await page.query_selector_all(f"xpath={final_xpath}")
                match_count = len(elements)

                if match_count > 0:
                    first_element = elements[0]
                    tag_name = await first_element.evaluate("el => el.tagName.toLowerCase()")
                    text_content = await first_element.evaluate("el => el.textContent?.trim().substring(0, 100) || ''")

                    element_info = f"{tag_name}"
                    if text_content:
                        element_info += f" with text '{text_content}'"

                    # Calculate basic robustness score from XPath structure
                    basic_score, basic_reasons = calculate_robustness_score(final_xpath, {"tag": tag_name, "text": text_content})

                    log_step("final_validation", "success", f"XPath validates: {match_count} matches")
                    log_step("basic_scoring", "completed", f"Basic score: {basic_score}/5")

                    # Run comprehensive robustness testing
                    log_step("robustness_testing", "running", "Testing XPath against page mutations")

                    try:
                        robustness_result = await test_robustness(final_xpath, content, url)
                        robustness_percentage = robustness_result["score"] * 100
                        robustness_display = get_robustness_display(robustness_result["score"])

                        log_step("robustness_testing", "success", f"Robustness: {robustness_percentage:.1f}% ({len(robustness_result['passed'])}/{len(robustness_result['passed']) + len(robustness_result['failed'])} mutations survived)")

                        # Combine basic score with robustness testing
                        final_score = min(5, basic_score + (robustness_result["score"] * 2))  # Max 5 points
                        final_reasons = basic_reasons + [f"Robustness: {robustness_display['label']} ({robustness_percentage:.0f}%)"]

                    except Exception as e:
                        log_step("robustness_testing", "error", f"Robustness test failed: {str(e)}")
                        robustness_result = {
                            "score": 0.5,  # Assume moderate robustness if test fails
                            "passed": [],
                            "failed": ["test_error"],
                            "details": {"error": str(e)}
                        }
                        robustness_display = {
                            "icon": "⚠️",
                            "label": "Unknown",
                            "color": "gray",
                            "description": "Robustness test failed"
                        }
                        final_score = basic_score
                        final_reasons = basic_reasons + ["Robustness test failed"]

                    await browser.close()

                    return {
                        "xpath": final_xpath,
                        "validated": True,
                        "match_count": match_count,
                        "element_info": element_info,
                        "process_log": process_log,
                        "robustness_score": final_score,
                        "score_reasons": final_reasons,
                        "robustness_testing": robustness_result,
                        "robustness_display": robustness_display
                    }
            else:
                # All validation attempts failed
                log_step("final_validation", "failed", f"XPath validation failed after {validation_attempts} attempts")

                await browser.close()

                return {
                    "xpath": final_xpath,
                    "validated": False,
                    "match_count": 0,
                    "element_info": f"Validation failed after {validation_attempts} attempts",
                    "process_log": process_log,
                    "robustness_score": 0,
                    "score_reasons": ["No matching elements found"]
                }

        except Exception as e:
            log_step("critical_error", "failed", str(e))
            if 'browser' in locals():
                await browser.close()

            return {
                "xpath": "//body",
                "validated": False,
                "match_count": 0,
                "element_info": f"Critical error: {str(e)}",
                "process_log": process_log,
                "robustness_score": 0,
                "score_reasons": ["Critical error occurred"]
            }