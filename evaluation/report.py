#!/usr/bin/env python3
"""
Report generator for Storms XPath evaluation results.

This script generates markdown reports comparing different versions
and analyzing performance across test categories.
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

class EvaluationReporter:
    def __init__(self, results_file: str):
        self.results_file = Path(results_file)

        if not self.results_file.exists():
            raise FileNotFoundError(f"Results file not found: {results_file}")

        with open(self.results_file, 'r') as f:
            self.data = json.load(f)

        self.results = self.data.get('results', [])
        self.summary = {
            'versions': self.data.get('versions', {}),
            'categories': self.data.get('categories', {}),
            'total_tests': self.data.get('total_tests', 0),
            'timestamp': self.data.get('timestamp', 'Unknown')
        }

    def generate_markdown_report(self, output_file: str = None) -> str:
        """Generate a comprehensive markdown report"""

        if output_file is None:
            output_file = self.results_file.with_suffix('.md')

        report_lines = []

        # Header
        report_lines.extend([
            "# 🛈 Storms XPath Generator Evaluation Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Evaluation Date:** {self.summary['timestamp']}  ",
            f"**Total Test Cases:** {self.summary['total_tests']}  ",
            f"**Results File:** `{self.results_file.name}`",
            "",
            "---",
            ""
        ])

        # Executive Summary
        report_lines.extend(self._generate_executive_summary())

        # Version Comparison
        report_lines.extend(self._generate_version_comparison())

        # Category Analysis
        report_lines.extend(self._generate_category_analysis())

        # Detailed Results
        report_lines.extend(self._generate_detailed_results())

        # Performance Analysis
        report_lines.extend(self._generate_performance_analysis())

        # Recommendations
        report_lines.extend(self._generate_recommendations())

        # Write to file
        report_content = "\n".join(report_lines)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

        print(f"📄 Report generated: {output_file}")
        return str(output_file)

    def _generate_executive_summary(self) -> List[str]:
        """Generate executive summary section"""
        lines = [
            "## 📊 Executive Summary",
            ""
        ]

        versions = list(self.summary['versions'].keys())
        if len(versions) >= 2:
            v1_stats = self.summary['versions'].get('v1', {})
            v2_stats = self.summary['versions'].get('v2', {})

            v1_success = v1_stats.get('success_rate', 0) * 100
            v2_success = v2_stats.get('success_rate', 0) * 100

            lines.extend([
                f"- **Best Performing Version:** {'v2' if v2_success > v1_success else 'v1'} ({max(v1_success, v2_success):.1f}% success rate)",
                f"- **Performance Improvement:** {abs(v2_success - v1_success):.1f} percentage points ({'v2 vs v1' if v2_success > v1_success else 'v1 vs v2'})",
                f"- **Most Challenging Category:** {self._find_most_challenging_category()}",
                f"- **Average Response Time:** {self._calculate_average_response_time():.2f}s",
                ""
            ])

        return lines

    def _generate_version_comparison(self) -> List[str]:
        """Generate version comparison table"""
        lines = [
            "## 🔧 Version Performance Comparison",
            "",
            "| Version | Success Rate | Valid XPaths | Avg Time (s) | Total Tests |",
            "|---------|--------------|--------------|--------------|-------------|"
        ]

        for version, stats in self.summary['versions'].items():
            success_rate = stats.get('success_rate', 0) * 100
            valid_xpaths = stats.get('validated_xpaths', 0)
            total = stats.get('total', 0)
            avg_time = stats.get('average_time', 0)

            lines.append(f"| {version.upper()} | {success_rate:.1f}% | {valid_xpaths}/{total} | {avg_time:.2f} | {total} |")

        lines.extend(["", "### 📈 Performance Insights", ""])

        # Add insights based on data
        if 'v1' in self.summary['versions'] and 'v2' in self.summary['versions']:
            v1_success = self.summary['versions']['v1'].get('success_rate', 0) * 100
            v2_success = self.summary['versions']['v2'].get('success_rate', 0) * 100
            v1_time = self.summary['versions']['v1'].get('average_time', 0)
            v2_time = self.summary['versions']['v2'].get('average_time', 0)

            lines.extend([
                f"- **Accuracy:** V2 shows {v2_success - v1_success:+.1f}% difference in success rate compared to V1",
                f"- **Speed:** V2 is {((v2_time / v1_time - 1) * 100):+.1f}% {'slower' if v2_time > v1_time else 'faster'} than V1 ({v2_time:.2f}s vs {v1_time:.2f}s)",
                f"- **Trade-off:** {'V2 sacrifices speed for accuracy' if v2_time > v1_time and v2_success > v1_success else 'V1 prioritizes speed over accuracy'}",
                ""
            ])

        return lines

    def _generate_category_analysis(self) -> List[str]:
        """Generate category performance analysis"""
        lines = [
            "## 📂 Performance by Test Category",
            "",
            "| Category | Success Rate | Difficulty | Notes |",
            "|----------|--------------|------------|-------|"
        ]

        # Sort categories by success rate
        sorted_categories = sorted(
            self.summary['categories'].items(),
            key=lambda x: x[1].get('success_rate', 0),
            reverse=True
        )

        for category, stats in sorted_categories:
            success_rate = stats.get('success_rate', 0) * 100
            total = stats.get('total', 0)

            if success_rate >= 80:
                difficulty = "🟢 Easy"
            elif success_rate >= 60:
                difficulty = "🟡 Medium"
            else:
                difficulty = "🔴 Hard"

            # Category-specific insights
            notes = self._get_category_insights(category, success_rate)

            lines.append(f"| {category.title()} | {success_rate:.1f}% ({stats.get('successful', 0)}/{total}) | {difficulty} | {notes} |")

        lines.extend(["", "### 🎯 Category Insights", ""])
        lines.extend(self._generate_category_insights())

        return lines

    def _generate_detailed_results(self) -> List[str]:
        """Generate detailed test results"""
        lines = [
            "## 📋 Detailed Test Results",
            "",
            "<details>",
            "<summary>Click to expand detailed results</summary>",
            ""
        ]

        # Group by category
        by_category = {}
        for result in self.results:
            category = result.get('category', 'unknown')
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(result)

        for category, results in by_category.items():
            lines.extend([
                f"### {category.title()} Tests",
                ""
            ])

            for result in results:
                status_icon = "✅" if result.get('success') else "❌"
                test_id = result.get('test_id', 'unknown')
                version = result.get('version', 'unknown')
                instruction = result.get('instruction', '')[:60] + ("..." if len(result.get('instruction', '')) > 60 else "")
                execution_time = result.get('execution_time', 0)

                lines.append(f"**{status_icon} {test_id}** ({version.upper()}) - {execution_time:.2f}s")
                lines.append(f"- *{instruction}*")

                if result.get('generated_xpath'):
                    lines.append(f"- XPath: `{result['generated_xpath']}`")

                if result.get('error_message'):
                    lines.append(f"- ❌ Error: {result['error_message']}")
                elif result.get('validated'):
                    matches = result.get('match_count', 0)
                    lines.append(f"- ✅ Validated: {matches} match{'es' if matches != 1 else ''}")

                lines.append("")

        lines.extend([
            "</details>",
            ""
        ])

        return lines

    def _generate_performance_analysis(self) -> List[str]:
        """Generate performance timing analysis"""
        lines = [
            "## ⚡ Performance Analysis",
            ""
        ]

        # Calculate timing statistics by version
        timing_stats = {}
        for version in self.summary['versions'].keys():
            version_results = [r for r in self.results if r.get('version') == version]
            times = [r.get('execution_time', 0) for r in version_results if r.get('execution_time')]

            if times:
                timing_stats[version] = {
                    'min': min(times),
                    'max': max(times),
                    'avg': sum(times) / len(times),
                    'count': len(times)
                }

        if timing_stats:
            lines.extend([
                "### Response Time Distribution",
                "",
                "| Version | Min (s) | Max (s) | Avg (s) | Samples |",
                "|---------|---------|---------|---------|---------|"
            ])

            for version, stats in timing_stats.items():
                lines.append(f"| {version.upper()} | {stats['min']:.2f} | {stats['max']:.2f} | {stats['avg']:.2f} | {stats['count']} |")

            lines.extend(["", "### ⚠️ Performance Issues", ""])

            # Identify slow tests
            slow_threshold = 10.0  # seconds
            slow_tests = [r for r in self.results if r.get('execution_time', 0) > slow_threshold]

            if slow_tests:
                lines.append(f"Found {len(slow_tests)} slow test(s) (>{slow_threshold}s):")
                for test in slow_tests[:5]:  # Show top 5 slowest
                    lines.append(f"- {test.get('test_id', 'unknown')} ({test.get('version', 'unknown')}): {test.get('execution_time', 0):.2f}s")
                if len(slow_tests) > 5:
                    lines.append(f"- ... and {len(slow_tests) - 5} more")
            else:
                lines.append("No performance issues detected (all tests < 10s)")

        lines.append("")
        return lines

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on results"""
        lines = [
            "## 💡 Recommendations",
            ""
        ]

        # Analyze results to provide recommendations
        recommendations = []

        # Version recommendations
        if 'v1' in self.summary['versions'] and 'v2' in self.summary['versions']:
            v1_success = self.summary['versions']['v1'].get('success_rate', 0)
            v2_success = self.summary['versions']['v2'].get('success_rate', 0)

            if v2_success > v1_success + 0.1:  # 10% improvement
                recommendations.append(
                    "🎯 **Use V2 for production:** V2 shows significantly better accuracy and should be the default choice."
                )
            elif v1_success > v2_success + 0.1:
                recommendations.append(
                    "⚡ **Consider V1 for speed:** V1 shows better performance and may be suitable for time-critical applications."
                )

        # Category-specific recommendations
        worst_category = min(self.summary['categories'].items(), key=lambda x: x[1].get('success_rate', 0))
        if worst_category[1].get('success_rate', 0) < 0.5:  # Less than 50% success
            recommendations.append(
                f"🔧 **Improve {worst_category[0]} handling:** This category shows low success rates and needs algorithm improvements."
            )

        # Error analysis
        failed_tests = [r for r in self.results if not r.get('success')]
        if failed_tests:
            common_errors = {}
            for test in failed_tests:
                error = test.get('error_message', 'Unknown error')
                common_errors[error] = common_errors.get(error, 0) + 1

            most_common_error = max(common_errors.items(), key=lambda x: x[1])
            if most_common_error[1] > len(failed_tests) * 0.3:  # More than 30% of failures
                recommendations.append(
                    f"🐛 **Address common error:** '{most_common_error[0]}' accounts for {most_common_error[1]} failures."
                )

        # Performance recommendations
        avg_time = self._calculate_average_response_time()
        if avg_time > 5.0:
            recommendations.append(
                f"⚡ **Optimize performance:** Average response time ({avg_time:.2f}s) exceeds acceptable limits."
            )

        if not recommendations:
            recommendations.append("✅ **Overall good performance:** No major issues identified in this evaluation.")

        for i, rec in enumerate(recommendations, 1):
            lines.append(f"{i}. {rec}")

        lines.extend([
            "",
            "---",
            "",
            f"*Report generated from {self.results_file.name} on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        ])

        return lines

    def _find_most_challenging_category(self) -> str:
        """Find the category with lowest success rate"""
        if not self.summary['categories']:
            return "Unknown"

        worst = min(self.summary['categories'].items(), key=lambda x: x[1].get('success_rate', 0))
        return f"{worst[0].title()} ({worst[1].get('success_rate', 0)*100:.1f}%)"

    def _calculate_average_response_time(self) -> float:
        """Calculate overall average response time"""
        times = [r.get('execution_time', 0) for r in self.results if r.get('execution_time')]
        return sum(times) / len(times) if times else 0.0

    def _get_category_insights(self, category: str, success_rate: float) -> str:
        """Get category-specific insights"""
        insights = {
            'simple': 'Basic element selection',
            'contextual': 'Requires DOM context understanding',
            'ambiguous': 'Multiple similar elements',
            'complex': 'Advanced XPath features needed'
        }

        base_insight = insights.get(category, 'Test category')

        if success_rate >= 90:
            return f"{base_insight} - Excellent"
        elif success_rate >= 70:
            return f"{base_insight} - Good"
        elif success_rate >= 50:
            return f"{base_insight} - Needs improvement"
        else:
            return f"{base_insight} - Major issues"

    def _generate_category_insights(self) -> List[str]:
        """Generate insights about category performance"""
        lines = []

        category_order = ['simple', 'contextual', 'ambiguous', 'complex']

        for category in category_order:
            if category in self.summary['categories']:
                stats = self.summary['categories'][category]
                success_rate = stats.get('success_rate', 0) * 100

                if category == 'simple' and success_rate < 80:
                    lines.append("- ⚠️ **Simple category underperforming** - Basic XPath generation needs improvement")
                elif category == 'complex' and success_rate > 70:
                    lines.append("- 🌟 **Strong complex handling** - Advanced XPath generation working well")
                elif category == 'ambiguous' and success_rate < 50:
                    lines.append("- 🎯 **Ambiguity resolution needed** - Multiple element scenarios need better handling")

        if not lines:
            lines.append("- 📊 Performance appears balanced across categories")

        return lines

def main():
    parser = argparse.ArgumentParser(description="Generate Storms evaluation report")
    parser.add_argument("results_file", help="Path to evaluation results JSON file")
    parser.add_argument("-o", "--output", help="Output markdown file path")

    args = parser.parse_args()

    try:
        reporter = EvaluationReporter(args.results_file)
        output_file = reporter.generate_markdown_report(args.output)
        print(f"✅ Report generated successfully: {output_file}")

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Failed to generate report: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())