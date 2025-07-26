import difflib
from dataclasses import dataclass
from enum import Enum

from sql_metadata.generalizator import Generalizator

from .app_settings import DIFF_DEFAULT_COLOR, DIFF_NEW_COLOR, DIFF_OLD_COLOR


red_color = "\033[1;31m"
green_color = "\033[1;32m"
reset_color = "\033[0m"

old_color = DIFF_OLD_COLOR or red_color
new_color = DIFF_NEW_COLOR or green_color
default_color = DIFF_DEFAULT_COLOR or reset_color


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


def create_queries_diff(
    new_captured_queries: list[dict],
    old_captured_queries: list[dict],
    diff_only: bool,
    generalized_diff: bool,
) -> tuple[str, bool]:
    is_same = True
    queries_diff_list = build_queries_diff_list(new_captured_queries, old_captured_queries)

    diff_list = []
    for diff_line in queries_diff_list:
        query = diff_line.get_query(generalized_diff)

        if diff_line.diff_type == DiffType.REMOVED:
            is_same = False
            diff_list.append(old_color + query + reset_color)
        elif diff_line.diff_type == DiffType.ADDED:
            is_same = False
            diff_list.append(new_color + query + reset_color)
        else:  # DiffType.UNCHANGED
            if not diff_only:
                diff_list.append(default_color + query + reset_color)

    return "\n".join(diff_list), is_same
