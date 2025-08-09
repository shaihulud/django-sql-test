import json
import os
import tempfile
from unittest import TestCase
from unittest.mock import Mock, patch

from django_sql_test.engine import FileEngine
from django_sql_test.utils import NumNewQueriesMixin


class CallIndexTrackingTestCase(TestCase):
    """Test call index tracking without database dependencies."""

    def test_call_index_increment(self):
        """Test that call indices increment correctly."""

        class MockTestCase(NumNewQueriesMixin):
            def __init__(self):
                self._testMethodName = "test_method"

        test_instance = MockTestCase()

        # First call should be index 0
        index_1 = test_instance._get_call_index()
        self.assertEqual(index_1, 0)

        # Second call should be index 1
        index_2 = test_instance._get_call_index()
        self.assertEqual(index_2, 1)

        # Third call should be index 2
        index_3 = test_instance._get_call_index()
        self.assertEqual(index_3, 2)

    def test_call_index_resets_for_new_method(self):
        """Test that call indices reset for new test methods."""

        class MockTestCase(NumNewQueriesMixin):
            def __init__(self):
                self._testMethodName = "test_method_1"

        test_instance = MockTestCase()

        # First method, first call
        index_1 = test_instance._get_call_index()
        self.assertEqual(index_1, 0)

        # First method, second call
        index_2 = test_instance._get_call_index()
        self.assertEqual(index_2, 1)

        # Simulate moving to new test method
        test_instance._testMethodName = "test_method_2"

        # New method should reset to 0
        index_3 = test_instance._get_call_index()
        self.assertEqual(index_3, 0)

        # And continue incrementing
        index_4 = test_instance._get_call_index()
        self.assertEqual(index_4, 1)


class MultipleAssertNumQueriesTestCase(NumNewQueriesMixin, TestCase):
    """Test that multiple assertNumQueries calls within the same test work correctly."""

    def setUp(self):
        """Set up test method name for proper call index tracking."""
        self._testMethodName = self._testMethodName or "unknown_test"

    def test_multiple_calls_same_method(self):
        """Test that multiple calls within same test method get incremental call indices."""
        # Test the call index tracking directly
        call_index_1 = self._get_call_index()
        call_index_2 = self._get_call_index()
        call_index_3 = self._get_call_index()

        self.assertEqual(call_index_1, 0)
        self.assertEqual(call_index_2, 1)
        self.assertEqual(call_index_3, 2)

    def test_second_method_resets_counter(self):
        """Test that different test method resets the call index to 0."""
        call_index = self._get_call_index()
        self.assertEqual(call_index, 0)

        # Call again in same method
        call_index_2 = self._get_call_index()
        self.assertEqual(call_index_2, 1)

    @patch("django_sql_test.utils.connections")
    @patch("django_sql_test.utils._AssertNumNewQueriesContext")
    def test_context_manager_usage(self, mock_context_class, mock_connections):
        """Test that context manager correctly passes call indices."""
        # Mock the connection
        mock_connection = Mock()
        mock_connections.__getitem__.return_value = mock_connection

        # Mock the context manager
        mock_context = Mock()
        mock_context.call_index = None  # Will be set by our code
        mock_context_class.return_value = mock_context

        # First assertNumQueries call should get call_index=0
        context_1 = self.assertNumQueries(0)
        self.assertEqual(mock_context_class.call_args[0][3], 0)  # call_index argument

        # Second assertNumQueries call should get call_index=1
        context_2 = self.assertNumQueries(0)
        self.assertEqual(mock_context_class.call_args[0][3], 1)  # call_index argument

        # Third assertNumQueries call should get call_index=2
        context_3 = self.assertNumQueries(0)
        self.assertEqual(mock_context_class.call_args[0][3], 2)  # call_index argument

    @patch("django_sql_test.utils.connections")
    @patch("django_sql_test.utils._AssertNumNewQueriesContext")
    def test_functional_usage(self, mock_context_class, mock_connections):
        """Test using assertNumQueries with function calls."""
        # Mock the connection
        mock_connection = Mock()
        mock_connections.__getitem__.return_value = mock_connection

        # Mock the context manager
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_context)
        mock_context.__exit__ = Mock(return_value=None)
        mock_context_class.return_value = mock_context

        def mock_function_1():
            pass

        def mock_function_2():
            pass

        # These should work without interfering with each other
        self.assertNumQueries(0, mock_function_1)
        self.assertNumQueries(0, mock_function_2)

        # Verify both calls were made with incremental call indices
        calls = mock_context_class.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0][3], 0)  # First call: call_index=0
        self.assertEqual(calls[1][0][3], 1)  # Second call: call_index=1

    @patch("django_sql_test.utils.get_engine")
    @patch("django_sql_test.utils.connections")
    @patch("django_sql_test.utils._AssertNumNewQueriesContext")
    def test_engine_receives_correct_call_indices(self, mock_context_class, mock_connections, mock_get_engine):
        """Test that the engine receives the correct call indices."""
        # Mock the connection
        mock_connection = Mock()
        mock_connections.__getitem__.return_value = mock_connection

        # Mock the engine
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine

        # Mock the context manager to simulate successful execution
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_context)
        mock_context.__exit__ = Mock(return_value=None)
        mock_context.__len__ = Mock(return_value=0)  # No queries executed
        mock_context.captured_queries = []
        mock_context_class.return_value = mock_context

        # First call
        with self.assertNumQueries(0):
            pass

        # Second call
        with self.assertNumQueries(0):
            pass

        # Verify context was created with correct call indices
        calls = mock_context_class.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0][3], 0)  # First call: call_index=0
        self.assertEqual(calls[1][0][3], 1)  # Second call: call_index=1


