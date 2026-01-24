"""
Django management command to analyze stored test queries for N+1 problems.
"""

import json
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.utils.termcolors import make_style

from django_sql_test.engine import get_engine
from django_sql_test.n_plus_one import analyze_queries, filter_by_severity, get_suggestions, SEVERITY_LEVELS


class Command(BaseCommand):
    help = "Analyze stored test queries for N+1 query problems"

    def add_arguments(self, parser):
        parser.add_argument(
            "--severity",
            choices=["low", "medium", "high"],
            default="medium",
            help="Minimum severity level to report (default: medium)",
        )
        parser.add_argument(
            "--test-pattern", type=str, help='Filter tests by pattern (e.g., "test_user" or "UserTestCase")'
        )
        parser.add_argument("--top", type=int, default=10, help="Show top N worst problems (default: 10)")
        parser.add_argument(
            "--detailed", action="store_true", help="Show detailed analysis including all example queries"
        )
        parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format (default: text)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_error = make_style(opts=("bold",), fg="red")
        self.style_warning = make_style(opts=("bold",), fg="yellow")
        self.style_success = make_style(opts=("bold",), fg="green")
        self.style_info = make_style(fg="cyan")

    def handle(self, *args, **options):
        severity_threshold = options["severity"]
        test_pattern = options.get("test_pattern")
        top_n = options["top"]
        detailed = options["detailed"]
        output_format = options["format"]

        self.stdout.write(self.style_info("Analyzing stored test queries for N+1 problems..."))

        try:
            engine = get_engine()
        except Exception as e:
            raise CommandError(f"Failed to initialize engine: {e}")

        # Get all stored data
        try:
            if hasattr(engine, "data"):
                all_data = engine.data
            else:
                raise CommandError("Engine does not support direct data access for analysis")
        except Exception as e:
            raise CommandError(f"Failed to retrieve test data: {e}")

        if not all_data:
            self.stdout.write(self.style_warning("No test data found. Run some tests first."))
            return

        # Filter by test pattern if provided
        if test_pattern:
            all_data = {k: v for k, v in all_data.items() if test_pattern.lower() in k.lower()}

        if not all_data:
            self.stdout.write(self.style_warning(f"No test data matches pattern '{test_pattern}'"))
            return

        # Analyze each test case
        all_problems = []
        for test_key, queries in all_data.items():
            if not queries:
                continue
            for problem in analyze_queries(queries):
                problem.test_case = test_key
                all_problems.append(problem)

        if not all_problems:
            self.stdout.write(self.style_success("No N+1 problems detected!"))
            return

        # Filter by severity and sort
        filtered_problems = filter_by_severity(all_problems, severity_threshold)

        if not filtered_problems:
            self.stdout.write(
                self.style_success(f"No N+1 problems found at '{severity_threshold}' severity or higher!")
            )
            return

        filtered_problems.sort(key=lambda p: (SEVERITY_LEVELS.get(p.severity, 1), p.count), reverse=True)
        top_problems = filtered_problems[:top_n]

        # Output results
        if output_format == "json":
            self._output_json(top_problems)
        else:
            self._output_text(top_problems, detailed)

    def _output_text(self, problems, detailed):
        """Output problems in human-readable text format."""
        self.stdout.write(self.style_error(f"\nFound {len(problems)} N+1 query problems:\n"))

        severity_style = {"high": self.style_error, "medium": self.style_warning, "low": self.style_info}

        for i, problem in enumerate(problems, 1):
            style = severity_style.get(problem.severity, self.style_info)
            self.stdout.write(f"\n{i}. {style(problem.severity.upper())} - {problem}")
            self.stdout.write(f"   Test: {problem.test_case or 'Unknown'}")

            pattern = problem.pattern if detailed or len(problem.pattern) <= 80 else f"{problem.pattern[:77]}..."
            self.stdout.write(f"   Pattern: {pattern}")

            if detailed and problem.similar_queries:
                self.stdout.write("   Example queries:")
                for j, query in enumerate(problem.similar_queries[:5], 1):
                    self.stdout.write(f"     {j}. {query.get('sql', '')}")
                if len(problem.similar_queries) > 5:
                    self.stdout.write(f"     ... and {len(problem.similar_queries) - 5} more")

            # Show suggestions for top 3 problems
            if i <= 3:
                suggestions = get_suggestions(problem)[:2]
                if suggestions:
                    self.stdout.write("   Suggestions:")
                    for suggestion in suggestions:
                        self.stdout.write(f"     - {suggestion}")

        # Summary
        severity_counts = defaultdict(int)
        for problem in problems:
            severity_counts[problem.severity] += 1

        self.stdout.write("\nSummary:")
        for severity in ["high", "medium", "low"]:
            if severity_counts[severity]:
                style = severity_style[severity]
                self.stdout.write(f"   {style(severity.capitalize())}: {severity_counts[severity]} problems")

    def _output_json(self, problems):
        """Output problems in JSON format."""
        json_data = [
            {
                "test_case": problem.test_case or "Unknown",
                "severity": problem.severity,
                "count": problem.count,
                "pattern": problem.pattern,
                "base_table": problem.base_table,
                "joined_table": problem.joined_table,
                "example_queries": [q.get("sql", "") for q in problem.similar_queries[:3]],
            }
            for problem in problems
        ]
        self.stdout.write(json.dumps(json_data, indent=2))
