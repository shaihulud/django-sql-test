import unittest

from django_sql_test.diff_utils import create_queries_diff


class CreateQueriesDiffTestCase(unittest.TestCase):
    def setUp(self):
        self.new_captured_queries = [
            {"sql": "SELECT a.a, a.b, a.c FROM a WHERE a.z = '12' AND a.m IN (1, 2)"},
            {"sql": "SELECT b.a, b.b, b.c FROM b LIMIT 21"},
        ]

    def test_empty_old_generalized_diff(self):
        expected_result = [
            "SELECT a.a, a.b, a.c FROM a WHERE a.z = X AND a.m IN (XYZ)",
            "SELECT b.a, b.b, b.c FROM b LIMIT N",
        ]
        result = create_queries_diff(
            new_captured_queries=self.new_captured_queries,
            old_captured_queries=[],
            diff_only=False,
            generalized_diff=True,
        )
        self.assertEqual(result.split("\n"), expected_result)

    def test_empty_old_regular_diff_shows_context(self):
        expected_result = [
            "SELECT a.a, a.b, a.c FROM a WHERE a.z = '12' AND a.m IN (1, 2)",
            "SELECT b.a, b.b, b.c FROM b LIMIT 21",
        ]
        result = create_queries_diff(
            new_captured_queries=self.new_captured_queries,
            old_captured_queries=[],
            diff_only=False,
            generalized_diff=False,
        )
        self.assertEqual(list(map(str.strip, result.split("\n"))), expected_result)

    def test_empty_old_regular_diff_only_true_hides_context(self):
        result = create_queries_diff(
            new_captured_queries=self.new_captured_queries,
            old_captured_queries=[],
            diff_only=True,
            generalized_diff=False,
        )
        self.assertEqual(result, "")

    def test_nonempty_old_generalized_no_diff_only(self):
        expected_result = [
            "  SELECT a.a, a.b, a.c FROM a WHERE a.z = X AND a.m IN (XYZ)",
            "+ SELECT b.a, b.b, b.c FROM b LIMIT N",
        ]
        result = create_queries_diff(
            new_captured_queries=self.new_captured_queries,
            old_captured_queries=self.new_captured_queries[:1],
            diff_only=False,
            generalized_diff=True,
        )
        self.assertEqual(result.split("\n"), expected_result)

    def test_nonempty_old_generalized_diff_only(self):
        expected_result = [
            "+ SELECT b.a, b.b, b.c FROM b LIMIT N",
        ]
        result = create_queries_diff(
            new_captured_queries=self.new_captured_queries,
            old_captured_queries=self.new_captured_queries[:1],
            diff_only=True,
            generalized_diff=True,
        )
        self.assertEqual(result.split("\n"), expected_result)

    def test_nonempty_old_regular_diff(self):
        expected_result = [
            "  SELECT a.a, a.b, a.c FROM a WHERE a.z = '12' AND a.m IN (1, 2)",
            "+ SELECT b.a, b.b, b.c FROM b LIMIT 21",
        ]
        result = create_queries_diff(
            new_captured_queries=self.new_captured_queries,
            old_captured_queries=self.new_captured_queries[:1],
            diff_only=False,
            generalized_diff=False,
        )
        self.assertEqual(result.split("\n"), expected_result)

    def test_nonempty_old_regular_diff_only(self):
        expected_result = [
            "+ SELECT b.a, b.b, b.c FROM b LIMIT 21",
        ]
        result = create_queries_diff(
            new_captured_queries=self.new_captured_queries,
            old_captured_queries=self.new_captured_queries[:1],
            diff_only=True,
            generalized_diff=False,
        )
        self.assertEqual(result.split("\n"), expected_result)

    def test_question_lines_are_filtered(self):
        expected_result = [
            "- SELECT b.a, b.b, b.c FROM b LIMIT N",  # TODO: fix this
            "+ SELECT b.a, b.b, b.c, b.d FROM b LIMIT 21",
        ]
        result = create_queries_diff(
            new_captured_queries=[{"sql": "SELECT b.a, b.b, b.c, b.d FROM b LIMIT 21"}],
            old_captured_queries=[{"sql": "SELECT b.a, b.b, b.c FROM b LIMIT 21"}],
            diff_only=False,
            generalized_diff=False,
        )
        self.assertEqual(result.split("\n"), expected_result)

    def test_deletion_only_new_empty(self):
        result = create_queries_diff(
            new_captured_queries=[],
            old_captured_queries=[{"sql": "SELECT b.a, b.b, b.c FROM b LIMIT 21"}],
            diff_only=False,
            generalized_diff=False,
        )
        self.assertEqual(result, "- SELECT b.a, b.b, b.c FROM b LIMIT N")
