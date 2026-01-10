import os
import sys
import asyncio
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from versions import v1_generate, v2_generate

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

class GenerateRequest(BaseModel):
    url: str
    instruction: str
    version: Optional[str] = "v1"

class ProcessLogEntry(BaseModel):
    step: str
    status: str
    details: Optional[str] = None

class GenerateResponse(BaseModel):
    xpath: str
    version: str = "v1"
    validated: bool = False
    match_count: int = 0
    element_info: Optional[str] = None
    process_log: Optional[List[ProcessLogEntry]] = None

@app.post("/api/generate", response_model=GenerateResponse)
async def generate_xpath(request: GenerateRequest):
    """Generate XPath using the specified version strategy"""
    version = request.version or "v1"

    try:
        # Route to appropriate version
        if version == "v1":
            result = await v1_generate(request.url, request.instruction)
        elif version == "v2":
            result = await v2_generate(request.url, request.instruction)
        elif version == "v3":
            # V3 not implemented yet, fall back to v2
            result = await v2_generate(request.url, request.instruction)
        else:
            # Default to v1 for unknown versions
            result = await v1_generate(request.url, request.instruction)

        # Convert process_log entries to ProcessLogEntry objects if present
        process_log = None
        if "process_log" in result:
            process_log = [
                ProcessLogEntry(**entry) for entry in result["process_log"]
            ]

        return GenerateResponse(
            xpath=result["xpath"],
            version=version,
            validated=result.get("validated", False),
            match_count=result.get("match_count", 0),
            element_info=result.get("element_info"),
            process_log=process_log
        )

    except HTTPException:
        raise
    except Exception as e:
        # Log the full error for debugging
        import traceback
        print(f"Error in generate_xpath: {str(e)}")
        print(traceback.format_exc())

        raise HTTPException(
            status_code=500,
            detail=f"Error generating XPath: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "versions": ["v1", "v2", "v3"],
        "default_version": "v1"
    }

@app.get("/api/versions")
async def get_versions():
    """Get information about available versions"""
    return {
        "versions": {
            "v1": {
                "name": "MVP",
                "description": "Direct LLM call with single XPath generation",
                "features": ["Basic XPath generation", "Fast response", "Validation"],
                "active": True
            },
            "v2": {
                "name": "Validated",
                "description": "Heuristics first, then multi-candidate LLM generation",
                "features": ["Heuristic patterns", "Multiple candidates", "Validation testing", "Process logging"],
                "active": True
            },
            "v3": {
                "name": "Enterprise",
                "description": "Agentic approach with advanced tools (coming soon)",
                "features": ["Tool-augmented LLM", "Robustness scoring", "Self-correction"],
                "active": False
            }
        }
    }