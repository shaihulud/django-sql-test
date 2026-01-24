import unittest

from django_sql_test.n_plus_one import (
    analyze_queries,
    analyze_queries_for_n1,
    generalize,
    get_suggestions,
    get_tables,
    N1Analyzer,
    N1Problem,
)


class N1AnalyzerTestCase(unittest.TestCase):
    """Test the N+1 query analyzer."""

    def setUp(self):
        self.analyzer = N1Analyzer()

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

    def test_group_similar_queries(self):
        """Test grouping of similar queries."""
        queries = [
            {"sql": "SELECT * FROM users WHERE id = 1"},
            {"sql": "SELECT * FROM users WHERE id = 2"},
            {"sql": "SELECT * FROM posts WHERE id = 1"},
            {"sql": "SELECT * FROM users WHERE id = 3"},
        ]

        groups = self.analyzer.group_similar_queries(queries)

        # Should have 2 groups: users queries and posts queries
        self.assertEqual(len(groups), 2)

        # Find the users group
        users_group = None
        for pattern, group_queries in groups.items():
            if "users" in pattern:
                users_group = group_queries
                break

        self.assertIsNotNone(users_group)
        self.assertEqual(len(users_group), 3)  # 3 users queries

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
        self.assertEqual(problem.severity, "medium")  # 5 queries = medium severity

    def test_severity_calculation(self):
        """Test severity calculation based on query count."""
        # Low severity (< 5 queries)
        low_queries = [{"sql": f"SELECT * FROM users WHERE id = {i}"} for i in range(1, 4)]
        low_problems = analyze_queries(low_queries)
        if low_problems:
            self.assertEqual(low_problems[0].severity, "low")

        # Medium severity (5-9 queries)
        medium_queries = [{"sql": f"SELECT * FROM users WHERE id = {i}"} for i in range(1, 8)]
        medium_problems = analyze_queries(medium_queries)
        if medium_problems:
            self.assertEqual(medium_problems[0].severity, "medium")

        # High severity (10+ queries)
        high_queries = [{"sql": f"SELECT * FROM users WHERE id = {i}"} for i in range(1, 12)]
        high_problems = analyze_queries(high_queries)
        if high_problems:
            self.assertEqual(high_problems[0].severity, "high")

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

    def test_convenience_function(self):
        """Test the convenience function."""
        queries = [
            {"sql": "SELECT * FROM users WHERE id = 1"},
            {"sql": "SELECT * FROM users WHERE id = 2"},
            {"sql": "SELECT * FROM users WHERE id = 3"},
        ]

        problems = analyze_queries_for_n1(queries)

        self.assertIsInstance(problems, list)
        if problems:
            self.assertIsInstance(problems[0], N1Problem)

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
            severity="medium",
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
