"""
V3 Simplified: Elegant XPath generation without overcomplicated tool use
"""

import asyncio
import re
from typing import Dict, Any, Optional, List, Tuple
import os
from dotenv import load_dotenv

load_dotenv()

try:
    from playwright.async_api import async_playwright
    import anthropic
    from bs4 import BeautifulSoup

    # Try importing utils with different paths
    try:
        from utils.xpath_validator import validate_xpath_syntax
        from utils.xpath_fixer import fix_xpath
    except ImportError:
        # Fallback: disable validation/fixing if utils not available
        def validate_xpath_syntax(xpath): return {"is_valid": True, "syntax_errors": []}
        def fix_xpath(xpath, instruction=None): return {"is_fixed": False, "fixed_xpath": xpath, "changes_made": [], "confidence": 0.0}

    # Initialize Claude client
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    V3_AVAILABLE = True
except ImportError as e:
    print(f"V3 dependencies not available: {e}")
    V3_AVAILABLE = False
    client = None
    # Fallback functions
    def validate_xpath_syntax(xpath): return {"is_valid": True, "syntax_errors": []}
    def fix_xpath(xpath, instruction=None): return {"is_fixed": False, "fixed_xpath": xpath, "changes_made": [], "confidence": 0.0}


def extract_relevant_html(soup: BeautifulSoup, instruction: str, expanded_mode: bool = False, enrichment_data: Dict = None) -> str:
    """Extract relevant HTML elements with generic approach and optional LLM enrichment"""

    # Base interactive elements - always include these
    relevant_selectors = [
        'input', 'button', 'a', 'select', 'textarea',
        '[role="button"]', '[role="link"]', '[role="textbox"]',
        '[onclick]', '[type="submit"]', '[type="button"]',
        # Table elements for data queries
        'table', 'th'
    ]

    # Always include navigation context - no specific rules
    semantic_selectors = ['nav', 'header', 'footer']

    # Use enrichment data to expand search if available
    if expanded_mode and enrichment_data and enrichment_data.get("enriched"):
        # Add LLM-suggested context areas
        if enrichment_data.get("context_areas"):
            semantic_selectors.extend(enrichment_data["context_areas"])

        # Add LLM-suggested element types to relevant selectors
        if enrichment_data.get("element_types"):
            relevant_selectors.extend(enrichment_data["element_types"])

    # Expanded mode: cast a wider net when initial generation fails
    if expanded_mode:
        semantic_selectors.extend([
            'main', '[role="main"]', '[role="navigation"]',
            '.navigation', '.nav', '.menu', '.header', '.footer',
            'section', 'article'
        ])

    elements = []
    seen_elements = set()  # Avoid duplicates
    table_rows = []  # Store table rows separately for context

    # Extract table rows with full context (important for data queries)
    tables = soup.select('table')
    for table in tables[:3]:  # Limit to 3 tables
        rows = table.select('tr')
        for row in rows[:20]:  # Limit rows per table
            row_key = row.get_text(strip=True)[:50]
            if row_key and row_key not in seen_elements:
                seen_elements.add(row_key)
                table_rows.append(row)

    # First, get elements from semantic sections if specified
    for selector in semantic_selectors:
        try:
            sections = soup.select(selector)
            for section in sections[:3]:  # Limit sections
                # Get interactive elements within this semantic section
                section_elements = section.select('a, button, input[type="submit"], input[type="button"]')
                for elem in section_elements[:15]:  # More elements in expanded mode
                    elem_key = f"{elem.name}_{elem.get('id', '')}_{elem.get('name', '')}_{elem.get_text(strip=True)[:20]}"
                    if elem_key not in seen_elements:
                        seen_elements.add(elem_key)
                        elements.append(elem)
        except:
            continue

    # Then add general interactive elements
    element_limit = 15 if expanded_mode else 10
    for selector in relevant_selectors:
        try:
            found = soup.select(selector)
            for elem in found[:element_limit]:
                elem_key = f"{elem.name}_{elem.get('id', '')}_{elem.get('name', '')}_{elem.get_text(strip=True)[:20]}"
                if elem_key not in seen_elements:
                    seen_elements.add(elem_key)
                    elements.append(elem)
        except:
            continue

    # Build simplified HTML representation
    simplified_lines = []
    total_limit = 150 if expanded_mode else 100  # More elements in expanded mode

    # First, add table rows with structure preserved (critical for data queries)
    if table_rows:
        simplified_lines.append("<!-- TABLE DATA -->")
        for row in table_rows[:30]:  # Limit table rows
            cells = row.select('td, th')
            if cells:
                cell_texts = []
                for cell in cells:
                    cell_text = cell.get_text(strip=True)[:40]
                    cell_texts.append(cell_text)
                # Include links within the row
                links = row.select('a')
                link_info = ', '.join([f"<a>{a.get_text(strip=True)}</a>" for a in links[:4]])
                row_repr = f"<tr>{'|'.join(cell_texts)}</tr>"
                if link_info:
                    row_repr += f" Actions: {link_info}"
                simplified_lines.append(row_repr)
        simplified_lines.append("<!-- END TABLE DATA -->")

    for elem in elements[:total_limit]:
        # Extract key attributes
        attrs = []
        for attr in ['id', 'name', 'class', 'type', 'placeholder', 'aria-label', 'role', 'value', 'href']:
            if elem.get(attr):
                value = elem.get(attr)
                if isinstance(value, list):  # Handle class list
                    value = ' '.join(value)
                # Longer attribute values in expanded mode
                max_length = 80 if expanded_mode else 50
                attrs.append(f'{attr}="{value[:max_length]}"')

        # Get text content (longer in expanded mode)
        text_length = 50 if expanded_mode else 30
        text = elem.get_text(strip=True)[:text_length] if elem.get_text(strip=True) else ""

        # Format as simplified HTML
        attrs_str = ' '.join(attrs) if attrs else ""
        simplified_lines.append(f"<{elem.name} {attrs_str}>{text}</{elem.name}>")

    return '\n'.join(simplified_lines)


