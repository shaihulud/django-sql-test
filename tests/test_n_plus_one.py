import unittest

from django_sql_test.n_plus_one import (
    analyze_queries,
    filter_by_severity,
    format_problem_body,
    format_problems_text,
    generalize,
    get_suggestions,
    get_tables,
    N1Problem,
    Severity,
)


class NPlusOneDetectionTestCase(unittest.TestCase):
    """Test the N+1 query analyzer."""

    def test_generalize_query(self):
        """Test query generalization using sql_metadata."""
        # Test numeric replacement
        query1 = "SELECT * FROM users WHERE id = 123"
        generalized1 = generalize(query1)
        self.assertIn("= N", generalized1)

        # Test quoted value replacement
        query2 = "SELECT * FROM posts WHERE title = 'Hello World'"
        generalized2 = generalize(query2)
        self.assertNotIn("Hello World", generalized2)

    def test_get_tables(self):
        """Test table extraction using sql_metadata."""
        sql = "SELECT u.name FROM users u JOIN posts p ON u.id = p.user_id WHERE p.id = 1"
        tables = get_tables(sql)

        self.assertIn("users", tables)
        self.assertIn("posts", tables)

    def test_detect_simple_n1_pattern(self):
        """Test detection of simple N+1 pattern."""
        queries = [
            {"sql": "SELECT * FROM posts WHERE user_id = 1"},
            {"sql": "SELECT * FROM posts WHERE user_id = 2"},
            {"sql": "SELECT * FROM posts WHERE user_id = 3"},
            {"sql": "SELECT * FROM posts WHERE user_id = 4"},
        ]

        problems = analyze_queries(queries)

        self.assertEqual(len(problems), 1)
        problem = problems[0]
        self.assertEqual(problem.count, 4)
        self.assertEqual(problem.base_table, "posts")
        self.assertIn("WHERE", problem.pattern)

    def test_detect_join_n1_pattern(self):
        """Test detection of N+1 pattern with JOINs."""
        queries = [
            {"sql": "SELECT u.name, p.title FROM users u JOIN posts p ON u.id = p.user_id WHERE u.id = 1"},
            {"sql": "SELECT u.name, p.title FROM users u JOIN posts p ON u.id = p.user_id WHERE u.id = 2"},
            {"sql": "SELECT u.name, p.title FROM users u JOIN posts p ON u.id = p.user_id WHERE u.id = 3"},
            {"sql": "SELECT u.name, p.title FROM users u JOIN posts p ON u.id = p.user_id WHERE u.id = 4"},
            {"sql": "SELECT u.name, p.title FROM users u JOIN posts p ON u.id = p.user_id WHERE u.id = 5"},
        ]

        problems = analyze_queries(queries)

        self.assertEqual(len(problems), 1)
        problem = problems[0]
        self.assertEqual(problem.count, 5)
        self.assertEqual(problem.severity, Severity.MEDIUM)  # 5 queries = medium severity

    def test_severity_calculation(self):
        """Test severity calculation based on query count."""
        # Low severity (< 5 queries)
        low_queries = [{"sql": f"SELECT * FROM users WHERE id = {i}"} for i in range(1, 4)]
        low_problems = analyze_queries(low_queries)
        if low_problems:
            self.assertEqual(low_problems[0].severity, Severity.LOW)

        # Medium severity (5-9 queries)
        medium_queries = [{"sql": f"SELECT * FROM users WHERE id = {i}"} for i in range(1, 8)]
        medium_problems = analyze_queries(medium_queries)
        if medium_problems:
            self.assertEqual(medium_problems[0].severity, Severity.MEDIUM)

        # High severity (10+ queries)
        high_queries = [{"sql": f"SELECT * FROM users WHERE id = {i}"} for i in range(1, 12)]
        high_problems = analyze_queries(high_queries)
        if high_problems:
            self.assertEqual(high_problems[0].severity, Severity.HIGH)

    def test_detect_n1_with_string_parameters(self):
        """Test detection of N+1 pattern with non-numeric (UUID/string) keys."""
        queries = [
            {"sql": f"SELECT * FROM orders WHERE user_uuid = '{value}'"}
            for value in ("a1b2c3d4", "b2c3d4e5", "c3d4e5f6", "d4e5f6a1", "e5f6a1b2")
        ]

        problems = analyze_queries(queries)

        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0].count, 5)
        self.assertEqual(problems[0].base_table, "orders")

    def test_ignore_identical_queries(self):
        """Test that identical queries (not N+1) are ignored."""
        queries = [
            {"sql": "SELECT COUNT(*) FROM users"},
            {"sql": "SELECT COUNT(*) FROM users"},
            {"sql": "SELECT COUNT(*) FROM users"},
        ]

        problems = analyze_queries(queries)

        # Should not detect this as N+1 since it's the same exact query
        self.assertEqual(len(problems), 0)

    def test_mixed_queries_detection(self):
        """Test detection with mixed query types."""
        queries = [
            # N+1 pattern: multiple user lookups
            {"sql": "SELECT * FROM users WHERE id = 1"},
            {"sql": "SELECT * FROM users WHERE id = 2"},
            {"sql": "SELECT * FROM users WHERE id = 3"},
            {"sql": "SELECT * FROM users WHERE id = 4"},
            # Different pattern: post lookups
            {"sql": "SELECT * FROM posts WHERE user_id = 1"},
            {"sql": "SELECT * FROM posts WHERE user_id = 2"},
            {"sql": "SELECT * FROM posts WHERE user_id = 3"},
            # Single query - should not be flagged
            {"sql": "SELECT COUNT(*) FROM comments"},
        ]

        problems = analyze_queries(queries)

        # Should detect 2 N+1 problems: users and posts
        self.assertEqual(len(problems), 2)

        # Check that problems are sorted by severity/count
        self.assertGreaterEqual(problems[0].count, problems[1].count)

    def test_get_suggestions(self):
        """Test getting suggestions for N+1 problems."""
        problem = N1Problem(
            pattern="SELECT * FROM posts WHERE user_id = N",
            count=5,
            base_table="posts",
            joined_tables=["users"],
        )

        suggestions = get_suggestions(problem)

        self.assertGreater(len(suggestions), 0)
        # Should include select_related suggestion for joined table
        select_related_found = any("select_related" in s.lower() for s in suggestions)
        self.assertTrue(select_related_found)

    def test_empty_queries_list(self):
        """Test handling of empty queries list."""
        problems = analyze_queries([])
        self.assertEqual(len(problems), 0)

    def test_queries_without_sql(self):
        """Test handling of queries without SQL."""
        queries = [
            {"time": "0.001"},
            {"sql": "", "time": "0.002"},
            {"sql": None, "time": "0.003"},
        ]

        problems = analyze_queries(queries)
        self.assertEqual(len(problems), 0)

    def test_real_django_style_queries(self):
        """Test with realistic Django-style queries."""
        queries = [
            # Typical N+1: getting user for each post
            {"sql": 'SELECT "auth_user"."id", "auth_user"."username" FROM "auth_user" WHERE "auth_user"."id" = 1'},
            {"sql": 'SELECT "auth_user"."id", "auth_user"."username" FROM "auth_user" WHERE "auth_user"."id" = 2'},
            {"sql": 'SELECT "auth_user"."id", "auth_user"."username" FROM "auth_user" WHERE "auth_user"."id" = 3'},
            {"sql": 'SELECT "auth_user"."id", "auth_user"."username" FROM "auth_user" WHERE "auth_user"."id" = 4'},
            # Another N+1: getting comments for each post
            {
                "sql": 'SELECT "blog_comment"."id", "blog_comment"."content" FROM "blog_comment" WHERE "blog_comment"."post_id" = 1'
            },
            {
                "sql": 'SELECT "blog_comment"."id", "blog_comment"."content" FROM "blog_comment" WHERE "blog_comment"."post_id" = 2'
            },
            {
                "sql": 'SELECT "blog_comment"."id", "blog_comment"."content" FROM "blog_comment" WHERE "blog_comment"."post_id" = 3'
            },
            {
                "sql": 'SELECT "blog_comment"."id", "blog_comment"."content" FROM "blog_comment" WHERE "blog_comment"."post_id" = 4'
            },
        ]

        problems = analyze_queries(queries)

        # Should detect both N+1 patterns
        self.assertEqual(len(problems), 2)

        # Check table extraction works with quoted table names
        table_names = [p.base_table for p in problems]
        self.assertIn("auth_user", table_names)
        self.assertIn("blog_comment", table_names)


