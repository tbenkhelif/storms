import os
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from anthropic import Anthropic
from bs4 import BeautifulSoup
from dotenv import load_dotenv

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

class GenerateResponse(BaseModel):
    xpath: str
    version: str = "v1"

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
            response = await client.get(request.url, follow_redirects=True)
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

        return GenerateResponse(xpath=xpath, version="v1")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling Claude API: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}