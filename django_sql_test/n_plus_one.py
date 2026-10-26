"""
N+1 query problem detection for Django SQL queries.
"""

import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional, Union

from sql_metadata import Parser

from .diff_utils import generalize_query as generalize


# sql_metadata generalization placeholders: N (numbers), X/XX (strings, e.g. UUID keys), s (%s-style params).
# Case-sensitive on purpose. IN (XYZ) is deliberately excluded: repeated IN queries are usually
# prefetch_related batches, i.e. the fix for N+1 rather than the problem.
PARAM_PLACEHOLDER = re.compile(r"= (?:N|X+|s)\b")

# \b avoids matching "WHERE" inside an unrelated identifier (e.g. a table named "app_nowhere"); the
# non-greedy capture stops at the next clause keyword (or end of string) so PARAM_PLACEHOLDER below is
# checked only against the actual WHERE clause, not an unrelated JOIN/ON condition before it.
WHERE_CLAUSE = re.compile(r"\bWHERE\b(.*?)(?:\bGROUP BY\b|\bORDER BY\b|\bLIMIT\b|$)", re.IGNORECASE | re.DOTALL)


class Severity(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3

    @classmethod
    def parse(cls, value: Union["Severity", str]) -> "Severity":
        """Accept a Severity or its name ("low"/"medium"/"high", case-insensitive)."""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            try:
                return cls[value.upper()]
            except KeyError:
                valid = ", ".join(s.name.lower() for s in cls)
                raise ValueError(f"Invalid N+1 severity {value!r}; expected one of {valid}") from None
        raise TypeError(f"N+1 severity must be a str or Severity, got {type(value).__name__}")


HIGH_SEVERITY_THRESHOLD = 10
MEDIUM_SEVERITY_THRESHOLD = 5


def _calculate_severity(count: int) -> Severity:
    if count >= HIGH_SEVERITY_THRESHOLD:
        return Severity.HIGH
    if count >= MEDIUM_SEVERITY_THRESHOLD:
        return Severity.MEDIUM
    return Severity.LOW


def truncate_text(s: str, max_len: int) -> str:
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
    severity: Severity = Severity.MEDIUM
    test_case: Optional[str] = None

    def __str__(self):
        return f"N+1 Problem: {self.count} similar queries on {self.base_table or 'unknown table'}"


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

    # Group queries by (first table, generalized pattern) to separate different tables
    groups = defaultdict(list)
    for query in queries:
        sql = query.get("sql") or ""
        if not sql:
            continue
        tables = get_tables(sql)
        pattern = generalize(sql)
        base_table = tables[0] if tables else None
        groups[(base_table, pattern)].append({"sql": sql, "tables": tables})

    # Detect N+1 patterns
    problems = []
    for (base_table, pattern), group_queries in groups.items():
        if len(group_queries) < 2:
            continue

        # Skip identical queries (not N+1, just repeated same query)
        if len(set(q["sql"] for q in group_queries)) == 1:
            continue

        # N+1 indicator: WHERE clause with a parameter placeholder (typical FK lookup)
        where_match = WHERE_CLAUSE.search(pattern)
        if where_match is None or not PARAM_PLACEHOLDER.search(where_match.group(1)):
            continue

        count = len(group_queries)
        tables = group_queries[0]["tables"]
        problems.append(
            N1Problem(
                pattern=pattern,
                count=count,
                similar_queries=[{"sql": q["sql"]} for q in group_queries],
                base_table=base_table,
                joined_tables=tables[1:] or None,
                severity=_calculate_severity(count),
            )
        )

    problems.sort(key=severity_sort_key, reverse=True)
    return problems


def severity_sort_key(problem: N1Problem) -> tuple:
    return (problem.severity, problem.count)


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


def filter_by_severity(problems: List[N1Problem], threshold: Union[Severity, str] = Severity.MEDIUM) -> List[N1Problem]:
    """Filter problems by minimum severity threshold. Accepts a Severity or its name."""
    threshold = Severity.parse(threshold)
    return [p for p in problems if p.severity >= threshold]


def format_problem_body(problem: N1Problem, index: int, detailed: bool = False) -> List[str]:
    """Format the per-problem detail lines (test, pattern, example queries, suggestions).

    Shared by the inline assertNumQueries warning and the analyze_n_plus_one command, so a
    change to one doesn't silently drift out of sync with the other.
    """
    lines = []
    if problem.test_case:
        lines.append(f"   Test: {problem.test_case}")

    pattern = problem.pattern if detailed else truncate_text(problem.pattern, 100)
    lines.append(f"   Pattern: {pattern}")

    if problem.similar_queries:
        examples = problem.similar_queries if detailed else problem.similar_queries[:3]
        lines.append("   Example queries:")
        for j, query in enumerate(examples, 1):
            sql = query.get("sql", "")
            if not detailed:
                sql = truncate_text(sql, 80)
            lines.append(f"     {j}. {sql}")
        remaining = len(problem.similar_queries) - len(examples)
        if remaining > 0:
            lines.append(f"     ... and {remaining} more")

    # Show suggestions for top 3 problems
    if index <= 3:
        suggestions = get_suggestions(problem)[:2]
        if suggestions:
            lines.append("   Suggestions:")
            for suggestion in suggestions:
                lines.append(f"     - {suggestion}")

    return lines


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
        lines.append(f"   Severity: {problem.severity.name}")
        lines.extend(format_problem_body(problem, i, detailed))

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


def print_problems(problems: List[N1Problem], detailed: bool = False, file=None):
    """Print N+1 problems to stdout or specified file."""
    output = format_problems_text(problems, detailed)
    if output:
        dest = file or sys.stdout
        dest.write(output)
        dest.write("\n")
