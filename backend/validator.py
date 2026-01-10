from playwright.async_api import async_playwright
import asyncio
import sys
from typing import Optional

# Set Windows event loop policy if on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

async def validate_xpath(url: str, xpath: str) -> dict:
    """
    Validates an XPath selector on a given URL using Playwright.

    Args:
        url: The URL to test the XPath against
        xpath: The XPath selector to validate

    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "match_count": int,
            "element_info": str | None,  # tag name + text preview of first match
            "error": str | None
        }
    """
    browser = None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )

            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )

            page = await context.new_page()

            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=15000)

                await page.wait_for_load_state('networkidle', timeout=5000)
            except:
                await page.wait_for_timeout(2000)

            try:
                locator = page.locator(f"xpath={xpath}")

                match_count = await locator.count()

                element_info = None
                if match_count > 0:
                    first_element = locator.first

                    try:
                        tag_name = await first_element.evaluate("el => el.tagName.toLowerCase()")

                        text_content = await first_element.inner_text()
                        if text_content:
                            text_preview = text_content[:100].strip()
                            if len(text_content) > 100:
                                text_preview += "..."
                            element_info = f"<{tag_name}>: {text_preview}"
                        else:
                            try:
                                element_attrs = await first_element.evaluate("""
                                    el => {
                                        const attrs = [];
                                        if (el.id) attrs.push(`id="${el.id}"`);
                                        if (el.className) attrs.push(`class="${el.className}"`);
                                        if (el.href) attrs.push(`href="${el.href}"`);
                                        if (el.src) attrs.push(`src="${el.src}"`);
                                        if (el.alt) attrs.push(`alt="${el.alt}"`);
                                        if (el.title) attrs.push(`title="${el.title}"`);
                                        if (el.placeholder) attrs.push(`placeholder="${el.placeholder}"`);
                                        if (el.value && el.tagName !== 'TEXTAREA') attrs.push(`value="${el.value}"`);
                                        return attrs.slice(0, 3).join(' ');
                                    }
                                """)
                                if element_attrs:
                                    element_info = f"<{tag_name} {element_attrs}>"
                                else:
                                    element_info = f"<{tag_name}>"
                            except:
                                element_info = f"<{tag_name}>"
                    except:
                        element_info = "Element found but could not extract details"

                return {
                    "valid": match_count > 0,
                    "match_count": match_count,
                    "element_info": element_info,
                    "error": None
                }

            except Exception as e:
                return {
                    "valid": False,
                    "match_count": 0,
                    "element_info": None,
                    "error": f"XPath evaluation error: {str(e)}"
                }

            finally:
                await context.close()

    except Exception as e:
        return {
            "valid": False,
            "match_count": 0,
            "element_info": None,
            "error": f"Browser error: {str(e)}"
        }
    finally:
        if browser:
            await browser.close()


async def validate_xpath_with_retry(url: str, xpath: str, max_retries: int = 2) -> dict:
    """
    Validates XPath with retry logic for resilience.
    """
    last_error = None

    for attempt in range(max_retries + 1):
        result = await validate_xpath(url, xpath)

        if result["error"] is None or "XPath evaluation error" in result.get("error", ""):
            return result

        last_error = result
        if attempt < max_retries:
            await asyncio.sleep(1)

    return last_error or {
        "valid": False,
        "match_count": 0,
        "element_info": None,
        "error": "Validation failed after retries"
    }