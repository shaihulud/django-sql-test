import json
import os
import tempfile
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError

from django_sql_test.engine import Engine, FileEngine


class NoBulkAccessEngine(Engine):
    """An engine that does not override get_all_data()."""

    def get_data_for_testcase(self, testcase, call_index=0):
        return []

    def set_data_for_testcase(self, testcase, captured_queries, call_index=0):
        pass


class AnalyzeNPlusOneCommandTestCase(TestCase):
    def _make_engine_with_n1_data(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_file:
            temp_filename = temp_file.name
        self.addCleanup(os.unlink, temp_filename)

        queries = [{"sql": f"SELECT * FROM posts WHERE user_id = {i}"} for i in range(5)]
        with open(temp_filename, "w") as f:
            json.dump({"tests.TestClass.test_method:0": queries}, f)

        return FileEngine({"filename": temp_filename})

    def test_json_output_reports_problems(self):
        engine = self._make_engine_with_n1_data()

        stdout = StringIO()
        stderr = StringIO()
        with patch("django_sql_test.management.commands.analyze_n_plus_one.get_engine", return_value=engine):
            call_command("analyze_n_plus_one", "--format", "json", stdout=stdout, stderr=stderr)

        # stdout must be valid JSON on its own (e.g. pipeable to `jq`); status messages go to stderr.
        problems = json.loads(stdout.getvalue())
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0]["test_case"], "tests.TestClass.test_method:0")
        self.assertEqual(problems[0]["count"], 5)
        self.assertIn("joined_tables", problems[0])

    def test_json_output_detailed_includes_all_example_queries(self):
        engine = self._make_engine_with_n1_data()  # 5 similar queries

        stdout = StringIO()
        with patch("django_sql_test.management.commands.analyze_n_plus_one.get_engine", return_value=engine):
            call_command("analyze_n_plus_one", "--format", "json", "--detailed", stdout=stdout, stderr=StringIO())

        problems = json.loads(stdout.getvalue())
        self.assertEqual(len(problems[0]["example_queries"]), 5)

    def test_json_output_without_detailed_truncates_example_queries(self):
        engine = self._make_engine_with_n1_data()  # 5 similar queries

        stdout = StringIO()
        with patch("django_sql_test.management.commands.analyze_n_plus_one.get_engine", return_value=engine):
            call_command("analyze_n_plus_one", "--format", "json", stdout=stdout, stderr=StringIO())

        problems = json.loads(stdout.getvalue())
        self.assertEqual(len(problems[0]["example_queries"]), 3)

    def test_json_output_is_empty_array_when_no_data(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_file:
            temp_filename = temp_file.name
        self.addCleanup(os.unlink, temp_filename)
        with open(temp_filename, "w") as f:
            json.dump({}, f)
        engine = FileEngine({"filename": temp_filename})

        stdout = StringIO()
        with patch("django_sql_test.management.commands.analyze_n_plus_one.get_engine", return_value=engine):
            call_command("analyze_n_plus_one", "--format", "json", stdout=stdout, stderr=StringIO())

        self.assertEqual(json.loads(stdout.getvalue()), [])

    def test_text_output_reports_true_total_when_top_truncates(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_file:
            temp_filename = temp_file.name
        self.addCleanup(os.unlink, temp_filename)

        # 15 distinct N+1 problems, all at MEDIUM severity
        data = {
            f"tests.T.test_{t}:0": [{"sql": f"SELECT * FROM table_{t} WHERE user_id = {i}"} for i in range(5)]
            for t in range(15)
        }
        with open(temp_filename, "w") as f:
            json.dump(data, f)
        engine = FileEngine({"filename": temp_filename})

        stdout = StringIO()
        with patch("django_sql_test.management.commands.analyze_n_plus_one.get_engine", return_value=engine):
            call_command("analyze_n_plus_one", stdout=stdout, stderr=StringIO())  # default --top 10

        output = stdout.getvalue()
        self.assertIn("Found 15 N+1 query problems", output)
        self.assertIn("showing top 10", output)
        self.assertIn("Medium", output)
        self.assertIn(": 15 problems", output)

    def test_negative_top_raises_command_error(self):
        engine = self._make_engine_with_n1_data()

        with patch("django_sql_test.management.commands.analyze_n_plus_one.get_engine", return_value=engine):
            with self.assertRaises(CommandError) as ctx:
                call_command("analyze_n_plus_one", "--top", "-2", stdout=StringIO(), stderr=StringIO())

        self.assertIn("--top", str(ctx.exception))

    def test_zero_top_raises_command_error(self):
        engine = self._make_engine_with_n1_data()

        with patch("django_sql_test.management.commands.analyze_n_plus_one.get_engine", return_value=engine):
            with self.assertRaises(CommandError):
                call_command("analyze_n_plus_one", "--top", "0", stdout=StringIO(), stderr=StringIO())

    def test_engine_without_bulk_access_raises_command_error(self):
        with patch(
            "django_sql_test.management.commands.analyze_n_plus_one.get_engine", return_value=NoBulkAccessEngine({})
        ):
            with self.assertRaises(CommandError) as ctx:
                call_command("analyze_n_plus_one", stdout=StringIO())

        self.assertIn("get_all_data", str(ctx.exception))
