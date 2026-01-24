"""
N+1 query problem detection for Django SQL queries.
"""

import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

from sql_metadata import Parser
from sql_metadata.generalizator import Generalizator


Severity = Literal["low", "medium", "high"]
SEVERITY_LEVELS: Dict[Severity, int] = {"low": 1, "medium": 2, "high": 3}

HIGH_SEVERITY_THRESHOLD = 10
MEDIUM_SEVERITY_THRESHOLD = 5


def _calculate_severity(count: int) -> Severity:
    if count >= HIGH_SEVERITY_THRESHOLD:
        return "high"
    if count >= MEDIUM_SEVERITY_THRESHOLD:
        return "medium"
    return "low"


def _truncate(s: str, max_len: int) -> str:
    """Truncate string with ellipsis if longer than max_len."""
    return s if len(s) <= max_len else f"{s[:max_len]}..."


@dataclass
class N1Problem:
    """Represents a detected N+1 problem."""

    pattern: str
    count: int
    similar_queries: List[dict] = field(default_factory=list)
    base_table: Optional[str] = None
    joined_tables: Optional[List[str]] = None
    severity: Severity = "medium"
    test_case: Optional[str] = None

    def __str__(self):
        return f"N+1 Problem: {self.count} similar queries on {self.base_table or 'unknown table'}"


def generalize(sql: str) -> str:
    """Generalize SQL query for pattern matching. Uses sql_metadata."""
    try:
        return Generalizator(sql).generalize
    except Exception:
        return sql  # Return original on parse failure


def get_tables(sql: str) -> List[str]:
    """Extract all tables from SQL query. Uses sql_metadata."""
    try:
        return Parser(sql).tables
    except Exception:
        return []


def analyze_queries(queries: List[dict]) -> List[N1Problem]:
    """Analyze queries for N+1 problems."""
    if not queries:
        return []

    # Group queries by generalized pattern
    groups = defaultdict(list)
    for query in queries:
        sql = query.get("sql") or ""
        if not sql:
            continue
        tables = get_tables(sql)
        pattern = generalize(sql)
        # Use first table + pattern as key to separate different tables
        key = f"{tables[0] if tables else 'unknown'}:{pattern}"
        groups[key].append({"sql": sql, "tables": tables})

    # Detect N+1 patterns
    problems = []
    for group_key, group_queries in groups.items():
        if len(group_queries) < 2:
            continue

        # Skip identical queries (not N+1, just repeated same query)
        if len(set(q["sql"] for q in group_queries)) == 1:
            continue

        base_table, pattern = group_key.split(":", 1)
        if base_table == "unknown":
            base_table = None

        # N+1 indicator: WHERE clause with parameter (typical FK lookup)
        pattern_upper = pattern.upper()
        if "WHERE" not in pattern_upper or "= N" not in pattern_upper:
            continue

        count = len(group_queries)
        tables = group_queries[0]["tables"]
        problems.append(
            N1Problem(
                pattern=pattern,
                count=count,
                similar_queries=[{"sql": q["sql"]} for q in group_queries],
                base_table=base_table,
                joined_tables=tables[1:] if len(tables) > 1 else None,
                severity=_calculate_severity(count),
            )
        )

    problems.sort(key=lambda p: (SEVERITY_LEVELS[p.severity], p.count), reverse=True)
    return problems


def get_suggestions(problem: N1Problem) -> List[str]:
    """Get suggestions for fixing the N+1 problem."""
    suggestions = []
    if problem.joined_tables:
        tables = ", ".join(problem.joined_tables)
        suggestions.append(f"Consider using select_related() to JOIN {tables} in a single query")
    if problem.base_table:
        suggestions.append(f"Use prefetch_related() to fetch related {problem.base_table} objects in batches")
    suggestions.append("Review if all these queries are necessary")
    return suggestions


def filter_by_severity(problems: List[N1Problem], threshold: Severity = "medium") -> List[N1Problem]:
    """Filter problems by minimum severity threshold."""
    threshold_level = SEVERITY_LEVELS.get(threshold, 2)
    return [p for p in problems if SEVERITY_LEVELS.get(p.severity, 1) >= threshold_level]


def format_problems_text(problems: List[N1Problem], detailed: bool = False) -> str:
    """Format N+1 problems as human-readable text."""
    if not problems:
        return ""

    lines = [
        "",
        "=" * 60,
        "POTENTIAL N+1 QUERY PROBLEMS DETECTED",
        "=" * 60,
    ]

    for i, problem in enumerate(problems, 1):
        lines.append(f"\n{i}. {problem}")
        lines.append(f"   Severity: {problem.severity.upper()}")
        if problem.test_case:
            lines.append(f"   Test: {problem.test_case}")

        lines.append(f"   Pattern: {_truncate(problem.pattern, 100)}")

        if detailed and problem.similar_queries:
            lines.append("   Example queries:")
            for j, query in enumerate(problem.similar_queries[:5], 1):
                lines.append(f"     {j}. {query.get('sql', '')}")
            if len(problem.similar_queries) > 5:
                lines.append(f"     ... and {len(problem.similar_queries) - 5} more")
        elif problem.similar_queries:
            lines.append("   Example queries:")
            for j, query in enumerate(problem.similar_queries[:3], 1):
                lines.append(f"     {j}. {_truncate(query.get('sql', ''), 80)}")
            if len(problem.similar_queries) > 3:
                lines.append(f"     ... and {len(problem.similar_queries) - 3} more similar queries")

    lines.append("\nSUGGESTIONS:")
    for i, suggestion in enumerate(get_suggestions(problems[0]), 1):
        lines.append(f"   {i}. {suggestion}")

    lines.append("=" * 60)
    return "\n".join(lines)


def print_problems(problems: List[N1Problem], detailed: bool = False, file=None):
    """Print N+1 problems to stdout or specified file."""
    output = format_problems_text(problems, detailed)
    if output:
        dest = file or sys.stdout
        dest.write(output)
        dest.write("\n")


# Backwards compatibility - deprecated, use module functions directly
class N1Analyzer:
    """Deprecated: Use module functions directly (analyze_queries, get_suggestions, etc.)."""

    @staticmethod
    def normalize_query(sql: str) -> str:
        return generalize(sql)

    @staticmethod
    def extract_table_info(sql: str) -> Dict[str, List[str]]:
        tables = get_tables(sql)
        return {
            "tables": tables[:1] if tables else [],
            "joins": tables[1:] if len(tables) > 1 else [],
            "where_columns": [],
        }

    @staticmethod
    def group_similar_queries(queries: List[dict]) -> Dict[str, List[dict]]:
        groups: Dict[str, List[dict]] = defaultdict(list)
        for query in queries:
            sql = query.get("sql") or ""
            if not sql:
                continue
            tables = get_tables(sql)
            key = f"{tables[0] if tables else 'unknown'}:{generalize(sql)}"
            groups[key].append(query)
        return dict(groups)

    @staticmethod
    def analyze_queries(queries: List[dict]) -> List[N1Problem]:
        return analyze_queries(queries)

    @staticmethod
    def get_suggestions(problem: N1Problem) -> List[str]:
        return get_suggestions(problem)


def analyze_queries_for_n1(queries: List[dict]) -> List[N1Problem]:
    """Convenience function to analyze queries for N+1 problems."""
    return analyze_queries(queries)