class N1ProblemTestCase(unittest.TestCase):
    """Test the N1Problem dataclass."""

    def test_n1_problem_str(self):
        """Test string representation of N1Problem."""
        problem = N1Problem(
            pattern="SELECT * FROM USERS WHERE ID = %S",
            count=5,
            similar_queries=[],
            base_table="users",
            severity=Severity.MEDIUM,
        )

        str_repr = str(problem)
        self.assertIn("N+1 Problem", str_repr)
        self.assertIn("5 similar", str_repr)
        self.assertIn("users", str_repr)

    def test_n1_problem_without_table(self):
        """Test N1Problem without base table."""
        problem = N1Problem(pattern="SELECT * FROM UNKNOWN WHERE ID = %S", count=3, similar_queries=[])

        str_repr = str(problem)
        self.assertIn("unknown table", str_repr)


class FormatProblemsTextTestCase(unittest.TestCase):
    """format_problems_text must show suggestions for every listed problem, not just the first."""

    def _problem(self, table):
        return N1Problem(
            pattern=f"SELECT * FROM {table} WHERE id = %s",
            count=5,
            similar_queries=[],
            base_table=table,
            severity=Severity.MEDIUM,
        )

    def test_suggestions_shown_for_each_of_top_3_problems(self):
        problems = [self._problem("authors"), self._problem("comments"), self._problem("tags")]
        text = format_problems_text(problems)

        for problem in problems:
            self.assertIn(get_suggestions(problem)[0], text)

    def test_suggestions_omitted_beyond_top_3_problems(self):
        problems = [self._problem(t) for t in ("authors", "comments", "tags", "likes")]
        text = format_problems_text(problems)

        fourth_suggestions = get_suggestions(problems[3])
        self.assertTrue(fourth_suggestions)
        # The 4th problem's pattern/table still appear, but without a "Suggestions:" block for it.
        fourth_section = text.split("4. ")[1]
        self.assertNotIn("Suggestions:", fourth_section)