def calculate_robustness_score(xpath: str) -> Tuple[int, List[str]]:
    """Calculate robustness score based on XPath patterns"""

    score = 50  # Start with neutral score
    reasons = []

    # Good patterns (add points)
    if '@id=' in xpath or '@id)' in xpath:
        score += 20
        reasons.append("Uses ID selector (+20)")

    if '@name=' in xpath or '@name)' in xpath:
        score += 15
        reasons.append("Uses name attribute (+15)")

    if 'text()' in xpath or 'contains(text()' in xpath:
        score += 15
        reasons.append("Uses text content (+15)")

    if '@aria-label' in xpath:
        score += 15
        reasons.append("Uses ARIA label (+15)")

    if '@role=' in xpath:
        score += 10
        reasons.append("Uses ARIA role (+10)")

    # Neutral patterns
    if '@type=' in xpath:
        score += 5
        reasons.append("Uses type attribute (+5)")

    # Bad patterns (subtract points)
    if re.search(r'\[\d+\]', xpath):
        score -= 20
        reasons.append("Uses position selector (-20)")

    if xpath.count('/') > 10:
        score -= 15
        reasons.append("Very deep nesting (-15)")

    if xpath.count('[') > 3:
        score -= 10
        reasons.append("Complex with many conditions (-10)")

    if '@class=' in xpath and '@id=' not in xpath:
        score -= 10
        reasons.append("Relies on CSS classes (-10)")

    # Ensure score is within bounds
    final_score = min(100, max(0, score))

    return final_score, reasons


def extract_content_terms(instruction: str) -> List[str]:
    """Extract meaningful content terms from instruction, excluding action words"""

    if not instruction:
        return []

    # Common action/stop words to exclude
    stop_words = {
        'click', 'on', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'at', 'to', 'for',
        'find', 'search', 'look', 'get', 'go', 'navigate', 'open', 'select', 'choose',
        'button', 'link', 'element', 'page', 'tab', 'menu', 'form', 'field'
    }

    # Extract potential content terms
    words = re.findall(r'\b[a-zA-Z]+\b', instruction.lower())
    content_terms = []

    for word in words:
        if (len(word) > 2 and
            word not in stop_words and
            not word.isdigit()):
            content_terms.append(word)

    # Also look for quoted phrases
    quoted_phrases = re.findall(r'["\']([^"\']+)["\']', instruction)
    for phrase in quoted_phrases:
        if len(phrase.strip()) > 2:
            content_terms.append(phrase.strip().lower())

    return list(set(content_terms))  # Remove duplicates


