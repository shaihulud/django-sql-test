import difflib

from sql_metadata.generalizator import Generalizator


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
        return "\n".join(generalized_diff_list)

    idx = 0
    diff_list = []

    for line in generalized_diff_list:
        if line.startswith("-"):
            diff_list.append(line)
        elif line.startswith("+"):
            diff_list.append("+ " + new_captured_queries[idx]["sql"])
            idx += 1
        else:
            if not diff_only:
                diff_list.append("  " + new_captured_queries[idx]["sql"])
            idx += 1

    return "\n".join(diff_list)
