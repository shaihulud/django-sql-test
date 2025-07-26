import unittest

from django_sql_test.diff_utils import build_queries_diff_list, DiffLine, DiffType


class BuildQueriesDiffListTestCase(unittest.TestCase):

    def test_both_lists_empty(self):
        new_queries = []
        old_queries = []
        result = build_queries_diff_list(new_queries, old_queries)
        self.assertEqual(result, [])

    def test_old_queries_empty_new_has_queries(self):
        new_queries = [{"sql": "SELECT * FROM users"}]
        old_queries = []
        result = build_queries_diff_list(new_queries, old_queries)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].diff_type, DiffType.ADDED)
        self.assertEqual(result[0].original_query, "+ SELECT * FROM users")
        self.assertEqual(result[0].generalized_query, "+ SELECT * FROM users")

    def test_new_queries_empty_old_has_queries(self):
        new_queries = []
        old_queries = [{"sql": "SELECT * FROM users"}]
        result = build_queries_diff_list(new_queries, old_queries)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].diff_type, DiffType.REMOVED)
        self.assertEqual(result[0].original_query, "- SELECT * FROM users")
        self.assertEqual(result[0].generalized_query, "- SELECT * FROM users")

    def test_identical_queries(self):
        query = {"sql": "SELECT * FROM users WHERE id = 1"}
        new_queries = [query]
        old_queries = [query]
        result = build_queries_diff_list(new_queries, old_queries)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].diff_type, DiffType.UNCHANGED)
        self.assertEqual(result[0].original_query, "  SELECT * FROM users WHERE id = 1")
        self.assertEqual(result[0].generalized_query, "  SELECT * FROM users WHERE id = N")

    def test_completely_different_queries(self):
        new_queries = [{"sql": "SELECT * FROM products"}]
        old_queries = [{"sql": "SELECT * FROM users"}]
        result = build_queries_diff_list(new_queries, old_queries)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].diff_type, DiffType.REMOVED)
        self.assertEqual(result[0].original_query, "- SELECT * FROM users")
        self.assertEqual(result[0].generalized_query, "- SELECT * FROM users")
        self.assertEqual(result[1].diff_type, DiffType.ADDED)
        self.assertEqual(result[1].original_query, "+ SELECT * FROM products")
        self.assertEqual(result[1].generalized_query, "+ SELECT * FROM products")

    def test_queries_added_to_end(self):
        new_queries = [{"sql": "SELECT * FROM users"}, {"sql": "SELECT * FROM products"}]
        old_queries = [{"sql": "SELECT * FROM users"}]
        result = build_queries_diff_list(new_queries, old_queries)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].diff_type, DiffType.UNCHANGED)
        self.assertEqual(result[0].original_query, "  SELECT * FROM users")
        self.assertEqual(result[0].generalized_query, "  SELECT * FROM users")
        self.assertEqual(result[1].diff_type, DiffType.ADDED)
        self.assertEqual(result[1].original_query, "+ SELECT * FROM products")
        self.assertEqual(result[1].generalized_query, "+ SELECT * FROM products")

    def test_queries_removed_from_end(self):
        new_queries = [{"sql": "SELECT * FROM users"}]
        old_queries = [{"sql": "SELECT * FROM users"}, {"sql": "SELECT * FROM products"}]
        result = build_queries_diff_list(new_queries, old_queries)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].diff_type, DiffType.UNCHANGED)
        self.assertEqual(result[0].original_query, "  SELECT * FROM users")
        self.assertEqual(result[0].generalized_query, "  SELECT * FROM users")
        self.assertEqual(result[1].diff_type, DiffType.REMOVED)
        self.assertEqual(result[1].original_query, "- SELECT * FROM products")
        self.assertEqual(result[1].generalized_query, "- SELECT * FROM products")

    def test_queries_reordered(self):
        new_queries = [{"sql": "SELECT * FROM products"}, {"sql": "SELECT * FROM users"}]
        old_queries = [{"sql": "SELECT * FROM users"}, {"sql": "SELECT * FROM products"}]
        result = build_queries_diff_list(new_queries, old_queries)

        # The ndiff algorithm optimizes and finds common sequences
        # Result should be: + products, unchanged users, - products
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].diff_type, DiffType.ADDED)
        self.assertEqual(result[0].original_query, "+ SELECT * FROM products")
        self.assertEqual(result[0].generalized_query, "+ SELECT * FROM products")
        self.assertEqual(result[1].diff_type, DiffType.UNCHANGED)
        self.assertEqual(result[1].original_query, "  SELECT * FROM users")
        self.assertEqual(result[1].generalized_query, "  SELECT * FROM users")
        self.assertEqual(result[2].diff_type, DiffType.REMOVED)
        self.assertEqual(result[2].original_query, "- SELECT * FROM products")
        self.assertEqual(result[2].generalized_query, "- SELECT * FROM products")

    def test_mixed_changes_additions_removals_unchanged(self):
        new_queries = [
            {"sql": "SELECT * FROM users"},  # unchanged
            {"sql": "SELECT * FROM orders"},  # added
            {"sql": "SELECT * FROM categories"},  # added
        ]
        old_queries = [
            {"sql": "SELECT * FROM users"},  # unchanged
            {"sql": "SELECT * FROM products"},  # removed
        ]
        result = build_queries_diff_list(new_queries, old_queries)

        self.assertEqual(len(result), 4)
        self.assertEqual(result[0].diff_type, DiffType.UNCHANGED)
        self.assertEqual(result[0].original_query, "  SELECT * FROM users")
        self.assertEqual(result[0].generalized_query, "  SELECT * FROM users")
        self.assertEqual(result[1].diff_type, DiffType.REMOVED)
        self.assertEqual(result[1].original_query, "- SELECT * FROM products")
        self.assertEqual(result[1].generalized_query, "- SELECT * FROM products")
        self.assertEqual(result[2].diff_type, DiffType.ADDED)
        self.assertEqual(result[2].original_query, "+ SELECT * FROM orders")
        self.assertEqual(result[2].generalized_query, "+ SELECT * FROM orders")
        self.assertEqual(result[3].diff_type, DiffType.ADDED)
        self.assertEqual(result[3].original_query, "+ SELECT * FROM categories")
        self.assertEqual(result[3].generalized_query, "+ SELECT * FROM categories")

    def test_single_query_scenarios(self):
        new_queries = [{"sql": "SELECT id FROM users"}]
        old_queries = [{"sql": "SELECT name FROM users"}]
        result = build_queries_diff_list(new_queries, old_queries)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].diff_type, DiffType.REMOVED)
        self.assertEqual(result[0].original_query, "- SELECT name FROM users")
        self.assertEqual(result[0].generalized_query, "- SELECT name FROM users")
        self.assertEqual(result[1].diff_type, DiffType.ADDED)
        self.assertEqual(result[1].original_query, "+ SELECT id FROM users")
        self.assertEqual(result[1].generalized_query, "+ SELECT id FROM users")

    def test_parameterized_queries_same_generalized_form(self):
        new_queries = [{"sql": "SELECT * FROM users WHERE id = 1"}]
        old_queries = [{"sql": "SELECT * FROM users WHERE id = 2"}]
        result = build_queries_diff_list(new_queries, old_queries)

        # These should be treated as unchanged since they generalize to the same form
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].diff_type, DiffType.UNCHANGED)
        self.assertEqual(result[0].original_query, "  SELECT * FROM users WHERE id = 1")
        self.assertEqual(result[0].generalized_query, "  SELECT * FROM users WHERE id = N")

    def test_multiple_identical_queries(self):
        new_queries = [{"sql": "SELECT * FROM users"}, {"sql": "SELECT * FROM users"}]
        old_queries = [{"sql": "SELECT * FROM users"}, {"sql": "SELECT * FROM users"}]
        result = build_queries_diff_list(new_queries, old_queries)

        self.assertEqual(len(result), 2)
        for diff_line in result:
            self.assertEqual(diff_line.diff_type, DiffType.UNCHANGED)
            self.assertEqual(diff_line.original_query, "  SELECT * FROM users")
            self.assertEqual(diff_line.generalized_query, "  SELECT * FROM users")

    def test_complex_mixed_scenario(self):
        new_queries = [
            {"sql": "SELECT * FROM users WHERE id = 1"},  # unchanged (generalized)
            {"sql": "SELECT * FROM products"},  # added
            {"sql": "SELECT * FROM orders"},  # unchanged
            {"sql": "SELECT * FROM reviews"},  # added
        ]
        old_queries = [
            {"sql": "SELECT * FROM users WHERE id = 2"},  # unchanged (generalized)
            {"sql": "SELECT * FROM categories"},  # removed
            {"sql": "SELECT * FROM orders"},  # unchanged
        ]
        result = build_queries_diff_list(new_queries, old_queries)

        # Verify we have the expected number of diff lines
        self.assertEqual(len(result), 5)

        # Check that we have the expected diff types
        diff_types = [line.diff_type for line in result]
        self.assertEqual(DiffType.UNCHANGED, diff_types[0])
        self.assertEqual(DiffType.REMOVED, diff_types[1])
        self.assertEqual(DiffType.ADDED, diff_types[2])
        self.assertEqual(DiffType.UNCHANGED, diff_types[3])
        self.assertEqual(DiffType.ADDED, diff_types[4])

    def test_returns_diffline_objects(self):
        new_queries = [{"sql": "SELECT * FROM users"}]
        old_queries = [{"sql": "SELECT * FROM products"}]
        result = build_queries_diff_list(new_queries, old_queries)

        for item in result:
            self.assertIsInstance(item, DiffLine)
            self.assertIsInstance(item.diff_type, DiffType)
            self.assertIsInstance(item.original_query, str)
            self.assertIsInstance(item.generalized_query, str)

    def test_large_number_of_queries(self):
        # Test with a larger set to ensure index tracking works correctly
        # Use completely different table names to ensure they don't generalize to the same thing
        new_queries = [{"sql": f"SELECT * FROM users_{i}"} for i in range(5)]
        old_queries = [{"sql": f"SELECT * FROM products_{i}"} for i in range(5)]
        result = build_queries_diff_list(new_queries, old_queries)

        # Should have differences since table names are completely different
        self.assertGreater(len(result), 0)

        # Verify we have the expected diff types
        diff_types = {line.diff_type for line in result}
        self.assertIn(DiffType.ADDED, diff_types)  # users tables
        self.assertIn(DiffType.REMOVED, diff_types)  # products tables

    def test_query_with_special_characters(self):
        # Use different table names to ensure they are treated as different
        new_queries = [{"sql": "SELECT * FROM orders WHERE name = 'O''Reilly'"}]
        old_queries = [{"sql": "SELECT * FROM users WHERE name = 'Smith & Co.'"}]
        result = build_queries_diff_list(new_queries, old_queries)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].diff_type, DiffType.REMOVED)
        self.assertEqual(result[0].original_query, "- SELECT * FROM users WHERE name = 'Smith & Co.'")
        self.assertEqual(result[0].generalized_query, "- SELECT * FROM users WHERE name = X")

        self.assertEqual(result[1].diff_type, DiffType.ADDED)
        self.assertEqual(result[1].original_query, "+ SELECT * FROM orders WHERE name = 'O''Reilly'")
        self.assertEqual(result[1].generalized_query, "+ SELECT * FROM orders WHERE name = XX")

    def test_very_long_queries(self):
        # Test with very long SQL queries to ensure no truncation issues
        long_select = "SELECT " + ", ".join([f"column_{i}" for i in range(50)])
        new_queries = [{"sql": f"{long_select} FROM large_table"}]
        old_queries = [{"sql": f"{long_select} FROM different_table"}]
        result = build_queries_diff_list(new_queries, old_queries)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].diff_type, DiffType.REMOVED)
        self.assertIn("different_table", result[0].original_query)
        self.assertIn("different_table", result[0].generalized_query)
        self.assertEqual(result[1].diff_type, DiffType.ADDED)
        # Ensure the full query is preserved in original_query
        self.assertIn("column_49", result[1].original_query)
        self.assertIn("large_table", result[1].original_query)
        # The generalized query will have column names replaced with column_N
        self.assertIn("column_N", result[1].generalized_query)
        self.assertIn("large_table", result[1].generalized_query)
