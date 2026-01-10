import os
import re
import sys
import asyncio
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from anthropic import Anthropic
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from validator import validate_xpath_with_retry

# Fix for Windows event loop policy
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

anthropic_client = Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

class GenerateRequest(BaseModel):
    url: str
    instruction: str
    version: Optional[str] = "v1"

class GenerateResponse(BaseModel):
    xpath: str
    version: str = "v1"
    validated: bool = False
    match_count: int = 0
    element_info: Optional[str] = None

def clean_html(html_content: str) -> str:
    soup = BeautifulSoup(html_content, 'html.parser')

    for script in soup(["script", "style"]):
        script.decompose()

    cleaned_html = str(soup)

    if len(cleaned_html) > 50000:
        cleaned_html = cleaned_html[:50000]

    return cleaned_html

@app.post("/api/generate", response_model=GenerateResponse)
async def generate_xpath(request: GenerateRequest):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(request.url, follow_redirects=True, timeout=15.0)
            response.raise_for_status()
            html_content = response.text
    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"Error fetching URL: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"HTTP error: {e.response.status_code}")

    cleaned_html = clean_html(html_content)

    prompt = f"""You are an XPath generator for web test automation.

Given this HTML:
{cleaned_html}

User instruction: "{request.instruction}"

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

        # Try validation, but don't fail if Playwright has issues
        try:
            validation_result = await validate_xpath_with_retry(request.url, xpath)
        except Exception as e:
            print(f"Validation skipped due to error: {e}")
            validation_result = {
                "valid": False,
                "match_count": 0,
                "element_info": None,
                "error": "Validation unavailable"
            }

        return GenerateResponse(
            xpath=xpath,
            version=request.version or "v1",
            validated=validation_result["valid"],
            match_count=validation_result["match_count"],
            element_info=validation_result["element_info"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling Claude API: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "playwright_ready": True}