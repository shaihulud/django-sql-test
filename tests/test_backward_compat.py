import json
import os
import tempfile
from unittest import TestCase

from django_sql_test.engine import FileEngine


class MockTestCase:
    _testMethodName = "test_method"

    def __str__(self):
        # The key format used by versions < 1.0: str(testcase)
        return "test_method (tests.TestClass)"

    @property
    def __class__(self):
        class MockClass:
            __module__ = "tests"
            __qualname__ = "TestClass"

        return MockClass


class LegacySnapshotKeyTestCase(TestCase):
    """Snapshot files written by versions < 1.0 must keep working after upgrade."""

    def setUp(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_file:
            self.temp_filename = temp_file.name
        self.addCleanup(os.unlink, self.temp_filename)

        self.test_case = MockTestCase()
        self.legacy_queries = [{"sql": "SELECT 1"}]
        with open(self.temp_filename, "w") as f:
            json.dump({str(self.test_case): self.legacy_queries}, f)

    def test_reads_legacy_key_when_new_key_is_missing(self):
        engine = FileEngine({"filename": self.temp_filename})

        self.assertEqual(engine.get_data_for_testcase(self.test_case, call_index=0), self.legacy_queries)
        # Pre-1.0 files hold a single snapshot per test, so only call_index=0 falls back
        self.assertEqual(engine.get_data_for_testcase(self.test_case, call_index=1), [])

    def test_write_migrates_legacy_key_to_new_format(self):
        engine = FileEngine({"filename": self.temp_filename})
        new_queries = [{"sql": "SELECT 2"}]

        engine.set_data_for_testcase(self.test_case, new_queries, call_index=0)

        with open(self.temp_filename, "r") as f:
            data = json.load(f)
        self.assertEqual(data, {"tests.TestClass.test_method:0": new_queries})