class FileEngineCallIndexTestCase(TestCase):
    """Test that FileEngine correctly handles call indices."""

    def test_engine_stores_by_call_index(self):
        """Test that FileEngine stores and retrieves data by call index."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_file:
            temp_filename = temp_file.name

        try:
            # Create engine with temporary file
            engine = FileEngine({"filename": temp_filename})

            # Mock test case
            class MockTestCase:
                def __str__(self):
                    return "test_method (tests.TestClass)"

            test_case = MockTestCase()

            # Store different queries for different call indices
            queries_0 = [{"sql": "SELECT 1"}]
            queries_1 = [{"sql": "SELECT 2"}]
            queries_2 = [{"sql": "SELECT 3"}]

            engine.set_data_for_testcase(test_case, queries_0, call_index=0)
            engine.set_data_for_testcase(test_case, queries_1, call_index=1)
            engine.set_data_for_testcase(test_case, queries_2, call_index=2)

            # Retrieve and verify
            self.assertEqual(engine.get_data_for_testcase(test_case, call_index=0), queries_0)
            self.assertEqual(engine.get_data_for_testcase(test_case, call_index=1), queries_1)
            self.assertEqual(engine.get_data_for_testcase(test_case, call_index=2), queries_2)

        finally:
            # Clean up
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    def test_engine_file_format(self):
        """Test that the file format includes call indices in keys."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_file:
            temp_filename = temp_file.name

        try:
            engine = FileEngine({"filename": temp_filename})

            class MockTestCase:
                def __str__(self):
                    return "test_method (tests.TestClass)"

            test_case = MockTestCase()
            queries = [{"sql": "SELECT 1"}]

            engine.set_data_for_testcase(test_case, queries, call_index=2)

            # Read the file directly and check the key format
            with open(temp_filename, "r") as f:
                data = json.load(f)

            expected_key = "test_method (tests.TestClass):2"
            self.assertIn(expected_key, data)
            self.assertEqual(data[expected_key], queries)

        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    def test_engine_returns_empty_for_missing_call_index(self):
        """Test that engine returns empty list for non-existent call index."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_file:
            temp_filename = temp_file.name

        try:
            engine = FileEngine({"filename": temp_filename})

            class MockTestCase:
                def __str__(self):
                    return "test_method (tests.TestClass)"

            test_case = MockTestCase()

            # Don't store anything, just try to retrieve
            result = engine.get_data_for_testcase(test_case, call_index=5)
            self.assertEqual(result, [])

        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
