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
            if SHOW_UPDATED_QUERIES:
                old_captured_queries = engine.get_data_for_testcase(self.test_case)
                builder = QueryDiffBuilder(self.captured_queries, old_captured_queries, color_scheme)

                if not builder.is_same:
                    queries_diff = builder.build_queries_diff(DIFF_ONLY, GENERALIZED_DIFF)
                    sys.stdout.write(
                        f"executed queries number is the same, but queries differ\nQueries diff:\n{queries_diff}\n"
                    )
            engine.set_data_for_testcase(self.test_case, self.captured_queries)
        else:
            old_captured_queries = engine.get_data_for_testcase(self.test_case)
            builder = QueryDiffBuilder(self.captured_queries, old_captured_queries, color_scheme)
            queries_diff = builder.build_queries_diff(DIFF_ONLY, GENERALIZED_DIFF)
            self.test_case.assertEqual(
                executed,
                self.num,
                "%d queries executed, %d expected\nQueries diff:\n%s" % (executed, self.num, queries_diff),
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
