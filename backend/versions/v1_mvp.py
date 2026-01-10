import httpx
from anthropic import Anthropic
from bs4 import BeautifulSoup
import os
from typing import Optional
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


async def generate(url: str, instruction: str) -> dict:
    """
    V1 MVP: Direct LLM call with single XPath generation

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

    # Generate XPath with Claude
    process_log.append({
        "step": "Generating XPath with Claude",
        "status": "started"
    })

    prompt = f"""You are an XPath generator for web test automation.

Given this HTML:
{cleaned_html}

User instruction: "{instruction}"

Return ONLY a valid XPath expression that would select the target element.
Prefer robust selectors in this order: text content > aria-label > id > class
Do not include any explanation, just the XPath."""

    try:
        message = anthropic_client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=300,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        xpath = message.content[0].text.strip()
        xpath = xpath.strip('"\'')

        process_log.append({
            "step": "Generating XPath with Claude",
            "status": "success",
            "details": xpath
        })
    except Exception as e:
        process_log.append({
            "step": "Generating XPath with Claude",
            "status": "failed",
            "details": str(e)
        })
        raise

    # Validate XPath
    process_log.append({
        "step": "Validating XPath",
        "status": "started"
    })

    try:
        validation_result = await validate_xpath_with_retry(url, xpath)

        if validation_result["valid"]:
            process_log.append({
                "step": "Validating XPath",
                "status": "success",
                "details": f"Found {validation_result['match_count']} matches"
            })
        else:
            process_log.append({
                "step": "Validating XPath",
                "status": "failed",
                "details": validation_result.get("error", "No matches found")
            })
    except Exception as e:
        process_log.append({
            "step": "Validating XPath",
            "status": "skipped",
            "details": f"Validation unavailable: {str(e)}"
        })
        validation_result = {
            "valid": False,
            "match_count": 0,
            "element_info": None,
            "error": "Validation unavailable"
        }

    return {
        "xpath": xpath,
        "validated": validation_result["valid"],
        "match_count": validation_result["match_count"],
        "element_info": validation_result["element_info"],
        "process_log": process_log
    }