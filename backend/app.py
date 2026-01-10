import os
import sys
import asyncio
import json
import time
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx
from versions import v1_generate, v2_generate, v3_generate

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

class EvaluateRequest(BaseModel):
    version: str
    test_case_ids: Optional[List[str]] = None

class EvaluationResult(BaseModel):
    test_id: str
    category: str
    url: str
    instruction: str
    version: str
    generated_xpath: Optional[str]
    validated: bool
    match_count: int
    element_info: Optional[str]
    success: bool
    error_message: Optional[str]
    execution_time: float

class EvaluationMetrics(BaseModel):
    total_tests: int
    successful: int
    success_rate: float
    average_time: float
    p95_time: float
    validated_xpaths: int

class EvaluateResponse(BaseModel):
    metrics: EvaluationMetrics
    results: List[EvaluationResult]

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
            result = await v3_generate(request.url, request.instruction)
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
                "description": "Agentic approach with Claude tool use and self-correction",
                "features": ["Tool-augmented LLM", "Robustness scoring", "Self-correction", "Page inspection"],
                "active": True
            }
        }
    }

@app.get("/api/proxy")
async def proxy_url(url: str):
    """Proxy endpoint to serve external websites through our backend"""
    try:
        async with httpx.AsyncClient(
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        ) as client:
            response = await client.get(url, follow_redirects=True, timeout=15.0)
            response.raise_for_status()

            # Get the content
            content = response.text

            # Inject our highlighting script capabilities
            script_injection = '''
<script>
console.log('🔧 Storms proxy script injected');
// Allow parent frame to inject highlighting scripts
window.addEventListener('message', function(event) {
    console.log('📨 Received message:', event.data);
    if (event.origin !== 'http://localhost:5173') {
        console.log('❌ Wrong origin:', event.origin);
        return;
    }
    if (event.data.type === 'INJECT_HIGHLIGHT_SCRIPT') {
        try {
            console.log('🚀 Executing highlight script');
            eval(event.data.script);
        } catch(e) {
            console.error('❌ Error executing highlight script:', e);
        }
    }
});

// Signal that we're ready
window.parent.postMessage({type: 'PROXY_READY'}, '*');
</script>'''

            # Inject before closing head tag or body tag
            if '</head>' in content:
                content = content.replace('</head>', script_injection + '</head>')
            elif '</body>' in content:
                content = content.replace('</body>', script_injection + '</body>')
            else:
                content = content + script_injection

            # Return with proper headers
            return HTMLResponse(
                content=content,
                headers={
                    "Content-Type": "text/html; charset=utf-8",
                    # Remove X-Frame-Options to allow iframe embedding
                    "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "no-cache"
                }
            )

    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"Request error: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"HTTP {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

@app.post("/api/evaluate", response_model=EvaluateResponse)
async def evaluate_version(request: EvaluateRequest):
    """Run evaluation test cases against a specific version"""

    # Load test cases
    test_cases_file = Path(__file__).parent.parent / "evaluation" / "test_cases.json"

    try:
        with open(test_cases_file, 'r') as f:
            test_data = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Test cases file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading test cases: {str(e)}")

    test_cases = test_data.get("test_cases", [])

    # Filter test cases if specific IDs provided
    if request.test_case_ids:
        test_cases = [tc for tc in test_cases if tc["id"] in request.test_case_ids]

    if not test_cases:
        raise HTTPException(status_code=400, detail="No test cases found")

    # Run evaluation
    results = []
    execution_times = []

    for test_case in test_cases:
        start_time = time.time()

        try:
            # Route to appropriate version
            if request.version == "v1":
                result = await v1_generate(test_case["url"], test_case["instruction"])
            elif request.version == "v2":
                result = await v2_generate(test_case["url"], test_case["instruction"])
            elif request.version == "v3":
                result = await v3_generate(test_case["url"], test_case["instruction"])
            else:
                raise HTTPException(status_code=400, detail=f"Unknown version: {request.version}")

            execution_time = time.time() - start_time
            execution_times.append(execution_time)

            # Determine success based on validation
            success = result.get("validated", False) and result.get("match_count", 0) > 0

            results.append(EvaluationResult(
                test_id=test_case["id"],
                category=test_case["category"],
                url=test_case["url"],
                instruction=test_case["instruction"],
                version=request.version,
                generated_xpath=result.get("xpath"),
                validated=result.get("validated", False),
                match_count=result.get("match_count", 0),
                element_info=result.get("element_info"),
                success=success,
                error_message=None,
                execution_time=execution_time
            ))

        except Exception as e:
            execution_time = time.time() - start_time
            execution_times.append(execution_time)

            results.append(EvaluationResult(
                test_id=test_case["id"],
                category=test_case["category"],
                url=test_case["url"],
                instruction=test_case["instruction"],
                version=request.version,
                generated_xpath=None,
                validated=False,
                match_count=0,
                element_info=None,
                success=False,
                error_message=str(e),
                execution_time=execution_time
            ))

    # Calculate metrics
    successful_count = sum(1 for r in results if r.success)
    total_tests = len(results)
    success_rate = successful_count / total_tests if total_tests > 0 else 0
    average_time = sum(execution_times) / len(execution_times) if execution_times else 0

    # Calculate P95 latency
    sorted_times = sorted(execution_times)
    p95_index = int(0.95 * len(sorted_times))
    p95_time = sorted_times[p95_index] if sorted_times else 0

    validated_xpaths = sum(1 for r in results if r.validated and r.match_count > 0)

    metrics = EvaluationMetrics(
        total_tests=total_tests,
        successful=successful_count,
        success_rate=success_rate,
        average_time=average_time,
        p95_time=p95_time,
        validated_xpaths=validated_xpaths
    )

    return EvaluateResponse(
        metrics=metrics,
        results=results
    )