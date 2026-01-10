import httpx
from anthropic import Anthropic
from bs4 import BeautifulSoup
import os
import re
from typing import Optional, List
from validator import validate_xpath_with_retry
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

anthropic_client = Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

def clean_html(html_content: str) -> str:
    """Remove script and style tags, truncate to 50k chars"""
    soup = BeautifulSoup(html_content, 'html.parser')

    for script in soup(["script", "style"]):
        script.decompose()

    cleaned_html = str(soup)

    if len(cleaned_html) > 50000:
        cleaned_html = cleaned_html[:50000]

    return cleaned_html


def extract_text_patterns(instruction: str) -> List[str]:
    """Extract quoted text or obvious text patterns from instruction"""
    patterns = []

    # Find single-quoted text
    single_quoted = re.findall(r"'([^']+)'", instruction)
    patterns.extend(single_quoted)

    # Find double-quoted text
    double_quoted = re.findall(r'"([^"]+)"', instruction)
    patterns.extend(double_quoted)

    # Find capitalized words that might be button/link text
    if not patterns:
        words = instruction.split()
        for word in words:
            if word and word[0].isupper() and len(word) > 2 and word not in ['The', 'And', 'For', 'With']:
                patterns.append(word)

    return patterns


def generate_heuristic_xpaths(instruction: str) -> List[str]:
    """Generate XPath candidates based on instruction patterns"""
    instruction_lower = instruction.lower()
    xpaths = []

    # Extract any quoted text or patterns
    text_patterns = extract_text_patterns(instruction)

    # Button patterns
    if any(word in instruction_lower for word in ['click', 'button', 'submit', 'press']):
        for text in text_patterns:
            xpaths.extend([
                f"//button[normalize-space()='{text}']",
                f"//button[contains(normalize-space(), '{text}')]",
                f"//*[@type='submit' and normalize-space()='{text}']",
                f"//*[@type='button' and normalize-space()='{text}']",
                f"//*[@role='button' and normalize-space()='{text}']",
            ])

    # Link patterns
    if any(word in instruction_lower for word in ['link', 'navigate', 'go to', 'open']):
        for text in text_patterns:
            xpaths.extend([
                f"//a[normalize-space()='{text}']",
                f"//a[contains(normalize-space(), '{text}')]",
                f"//*[@role='link' and normalize-space()='{text}']",
            ])

    # Input field patterns
    if any(word in instruction_lower for word in ['input', 'field', 'enter', 'type', 'fill']):
        # Look for field names
        field_patterns = ['email', 'password', 'username', 'name', 'search', 'phone', 'address']
        for pattern in field_patterns:
            if pattern in instruction_lower:
                xpaths.extend([
                    f"//input[@name='{pattern}']",
                    f"//input[@id='{pattern}']",
                    f"//input[@placeholder[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{pattern}')]]",
                    f"//input[@type='{pattern}']",
                    f"//label[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{pattern}')]//input",
                    f"//label[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{pattern}')]/following-sibling::input",
                ])

        # Generic input patterns if specific field not found
        if not xpaths and text_patterns:
            for text in text_patterns:
                xpaths.extend([
                    f"//label[contains(normalize-space(), '{text}')]//input",
                    f"//label[contains(normalize-space(), '{text}')]/following-sibling::input",
                    f"//input[@placeholder[contains(normalize-space(), '{text}')]]",
                ])

    # Dropdown/select patterns
    if any(word in instruction_lower for word in ['select', 'dropdown', 'choose', 'pick']):
        xpaths.extend([
            "//select",
            "//*[@role='combobox']",
            "//*[@role='listbox']",
            "//*[@aria-haspopup='listbox']",
        ])
        for text in text_patterns:
            xpaths.extend([
                f"//select[@name='{text}']",
                f"//label[contains(normalize-space(), '{text}')]//select",
            ])

    # Checkbox patterns
    if any(word in instruction_lower for word in ['checkbox', 'check', 'tick', 'agree']):
        xpaths.append("//input[@type='checkbox']")
        for text in text_patterns:
            xpaths.extend([
                f"//label[contains(normalize-space(), '{text}')]//input[@type='checkbox']",
                f"//input[@type='checkbox' and @name='{text}']",
            ])

    # Radio button patterns
    if any(word in instruction_lower for word in ['radio', 'option', 'choose one']):
        xpaths.append("//input[@type='radio']")
        for text in text_patterns:
            xpaths.extend([
                f"//label[contains(normalize-space(), '{text}')]//input[@type='radio']",
                f"//input[@type='radio' and @value='{text}']",
            ])

    # Heading patterns
    if any(word in instruction_lower for word in ['heading', 'title', 'header']):
        for text in text_patterns:
            xpaths.extend([
                f"//h1[contains(normalize-space(), '{text}')]",
                f"//h2[contains(normalize-space(), '{text}')]",
                f"//h3[contains(normalize-space(), '{text}')]",
                f"//*[@role='heading' and contains(normalize-space(), '{text}')]",
            ])

    # Generic text patterns for any quoted text not caught above
    for text in text_patterns:
        if not any(text in xpath for xpath in xpaths):
            xpaths.extend([
                f"//*[normalize-space()='{text}']",
                f"//*[contains(normalize-space(), '{text}')]",
            ])

    # Remove duplicates while preserving order
    seen = set()
    unique_xpaths = []
    for xpath in xpaths:
        if xpath not in seen:
            seen.add(xpath)
            unique_xpaths.append(xpath)

    return unique_xpaths[:10]  # Return max 10 candidates


