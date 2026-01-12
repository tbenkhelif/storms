#!/usr/bin/env python3
"""
Evaluation runner for Storms XPath generator versions.

This script runs the evaluation test cases against different versions
and produces results for comparison.
"""

import json
import asyncio
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
from dataclasses import dataclass, asdict

@dataclass
class EvaluationResult:
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
    xpath_correct: bool  # Whether XPath matches expected or finds correct element
    error_message: Optional[str]
    execution_time: float
    process_log: Optional[List[Dict]] = None

class XPathEvaluator:
    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url
        self.results: List[EvaluationResult] = []

    async def run_evaluation(self, versions: List[str] = None, test_categories: List[str] = None, test_file: str = None) -> Dict[str, Any]:
        """Run evaluation against specified versions and categories"""

        if versions is None:
            versions = ["v1", "v2", "v3"]

        # Load test cases
        if test_file:
            test_cases_path = Path(test_file)
        else:
            test_cases_path = Path(__file__).parent / "test_cases.json"

        with open(test_cases_path, 'r') as f:
            test_data = json.load(f)

        test_cases = test_data['test_cases']

        # Filter by categories if specified
        if test_categories:
            test_cases = [tc for tc in test_cases if tc['category'] in test_categories]

        print(f"🚀 Starting evaluation with {len(test_cases)} test cases across {len(versions)} versions")
        print(f"📋 Categories: {set(tc['category'] for tc in test_cases)}")
        print(f"🔧 Versions: {versions}")
        print("-" * 60)

        # Check backend health
        try:
            health_response = requests.get(f"{self.backend_url}/health", timeout=5)
            if health_response.status_code != 200:
                raise Exception(f"Backend health check failed: {health_response.status_code}")
            print("✅ Backend is healthy")
        except Exception as e:
            print(f"❌ Backend health check failed: {e}")
            print("Make sure the FastAPI backend is running on http://localhost:8000")
            return {"error": "Backend not available"}

        # Run tests
        total_tests = len(test_cases) * len(versions)
        current_test = 0

        for version in versions:
            print(f"\n🔄 Testing version {version}")
            print("-" * 40)

            for test_case in test_cases:
                current_test += 1
                progress = f"[{current_test}/{total_tests}]"

                print(f"{progress} {test_case['id']} ({test_case['category']}): {test_case['instruction'][:50]}...")

                result = await self._run_single_test(test_case, version)
                self.results.append(result)

                # Show result
                status_icon = "✅" if result.success else "❌"
                match_info = f" ({result.match_count} matches)" if result.validated else ""
                print(f"    {status_icon} {result.execution_time:.2f}s{match_info}")

                if result.error_message:
                    print(f"    ⚠️  {result.error_message}")

        # Generate summary
        summary = self._generate_summary()

        print("\n" + "="*60)
        print("📊 EVALUATION SUMMARY")
        print("="*60)

        for version in versions:
            version_results = [r for r in self.results if r.version == version]
            success_rate = sum(1 for r in version_results if r.success) / len(version_results) * 100
            avg_time = sum(r.execution_time for r in version_results) / len(version_results)
            valid_xpaths = sum(1 for r in version_results if r.validated and r.match_count > 0)
            correct_xpaths = sum(1 for r in version_results if r.xpath_correct)

            print(f"\n🔧 {version.upper()}")
            print(f"   Success Rate: {success_rate:.1f}% ({sum(1 for r in version_results if r.success)}/{len(version_results)})")
            print(f"   Found Elements: {valid_xpaths}/{len(version_results)} ({valid_xpaths/len(version_results)*100:.1f}%)")
            print(f"   Correct XPaths: {correct_xpaths}/{len(version_results)} ({correct_xpaths/len(version_results)*100:.1f}%)")
            print(f"   Avg Time: {avg_time:.2f}s")

        # Category breakdown
        print(f"\n📂 By Category:")
        for category in set(tc['category'] for tc in test_cases):
            category_results = [r for r in self.results if r.category == category]
            success_rate = sum(1 for r in category_results if r.success) / len(category_results) * 100
            print(f"   {category}: {success_rate:.1f}% success")

        return summary

    async def _run_single_test(self, test_case: Dict[str, Any], version: str) -> EvaluationResult:
        """Run a single test case"""
        start_time = time.time()

        try:
            # Make request to backend
            payload = {
                "url": test_case["url"],
                "instruction": test_case["instruction"],
                "version": version
            }

            response = requests.post(
                f"{self.backend_url}/api/generate",
                json=payload,
                timeout=30
            )

            execution_time = time.time() - start_time

            if response.status_code == 200:
                data = response.json()

                generated_xpath = data.get("xpath", "")
                element_info = data.get("element_info")
                validated = data.get("validated", False)
                match_count = data.get("match_count", 0)

                # Check correctness: XPath matches expected OR element matches expected
                xpath_correct = self._check_xpath_correctness(generated_xpath, test_case, element_info)

                # Success = validated AND found element(s) AND correct element
                success = validated and match_count > 0 and xpath_correct

                return EvaluationResult(
                    test_id=test_case["id"],
                    category=test_case["category"],
                    url=test_case["url"],
                    instruction=test_case["instruction"],
                    version=version,
                    generated_xpath=generated_xpath,
                    validated=validated,
                    match_count=match_count,
                    element_info=element_info,
                    success=success,
                    xpath_correct=xpath_correct,
                    error_message=None,
                    execution_time=execution_time,
                    process_log=data.get("process_log")
                )

            else:
                error_detail = response.json().get("detail", f"HTTP {response.status_code}") if response.headers.get("content-type", "").startswith("application/json") else f"HTTP {response.status_code}"

                return EvaluationResult(
                    test_id=test_case["id"],
                    category=test_case["category"],
                    url=test_case["url"],
                    instruction=test_case["instruction"],
                    version=version,
                    generated_xpath=None,
                    validated=False,
                    match_count=0,
                    element_info=None,
                    success=False,
                    xpath_correct=False,
                    error_message=error_detail,
                    execution_time=time.time() - start_time
                )

        except Exception as e:
            return EvaluationResult(
                test_id=test_case["id"],
                category=test_case["category"],
                url=test_case["url"],
                instruction=test_case["instruction"],
                version=version,
                generated_xpath=None,
                validated=False,
                match_count=0,
                element_info=None,
                success=False,
                xpath_correct=False,
                error_message=str(e),
                execution_time=time.time() - start_time
            )

    def _xpath_similarity(self, xpath1: str, xpath2: str) -> float:
        """Calculate similarity between two XPaths (simple approach)"""
        if xpath1 == xpath2:
            return 1.0

        # Basic similarity based on common elements
        xpath1_parts = set(xpath1.replace("//", "/").split("/"))
        xpath2_parts = set(xpath2.replace("//", "/").split("/"))

        if not xpath1_parts or not xpath2_parts:
            return 0.0

        common = len(xpath1_parts.intersection(xpath2_parts))
        total = len(xpath1_parts.union(xpath2_parts))

        return common / total if total > 0 else 0.0

    def _check_xpath_correctness(self, generated_xpath: str, test_case: Dict[str, Any], element_info: Optional[str]) -> bool:
        """Check if generated XPath is correct based on valid_xpaths or expected_element"""
        if not generated_xpath:
            return False

        # Method 1: Check against list of valid XPaths
        valid_xpaths = test_case.get("valid_xpaths", [])

        # Exact match
        if generated_xpath in valid_xpaths:
            return True

        # Normalized comparison (strip whitespace, handle quotes)
        normalized_generated = generated_xpath.strip().replace('"', "'")
        for valid_xpath in valid_xpaths:
            normalized_valid = valid_xpath.strip().replace('"', "'")
            if normalized_generated == normalized_valid:
                return True
            # Check similarity threshold
            if self._xpath_similarity(normalized_generated, normalized_valid) > 0.8:
                return True

        # Method 2: Check if element_info matches expected_element
        expected_element = test_case.get("expected_element", {})
        if element_info and expected_element:
            # Check tag
            expected_tag = expected_element.get("tag", "").lower()
            if expected_tag and f"<{expected_tag}" in element_info.lower():
                # Check text_contains if specified
                text_contains = expected_element.get("text_contains", "")
                if text_contains:
                    if text_contains.lower() in element_info.lower():
                        return True
                else:
                    # Tag matches and no text requirement
                    return True

                # Check attributes if specified
                expected_attrs = expected_element.get("attributes", {})
                if expected_attrs:
                    attrs_match = all(
                        f'{key}=' in element_info or f'{key}\"' in element_info or val.lower() in element_info.lower()
                        for key, val in expected_attrs.items()
                    )
                    if attrs_match:
                        return True

        return False

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate evaluation summary"""
        summary = {
            "total_tests": len(self.results),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": [asdict(result) for result in self.results],
            "versions": {},
            "categories": {}
        }

        # Version-wise summary
        for version in set(r.version for r in self.results):
            version_results = [r for r in self.results if r.version == version]
            summary["versions"][version] = {
                "total": len(version_results),
                "successful": sum(1 for r in version_results if r.success),
                "success_rate": sum(1 for r in version_results if r.success) / len(version_results),
                "average_time": sum(r.execution_time for r in version_results) / len(version_results),
                "validated_xpaths": sum(1 for r in version_results if r.validated and r.match_count > 0),
                "correct_xpaths": sum(1 for r in version_results if r.xpath_correct)
            }

        # Category-wise summary
        for category in set(r.category for r in self.results):
            category_results = [r for r in self.results if r.category == category]
            summary["categories"][category] = {
                "total": len(category_results),
                "successful": sum(1 for r in category_results if r.success),
                "success_rate": sum(1 for r in category_results if r.success) / len(category_results)
            }

        return summary

    def save_results(self, filename: str = None):
        """Save results to JSON file"""
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"evaluation_results_{timestamp}.json"

        filepath = Path(__file__).parent / filename
        summary = self._generate_summary()

        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        print(f"💾 Results saved to {filepath}")
        return filepath

async def main():
    """Main function to run evaluations"""
    import argparse

    parser = argparse.ArgumentParser(description="Run Storms XPath generator evaluation")
    parser.add_argument("--versions", nargs="+", default=["v1", "v2", "v3"],
                       help="Versions to test (default: v1 v2 v3)")
    parser.add_argument("--categories", nargs="+",
                       help="Test categories to run (default: all)")
    parser.add_argument("--test-file", type=str,
                       help="Path to test cases JSON file (default: test_cases.json)")
    parser.add_argument("--output", type=str,
                       help="Output filename for results")
    parser.add_argument("--backend", type=str, default="http://localhost:8000",
                       help="Backend URL (default: http://localhost:8000)")

    args = parser.parse_args()

    evaluator = XPathEvaluator(args.backend)

    try:
        summary = await evaluator.run_evaluation(
            versions=args.versions,
            test_categories=args.categories,
            test_file=args.test_file
        )

        if "error" not in summary:
            filepath = evaluator.save_results(args.output)
            print(f"\n🎯 Evaluation completed successfully!")
            print(f"📄 Results saved to: {filepath}")

    except KeyboardInterrupt:
        print("\n⚠️ Evaluation interrupted by user")
        if evaluator.results:
            filepath = evaluator.save_results("evaluation_interrupted.json")
            print(f"💾 Partial results saved to: {filepath}")

    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())