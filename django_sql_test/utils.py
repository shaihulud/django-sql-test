from django.db import connections, DEFAULT_DB_ALIAS
from django.test.utils import CaptureQueriesContext

from .app_settings import DIFF_ONLY, GENERALIZED_DIFF
from .diff_utils import create_queries_diff
from .engine import get_engine


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
            old_captured_queries = engine.get_data_for_testcase(self.test_case)
            queries_diff = create_queries_diff(self.captured_queries, old_captured_queries, DIFF_ONLY, GENERALIZED_DIFF)
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