class FormatProblemBodyTestCase(unittest.TestCase):
    """format_problem_body is shared by the inline assertNumQueries warning and the management command."""

    def _problem(self, pattern_len=20, num_queries=5):
        return N1Problem(
            pattern="SELECT * FROM posts WHERE id = %s" + ("x" * pattern_len),
            count=num_queries,
            similar_queries=[{"sql": f"SELECT * FROM posts WHERE id = {i}"} for i in range(num_queries)],
            base_table="posts",
            severity=Severity.MEDIUM,
        )

    def test_not_detailed_truncates_pattern_to_100_chars(self):
        problem = self._problem(pattern_len=200)
        lines = format_problem_body(problem, index=1, detailed=False)

        pattern_line = next(line for line in lines if line.startswith("   Pattern:"))
        self.assertLessEqual(len(pattern_line), len("   Pattern: ") + 100 + len("..."))
        self.assertIn("...", pattern_line)

    def test_detailed_shows_full_pattern_untruncated(self):
        problem = self._problem(pattern_len=200)
        lines = format_problem_body(problem, index=1, detailed=True)

        pattern_line = next(line for line in lines if line.startswith("   Pattern:"))
        self.assertIn(problem.pattern, pattern_line)

    def test_not_detailed_shows_up_to_3_truncated_examples(self):
        problem = self._problem(num_queries=5)
        lines = format_problem_body(problem, index=1, detailed=False)

        self.assertIn("   Example queries:", lines)
        example_lines = [line for line in lines if line.strip().split(". ", 1)[0].isdigit()]
        self.assertEqual(len(example_lines), 3)
        self.assertTrue(any("... and 2 more" in line for line in lines))

    def test_detailed_shows_all_full_examples_uncapped(self):
        problem = self._problem(num_queries=8)
        lines = format_problem_body(problem, index=1, detailed=True)

        example_lines = [line for line in lines if line.strip().split(". ", 1)[0].isdigit()]
        self.assertEqual(len(example_lines), 8)
        self.assertFalse(any("... and" in line for line in lines))

    def test_test_case_line_omitted_when_unset(self):
        problem = self._problem()
        lines = format_problem_body(problem, index=1, detailed=False)

        self.assertFalse(any(line.startswith("   Test:") for line in lines))

    def test_test_case_line_shown_when_set(self):
        problem = self._problem()
        problem.test_case = "tests.PostsTestCase.test_list:0"
        lines = format_problem_body(problem, index=1, detailed=False)

        self.assertIn("   Test: tests.PostsTestCase.test_list:0", lines)


class SeverityParseTestCase(unittest.TestCase):
    """Severity.parse() accepts a name or a Severity member - int is deliberately not supported (YAGNI)."""

    def test_parses_name_case_insensitively(self):
        self.assertEqual(Severity.parse("medium"), Severity.MEDIUM)
        self.assertEqual(Severity.parse("HIGH"), Severity.HIGH)
        self.assertEqual(Severity.parse("Low"), Severity.LOW)

    def test_passes_through_severity_member(self):
        self.assertEqual(Severity.parse(Severity.HIGH), Severity.HIGH)

    def test_invalid_name_raises_value_error(self):
        with self.assertRaises(ValueError):
            Severity.parse("meduim")  # typo

    def test_int_raises_type_error(self):
        with self.assertRaises(TypeError):
            Severity.parse(2)

    def test_invalid_type_raises_type_error(self):
        with self.assertRaises(TypeError):
            Severity.parse(None)


class FilterBySeverityThresholdTestCase(unittest.TestCase):
    def setUp(self):
        self.problems = [
            N1Problem(pattern="p", count=3, severity=Severity.LOW),
            N1Problem(pattern="p", count=5, severity=Severity.MEDIUM),
            N1Problem(pattern="p", count=10, severity=Severity.HIGH),
        ]

    def test_threshold_as_name(self):
        self.assertEqual(len(filter_by_severity(self.problems, "high")), 1)

    def test_threshold_as_member(self):
        self.assertEqual(len(filter_by_severity(self.problems, Severity.MEDIUM)), 2)