async def generate_llm_candidates(cleaned_html: str, instruction: str) -> List[str]:
    """Generate multiple XPath candidates using LLM"""
    prompt = f"""You are an XPath generator for web test automation.

Given this HTML:
{cleaned_html}

User instruction: "{instruction}"

Generate 3 DIFFERENT XPath expressions that could select the target element.
Use different strategies for each:
1. First XPath: Use text content matching
2. Second XPath: Use attributes (id, class, name, etc.)
3. Third XPath: Use structural relationships (parent/child/sibling)

Return ONLY the 3 XPaths, one per line, no explanations or numbering."""

    try:
        message = anthropic_client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=500,
            temperature=0.3,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        response_text = message.content[0].text.strip()
        xpaths = []

        for line in response_text.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('//') == False:
                # Clean up the XPath
                xpath = line.strip('"\'').strip()
                if xpath.startswith('//'):
                    xpaths.append(xpath)

        return xpaths
    except Exception:
        return []


async def generate(url: str, instruction: str) -> dict:
    """
    V2 Validated: Heuristics first, then multi-candidate LLM generation

    Returns:
        {
            "xpath": str,
            "validated": bool,
            "match_count": int,
            "element_info": str | None,
            "process_log": list
        }
    """
    process_log = []

    # Fetch HTML
    process_log.append({
        "step": "Fetching HTML",
        "status": "started"
    })

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True, timeout=15.0)
            response.raise_for_status()
            html_content = response.text

        process_log.append({
            "step": "Fetching HTML",
            "status": "success",
            "details": f"Fetched {len(html_content)} characters"
        })
    except Exception as e:
        process_log.append({
            "step": "Fetching HTML",
            "status": "failed",
            "details": str(e)
        })
        raise

    # Clean HTML
    cleaned_html = clean_html(html_content)
    process_log.append({
        "step": "Cleaning HTML",
        "status": "success",
        "details": f"Reduced to {len(cleaned_html)} characters"
    })

    # Try heuristic patterns first
    process_log.append({
        "step": "Trying heuristic patterns",
        "status": "started"
    })

    heuristic_xpaths = generate_heuristic_xpaths(instruction)

    if heuristic_xpaths:
        process_log.append({
            "step": "Trying heuristic patterns",
            "status": "success",
            "details": f"Generated {len(heuristic_xpaths)} heuristic candidates"
        })

        # Test each heuristic XPath
        for i, xpath in enumerate(heuristic_xpaths, 1):
            process_log.append({
                "step": f"Testing heuristic #{i}",
                "status": "started",
                "details": xpath
            })

            try:
                validation_result = await validate_xpath_with_retry(url, xpath, max_retries=0)

                if validation_result["valid"] and validation_result["match_count"] > 0:
                    process_log.append({
                        "step": f"Testing heuristic #{i}",
                        "status": "success",
                        "details": f"Valid! Found {validation_result['match_count']} matches"
                    })

                    return {
                        "xpath": xpath,
                        "validated": True,
                        "match_count": validation_result["match_count"],
                        "element_info": validation_result["element_info"],
                        "process_log": process_log
                    }
                else:
                    process_log.append({
                        "step": f"Testing heuristic #{i}",
                        "status": "failed",
                        "details": "No matches found"
                    })
            except Exception as e:
                process_log.append({
                    "step": f"Testing heuristic #{i}",
                    "status": "error",
                    "details": str(e)
                })
    else:
        process_log.append({
            "step": "Trying heuristic patterns",
            "status": "skipped",
            "details": "No patterns matched instruction"
        })

    # Heuristics failed, try LLM with multiple candidates
    process_log.append({
        "step": "Generating candidates with Claude",
        "status": "started"
    })

    llm_xpaths = await generate_llm_candidates(cleaned_html, instruction)

    if llm_xpaths:
        process_log.append({
            "step": "Generating candidates with Claude",
            "status": "success",
            "details": f"Generated {len(llm_xpaths)} candidates"
        })

        # Test each LLM-generated XPath
        for i, xpath in enumerate(llm_xpaths, 1):
            process_log.append({
                "step": f"Testing LLM candidate #{i}",
                "status": "started",
                "details": xpath
            })

            try:
                validation_result = await validate_xpath_with_retry(url, xpath, max_retries=0)

                if validation_result["valid"] and validation_result["match_count"] > 0:
                    process_log.append({
                        "step": f"Testing LLM candidate #{i}",
                        "status": "success",
                        "details": f"Valid! Found {validation_result['match_count']} matches"
                    })

                    return {
                        "xpath": xpath,
                        "validated": True,
                        "match_count": validation_result["match_count"],
                        "element_info": validation_result["element_info"],
                        "process_log": process_log
                    }
                else:
                    process_log.append({
                        "step": f"Testing LLM candidate #{i}",
                        "status": "failed",
                        "details": "No matches found"
                    })
            except Exception as e:
                process_log.append({
                    "step": f"Testing LLM candidate #{i}",
                    "status": "error",
                    "details": str(e)
                })
    else:
        process_log.append({
            "step": "Generating candidates with Claude",
            "status": "failed",
            "details": "No candidates generated"
        })

    # All attempts failed, return the first LLM candidate or first heuristic
    fallback_xpath = llm_xpaths[0] if llm_xpaths else (heuristic_xpaths[0] if heuristic_xpaths else "//body")

    process_log.append({
        "step": "Fallback",
        "status": "warning",
        "details": f"No valid XPath found, returning: {fallback_xpath}"
    })

    return {
        "xpath": fallback_xpath,
        "validated": False,
        "match_count": 0,
        "element_info": None,
        "process_log": process_log
    }