import difflib
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from sql_metadata.generalizator import Generalizator


class DiffType(Enum):
    ADDED = "+"
    REMOVED = "-"
    UNCHANGED = " "


@dataclass
class DiffLine:
    diff_type: DiffType
    original_query: str
    generalized_query: str

    def get_query(self, is_generalized: bool) -> str:
        return self.generalized_query if is_generalized else self.original_query


class ColorScheme:
    red_color = "\033[1;31m"
    green_color = "\033[1;32m"
    reset = "\033[0m"

    def __init__(self, added: str, removed: str, unchanged: str):
        self.color_map = {
            DiffType.ADDED: added or self.green_color,
            DiffType.REMOVED: removed or self.red_color,
            DiffType.UNCHANGED: unchanged or self.reset,
        }

    def get_color(self, diff_type: DiffType) -> str:
        return self.color_map.get(diff_type) or self.reset


def get_raw_queries(captured_queries: list[dict]) -> list[str]:
    return [query["sql"] for query in captured_queries]


def generalize_queries(captured_queries: list[str]) -> list[str]:
    return [Generalizator(query).generalize for query in captured_queries]


def build_queries_diff_list(new_captured_queries: list[dict], old_captured_queries: list[dict]) -> list[DiffLine]:
    new_queries = generalize_queries(get_raw_queries(new_captured_queries))
    old_queries = generalize_queries(get_raw_queries(old_captured_queries))

    new_query_idx = 0
    old_query_idx = 0
    queries_diff_list = []

    for diff_line in difflib.ndiff(old_queries, new_queries):
        if diff_line.startswith("?"):
            continue

        if diff_line.startswith("-"):
            original_query = old_captured_queries[old_query_idx]["sql"]
            original_query = f"- {original_query}"
            queries_diff_list.append(
                DiffLine(diff_type=DiffType.REMOVED, original_query=original_query, generalized_query=diff_line)
            )
            old_query_idx += 1
        elif diff_line.startswith("+"):
            original_query = new_captured_queries[new_query_idx]["sql"]
            original_query = f"+ {original_query}"
            queries_diff_list.append(
                DiffLine(diff_type=DiffType.ADDED, original_query=original_query, generalized_query=diff_line)
            )
            new_query_idx += 1
        else:
            original_query = new_captured_queries[new_query_idx]["sql"]
            original_query = f"  {original_query}"
            queries_diff_list.append(
                DiffLine(diff_type=DiffType.UNCHANGED, original_query=original_query, generalized_query=diff_line)
            )
            new_query_idx += 1
            old_query_idx += 1

    return queries_diff_list


@dataclass
class QueryDiffBuilder:
    new_captured_queries: list[dict]
    old_captured_queries: list[dict]
    color_scheme: Optional[ColorScheme] = None

    def __post_init__(self):
        self.queries_diff_list = build_queries_diff_list(self.new_captured_queries, self.old_captured_queries)

        self.is_same = True
        for diff_line in self.queries_diff_list:
            if diff_line.diff_type != DiffType.UNCHANGED:
                self.is_same = False
                break

    def build_queries_diff(self, show_diff_only: bool, show_generalized_diff: bool) -> str:
        diff_list = []
        for diff_line in self.queries_diff_list:
            if show_diff_only and diff_line.diff_type == DiffType.UNCHANGED:
                continue

            query = diff_line.get_query(show_generalized_diff)

            if self.color_scheme:
                color = self.color_scheme.get_color(diff_line.diff_type)
                query = f"{color}{query}{self.color_scheme.reset}"

            diff_list.append(query)

        return "\n".join(diff_list)
