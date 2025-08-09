import sys

from django.db import connections, DEFAULT_DB_ALIAS
from django.test.utils import CaptureQueriesContext

from .app_settings import (
    DIFF_DEFAULT_COLOR,
    DIFF_NEW_COLOR,
    DIFF_OLD_COLOR,
    DIFF_ONLY,
    GENERALIZED_DIFF,
    SHOW_UPDATED_QUERIES,
)
from .diff_utils import ColorScheme, QueryDiffBuilder
from .engine import get_engine


color_scheme = ColorScheme(added=DIFF_NEW_COLOR, removed=DIFF_OLD_COLOR, unchanged=DIFF_DEFAULT_COLOR)


class _AssertNumNewQueriesContext(CaptureQueriesContext):
    def __init__(self, test_case, num, connection, call_index):
        self.test_case = test_case
        self.num = num
        self.call_index = call_index
        super().__init__(connection)

    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)
        if exc_type is not None:
            return

        executed = len(self)
        engine = get_engine()

        if executed == self.num:
            if SHOW_UPDATED_QUERIES:
                old_captured_queries = engine.get_data_for_testcase(self.test_case, self.call_index)
                builder = QueryDiffBuilder(self.captured_queries, old_captured_queries, color_scheme)

                if not builder.is_same:
                    queries_diff = builder.build_queries_diff(DIFF_ONLY, GENERALIZED_DIFF)
                    sys.stdout.write(
                        f"executed queries number is the same, but queries differ\nQueries diff:\n{queries_diff}\n"
                    )
            engine.set_data_for_testcase(self.test_case, self.captured_queries, self.call_index)
        else:
            old_captured_queries = engine.get_data_for_testcase(self.test_case, self.call_index)
            builder = QueryDiffBuilder(self.captured_queries, old_captured_queries, color_scheme)
            queries_diff = builder.build_queries_diff(DIFF_ONLY, GENERALIZED_DIFF)
            self.test_case.assertEqual(
                executed,
                self.num,
                "%d queries executed, %d expected\nQueries diff:\n%s" % (executed, self.num, queries_diff),
            )


class NumNewQueriesMixin:
    def _get_call_index(self):
        current_test_method = getattr(self, "_testMethodName", "unknown_test")

        if not hasattr(self, "_query_call_data"):
            self._query_call_data = {"current_method": current_test_method, "counter": 0}

        if self._query_call_data["current_method"] != current_test_method:
            self._query_call_data["current_method"] = current_test_method
            self._query_call_data["counter"] = 0

        call_index = self._query_call_data["counter"]
        self._query_call_data["counter"] += 1

        return call_index

    def assertNumQueries(self, num, func=None, *args, using=DEFAULT_DB_ALIAS, **kwargs):
        conn = connections[using]
        call_index = self._get_call_index()

        context = _AssertNumNewQueriesContext(self, num, conn, call_index)
        if func is None:
            return context

        with context:
            func(*args, **kwargs)

    def assertNumNewQueries(self, *args, **kwargs):
        return self.assertNumQueries(*args, **kwargs)
