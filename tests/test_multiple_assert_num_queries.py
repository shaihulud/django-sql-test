from unittest import TestCase
from unittest.mock import Mock, patch

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
