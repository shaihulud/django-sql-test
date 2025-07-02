import difflib

from sql_metadata.generalizator import Generalizator

from .app_settings import DIFF_DEFAULT_COLOR, DIFF_NEW_COLOR, DIFF_OLD_COLOR


red_color = "\033[1;31m"
green_color = "\033[1;32m"
reset_color = "\033[0m"

old_color = DIFF_OLD_COLOR or red_color
new_color = DIFF_NEW_COLOR or green_color
default_color = DIFF_DEFAULT_COLOR or reset_color


def get_raw_queries(captured_queries: list[dict]) -> list[str]:
    return [query["sql"] for query in captured_queries]


def generalize_queries(captured_queries: list[str]) -> list[str]:
    return [Generalizator(query).generalize for query in captured_queries]


def create_queries_diff(
    new_captured_queries: list[dict],
    old_captured_queries: list[dict],
    diff_only: bool,
    generalized_diff: bool,
) -> str:
    new_queries = generalize_queries(get_raw_queries(new_captured_queries))
    old_queries = generalize_queries(get_raw_queries(old_captured_queries))

    if not old_queries:
        generalized_diff_list = new_queries
    else:
        generalized_diff_list = (i for i in difflib.ndiff(old_queries, new_queries) if not i.startswith("?"))

    if generalized_diff:
        if diff_only and old_queries:
            generalized_diff_list = (i for i in generalized_diff_list if i.startswith("+") or i.startswith("-"))

        diff_list = []

        for line in generalized_diff_list:
            if line.startswith("-"):
                diff_list.append(old_color + line + reset_color)
            elif line.startswith("+"):
                diff_list.append(new_color + line + reset_color)
            else:
                diff_list.append(default_color + line + reset_color)

        return "\n".join(diff_list)

    idx = 0
    diff_list = []

    for line in generalized_diff_list:
        if line.startswith("-"):
            diff_list.append(old_color + line + reset_color)
        elif line.startswith("+"):
            diff_list.append(new_color + "+ " + new_captured_queries[idx]["sql"] + reset_color)
            idx += 1
        else:
            if not diff_only:
                diff_list.append(default_color + "  " + new_captured_queries[idx]["sql"] + reset_color)
            idx += 1

    return "\n".join(diff_list)