async def analyze_intent(instruction: str) -> str:
    """Quick intent analysis to identify target element type"""

    if not client:
        return ""

    try:
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            messages=[{"role": "user", "content": f"""Briefly analyze this web interaction instruction:
"{instruction}"

In exactly 3 short lines, state:
1. TARGET TYPE: (button/link/input/table-cell/checkbox/etc)
2. ACTION: (click/fill/read/select/etc)
3. KEY IDENTIFIER: (text content, attribute, or position to look for)"""}],
            max_tokens=80,
            temperature=0
        )

        intent_text = response.content[0].text if response.content else ""
        return intent_text.strip()
    except:
        return ""


async def enrich_instruction_with_llm(instruction: str) -> Dict[str, Any]:
    """Use LLM to analyze instruction and suggest element types and search strategies"""

    if not client:
        return {"enriched": False}

    enrichment_prompt = f"""Analyze this user instruction and identify what type of web element they likely want to interact with.

Instruction: "{instruction}"

Respond with a JSON object containing:
1. "element_types": List of likely HTML elements (e.g., ["button", "input", "a"])
2. "search_terms": List of text content to look for
3. "attributes": List of likely attribute patterns
4. "context_areas": List of page sections to focus on (e.g., ["nav", "header", "main"])

Keep it simple and practical. Focus on the most likely elements.

Example response:
{{
  "element_types": ["button", "a"],
  "search_terms": ["Contact", "Contact Us"],
  "attributes": ["aria-label", "title"],
  "context_areas": ["nav", "header", "footer"]
}}"""

    try:
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            messages=[{"role": "user", "content": enrichment_prompt}],
            max_tokens=300,
            temperature=0.2
        )

        response_text = response.content[0].text if response.content else ""

        # Try to extract JSON
        import json
        # Look for JSON in the response
        json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
        if json_match:
            enrichment_data = json.loads(json_match.group(0))
            enrichment_data["enriched"] = True
            return enrichment_data

    except Exception as e:
        pass

    # Fallback to no enrichment
    return {"enriched": False}


async def score_xpath_quality(xpath: str, page, instruction: str) -> Tuple[int, str]:
    """Score XPath quality based on specificity and relevance"""

    try:
        elements = await page.query_selector_all(f"xpath={xpath}")
        element_count = len(elements)

        if element_count == 0:
            return 0, "No matches"

        # Base score - fewer matches = higher specificity
        if element_count == 1:
            score = 100
        elif element_count <= 3:
            score = 80
        elif element_count <= 10:
            score = 60
        else:
            score = 40

        # Content relevance bonus
        content_terms = extract_content_terms(instruction)
        if content_terms and element_count > 0:
            # Check if first element contains relevant text
            first_element = elements[0]
            try:
                element_text = await first_element.evaluate("el => (el.textContent || '').toLowerCase()")
                for term in content_terms:
                    if term in element_text:
                        score += 20
                        break
            except:
                pass

        # Penalty for overly generic selectors
        if xpath in ["//a", "//button", "//input", "//a[@role='button']", "//button[@type='button']"]:
            score -= 30

        return max(0, min(100, score)), f"{element_count} matches"

    except Exception as e:
        return 0, f"Error: {str(e)}"


async def quick_refine_xpath(xpath: str, instruction: str, page) -> str:
    """Simple content-based refinement approach"""

    content_terms = extract_content_terms(instruction)
    refinement_candidates = []

    # Only use content terms for refinement - no hardcoded rules
    if content_terms:
        for term in content_terms:
            term_capitalized = term.capitalize()
            refinement_candidates.extend([
                # Text content matching - various capitalizations
                f"//a[contains(text(), '{term_capitalized}')]",
                f"//a[contains(text(), '{term.lower()}')]",
                f"//button[contains(text(), '{term_capitalized}')]",
                f"//button[contains(text(), '{term.lower()}')]",

                # Attribute matching
                f"//a[contains(@aria-label, '{term}')]",
                f"//button[contains(@aria-label, '{term}')]",
                f"//input[contains(@value, '{term_capitalized}')]",

                # Navigation context
                f"//nav//a[contains(text(), '{term_capitalized}')]",
                f"//header//a[contains(text(), '{term_capitalized}')]",
                f"//footer//a[contains(text(), '{term_capitalized}')]"
            ])

    # Basic fallback for button/input actions
    instruction_lower = instruction.lower()
    if any(word in instruction_lower for word in ['button', 'click', 'submit']):
        refinement_candidates.extend([
            "//button[not(@disabled)]",
            "//input[@type='submit']",
            "//a[@role='button']"
        ])

    # Try refinements and score them
    best_xpath = xpath
    best_score = 0

    for candidate in refinement_candidates:
        try:
            score, description = await score_xpath_quality(candidate, page, instruction)
            if score > best_score:
                best_xpath = candidate
                best_score = score
        except:
            continue

    return best_xpath


