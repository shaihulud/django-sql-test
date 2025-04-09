import difflib

from django.db import connections, DEFAULT_DB_ALIAS
from django.test.utils import CaptureQueriesContext
from sql_metadata.generalizator import Generalizator

from .engine import get_engine


def get_raw_queries(captured_queries):
    return [query["sql"] for query in captured_queries]


def generalize_queries(captured_queries):
    return [Generalizator(query).generalize for query in captured_queries]


def create_queries_diff(new_queries, old_queries, captured_queries):
    diff_list = difflib.ndiff(old_queries, new_queries)
    return "\n".join(diff_list)


class _AssertNumNewQueriesContext(CaptureQueriesContext):
    def __init__(self, test_case, num, connection):
        self.test_case = test_case
        self.num = num
        super().__init__(connection)

    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)
        if exc_type is not None:
            return

        executed = len(self)
        engine = get_engine()

        if executed == self.num:
            engine.set_data_for_testcase(self.test_case, self.captured_queries)
        else:
            new_queries = generalize_queries(get_raw_queries(self.captured_queries))
            old_queries = get_raw_queries(engine.get_data_for_testcase(self.test_case))
            queries_diff = create_queries_diff(new_queries, old_queries, self.captured_queries)
            self.test_case.assertEqual(
                executed,
                self.num,
                "%d queries executed, %d expected\nQueries diff was:\n%s\n\nCaptured queries were:\n%s" %
                (executed, self.num, queries_diff, "\n".join("%d. %s" % (i, query["sql"])
                    for i, query in enumerate(self.captured_queries, start=1))),
            )


class NumNewQueriesMixin:
    def assertNumQueries(self, num, func=None, *args, using=DEFAULT_DB_ALIAS, **kwargs):
        conn = connections[using]

        context = _AssertNumNewQueriesContext(self, num, conn)
        if func is None:
            return context

        with context:
            func(*args, **kwargs)

    def assertNumNewQueries(self, *args, **kwargs):
        return self.assertNumQueries(*args, **kwargs)