def generate_adaptive_prompt(instruction: str, attempt_number: int = 1, enrichment_data: Dict = None, intent_summary: str = None) -> Tuple[str, str]:
    """Generate clean system and user prompts with optional LLM enrichment context"""

    # Enhanced system prompt with intent understanding
    system_prompt = """You are an XPath expert. Generate a robust XPath selector based on the HTML structure provided.

CRITICAL - Understand user intent before generating:

1. ACTION WORDS imply interactive elements (buttons, not input fields):
   - "authenticate", "login", "submit", "sign in", "log in" → find submit buttons
   - "toggle", "enable", "disable", "switch", "turn on/off" → find buttons that control state
   - "delete", "remove", "edit", "modify", "update" → find action links/buttons
   - "create", "add", "new" → find buttons that create/add items

2. SUPERLATIVE/COMPARATIVE words require finding data values:
   - "most", "highest", "maximum", "largest" → find the cell with max value
   - "least", "lowest", "minimum", "smallest" → find the cell with min value
   - "first", "last", "middle", "second" → use positional selectors

3. RELATIONAL words need context traversal:
   - "next to", "beside", "associated with", "for [X]" → traverse to related elements
   - Find the context entity first, then navigate to the target

4. For TABLES: Use proper row/cell traversal:
   - //tr[contains(., 'value')]//td or //tr[td[text()='value']]//a

Rules:
1. Prefer semantic attributes: @id > @name > @aria-label > @role > @type
2. Use text content when unique and stable
3. Avoid generic selectors that match too many elements
4. Return ONLY the XPath expression, nothing else"""

    # Add enrichment context if available
    if attempt_number > 1 and enrichment_data and enrichment_data.get("enriched"):
        system_prompt += f"""

ENRICHMENT CONTEXT: Based on analysis, focus on:
- Element types: {enrichment_data.get('element_types', [])}
- Search terms: {enrichment_data.get('search_terms', [])}
- Key attributes: {enrichment_data.get('attributes', [])}"""

    # Add retry context if needed
    if attempt_number > 1:
        system_prompt += f"""

RETRY ATTEMPT #{attempt_number}: The previous attempt failed validation.
- Be more thorough in examining the provided HTML
- Consider alternative element types or broader selectors
- Focus on the most relevant elements provided"""

    # Simple user prompt
    if attempt_number > 1:
        user_prompt_prefix = f"RETRY #{attempt_number} - Previous XPath failed validation.\n\n"
    else:
        user_prompt_prefix = ""

    # Include intent analysis if available
    intent_section = ""
    if intent_summary:
        intent_section = f"Intent Analysis:\n{intent_summary}\n\n"

    user_prompt = f"{user_prompt_prefix}{intent_section}Task: {instruction}\nURL: {{url}}\n\nRelevant HTML elements:\n{{html}}\n\nGenerate the XPath:"

    return system_prompt, user_prompt


async def v3_generate(url: str, instruction: str) -> Dict[str, Any]:
    """
    V3 Simplified: Elegant XPath generation without complex tool use
    """

    if not V3_AVAILABLE or not client:
        return {
            "xpath": "//body",
            "validated": False,
            "match_count": 0,
            "element_info": "V3 dependencies not available",
            "process_log": [{"step": "dependency_check", "status": "failed"}]
        }

    process_log = []

    def log_step(step: str, status: str, details: str = None):
        entry = {"step": step, "status": status}
        if details:
            entry["details"] = details
        process_log.append(entry)

    async with async_playwright() as p:
        try:
            # Launch browser and load page
            log_step("browser_launch", "running", "Starting headless browser")
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()

            # Navigate to URL with appropriate timeout
            log_step("page_load", "running", f"Loading {url}")
            await page.goto(url, timeout=20000, wait_until='domcontentloaded')

            # Wait for dynamic content (longer for heavy sites like YouTube)
            await page.wait_for_timeout(4000)

            # Get page content
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            log_step("page_load", "success", "Page loaded successfully")

            # Adaptive XPath generation with intelligent failure recovery
            generated_xpath = None
            enrichment_data = None

            # Pre-analyze intent for better XPath generation
            log_step("intent_analysis", "running", "Analyzing user intent")
            intent_summary = await analyze_intent(instruction)
            if intent_summary:
                log_step("intent_analysis", "success", f"Intent: {intent_summary[:100]}")
            else:
                log_step("intent_analysis", "skipped", "No intent analysis available")

            for attempt in range(1, 3):  # Maximum 2 attempts
                # On retry, use LLM enrichment to understand what we're really looking for
                if attempt > 1 and not enrichment_data:
                    log_step("llm_enrichment", "running", "Analyzing instruction with LLM for better context")
                    enrichment_data = await enrich_instruction_with_llm(instruction)
                    if enrichment_data.get("enriched"):
                        log_step("llm_enrichment", "success", f"Got enrichment: {enrichment_data.get('element_types', [])}")
                    else:
                        log_step("llm_enrichment", "warning", "No enrichment available")

                # Extract relevant HTML (expanded mode for retry)
                expanded_mode = attempt > 1
                mode_desc = "expanded mode" if expanded_mode else "standard mode"
                log_step("html_extraction", "running", f"Extracting relevant elements ({mode_desc})")

                simplified_html = extract_relevant_html(soup, instruction, expanded_mode, enrichment_data)

                if not simplified_html:
                    log_step("html_extraction", "warning", "No interactive elements found")
                    simplified_html = "<body>No interactive elements found</body>"
                else:
                    element_count = len(simplified_html.split('\n'))
                    log_step("html_extraction", "success", f"Found {element_count} relevant elements ({mode_desc})")

                # Generate adaptive prompts
                log_step("xpath_generation", "running", f"Generating XPath with Claude (attempt {attempt})")
                system_prompt, user_prompt_template = generate_adaptive_prompt(instruction, attempt, enrichment_data, intent_summary)

                user_prompt = user_prompt_template.format(url=url, html=simplified_html)

                try:
                    response = client.messages.create(
                        model="claude-3-5-haiku-20241022",  # Use fast model with correct name
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}],
                        max_tokens=200,
                        temperature=0.3  # Lower temperature for consistency
                    )

                    # Extract XPath from response
                    response_text = response.content[0].text if response.content else ""

                    # Debug: log the full response to understand what Claude is generating
                    log_step("claude_response", "debug", f"Attempt {attempt} - Response length: {len(response_text)}, Preview: {response_text[:200]}")

                    # Extract XPath using improved patterns
                    extracted_xpath = None

                    # First try to find complete XPath expressions (more conservative)
                    complete_patterns = [
                        r'//[^"\n\r]*\]',  # XPath ending with ] (complete predicate)
                        r'//\w+(?:\[@[^]]+\])?',  # Simple element with optional attribute predicate
                        r'//\*',  # Simple wildcard
                    ]

                    for pattern in complete_patterns:
                        matches = re.findall(pattern, response_text)
                        for match in matches:
                            candidate = match.strip()
                            if len(candidate) > 3 and candidate.startswith('//'):
                                # Quick validation - check if brackets are balanced
                                if candidate.count('[') == candidate.count(']') and candidate.count('(') == candidate.count(')'):
                                    extracted_xpath = candidate
                                    break
                        if extracted_xpath:
                            break

                    # If no complete XPath found, try broader patterns and fix
                    if not extracted_xpath:
                        broad_patterns = [
                            r'//[^\n\r"\'`]+',  # Broader match
                            r'/[^\n\r"\'`]+',   # Absolute paths
                        ]

                        for pattern in broad_patterns:
                            matches = re.findall(pattern, response_text)
                            for match in matches:
                                candidate = match.strip().strip('`"\' \n.,')
                                if len(candidate) > 3 and (candidate.startswith('//') or candidate.startswith('/')):
                                    extracted_xpath = candidate
                                    break
                            if extracted_xpath:
                                break

                    if extracted_xpath:
                        # Validate and potentially fix the extracted XPath
                        log_step("xpath_validation", "running", "Validating extracted XPath")

                        validation = validate_xpath_syntax(extracted_xpath)
                        if validation["is_valid"]:
                            generated_xpath = extracted_xpath
                            log_step("xpath_generation", "success", f"Generated: {generated_xpath}")
                        else:
                            # Try to fix the XPath
                            log_step("xpath_fixing", "running", "Attempting to fix XPath syntax")
                            fix_result = fix_xpath(extracted_xpath, instruction)

                            if fix_result["is_fixed"] and fix_result["confidence"] > 0.7:
                                generated_xpath = fix_result["fixed_xpath"]
                                log_step("xpath_generation", "success", f"Fixed and generated: {generated_xpath}")
                                log_step("xpath_fixing", "success", f"Applied fixes: {', '.join(fix_result['changes_made'])}")
                            else:
                                # Use original but log the issues
                                generated_xpath = extracted_xpath
                                log_step("xpath_generation", "warning", f"Using potentially invalid XPath: {validation['syntax_errors']}")
                    else:
                        # Fallback to basic XPath
                        generated_xpath = "//input | //button | //a"
                        log_step("xpath_generation", "warning", "No XPath found in response, using fallback")

                    # Quick validation test to see if we should retry
                    if generated_xpath:
                        try:
                            elements = await page.query_selector_all(f"xpath={generated_xpath}")
                            match_count = len(elements)

                            # If we found matches, we're done
                            if match_count > 0:
                                log_step("quick_validation", "success", f"Found {match_count} matches on attempt {attempt}")
                                break
                            # If no matches and we have another attempt, continue to retry
                            elif attempt < 2:
                                log_step("quick_validation", "warning", f"No matches on attempt {attempt}, retrying with expanded context")
                                continue
                            else:
                                log_step("quick_validation", "failed", "No matches found after all attempts")
                                break
                        except:
                            # If validation fails, try next attempt or break
                            if attempt < 2:
                                log_step("quick_validation", "error", f"Validation error on attempt {attempt}, retrying")
                                continue
                            else:
                                break

                except Exception as e:
                    log_step("xpath_generation", "error", f"Attempt {attempt} error: {str(e)}")
                    if attempt < 2:
                        continue
                    else:
                        generated_xpath = "//input | //button | //a"

            # Final fallback if all attempts failed
            if not generated_xpath:
                generated_xpath = "//input | //button | //a"
                log_step("xpath_generation", "fallback", "Using final fallback XPath")

            # Continue with validation (skip refinement since we already validated in the loop)
            log_step("validation", "running", "Final validation")

            try:
                elements = await page.query_selector_all(f"xpath={generated_xpath}")
                match_count = len(elements)

                # Note: Refinement is now handled in the adaptive retry loop above
                if match_count == 0:
                    log_step("validation", "warning", "No elements matched final XPath")

                # Get element info if we have matches
                element_info = None
                if match_count > 0:
                    first_element = elements[0]
                    tag_name = await first_element.evaluate("el => el.tagName.toLowerCase()")
                    text_content = await first_element.evaluate("el => (el.textContent || '').trim().substring(0, 50)")
                    element_info = f"<{tag_name}>"
                    if text_content:
                        element_info += f": {text_content}"

                    log_step("validation", "success", f"Validated: {match_count} matches")
                else:
                    log_step("validation", "warning", "No elements matched")
                    element_info = "No elements matched"

                # Calculate robustness score
                robustness_score, robustness_reasons = calculate_robustness_score(generated_xpath)
                log_step("robustness_check", "success", f"Robustness score: {robustness_score}/100")

                # Determine robustness display
                if robustness_score >= 80:
                    robustness_display = {
                        "icon": "🛡️🛡️🛡️",
                        "label": "Highly Robust",
                        "color": "green",
                        "description": f"Score: {robustness_score}/100"
                    }
                elif robustness_score >= 60:
                    robustness_display = {
                        "icon": "🛡️🛡️",
                        "label": "Moderately Robust",
                        "color": "yellow",
                        "description": f"Score: {robustness_score}/100"
                    }
                else:
                    robustness_display = {
                        "icon": "🛡️",
                        "label": "Basic",
                        "color": "red",
                        "description": f"Score: {robustness_score}/100"
                    }

                await browser.close()

                return {
                    "xpath": generated_xpath,
                    "validated": match_count > 0,
                    "match_count": match_count,
                    "element_info": element_info,
                    "process_log": process_log,
                    "robustness_score": robustness_score,
                    "robustness_reasons": robustness_reasons,
                    "robustness_display": robustness_display
                }

            except Exception as e:
                log_step("validation", "error", str(e))
                await browser.close()

                return {
                    "xpath": generated_xpath,
                    "validated": False,
                    "match_count": 0,
                    "element_info": f"Validation error: {str(e)}",
                    "process_log": process_log
                }

        except Exception as e:
            log_step("critical_error", "failed", str(e))
            if 'browser' in locals():
                await browser.close()

            return {
                "xpath": "//body",
                "validated": False,
                "match_count": 0,
                "element_info": f"Error: {str(e)}",
                "process_log": process_log
            }