import unittest

from django_sql_test.diff_utils import ColorScheme, DiffType


GREEN = "\033[1;32m"
RED = "\033[1;31m"
RESET = "\033[0m"


class ColorSchemeDefaultsTestCase(unittest.TestCase):
    def test_default_colors_added_green_removed_red(self):
        color_scheme = ColorScheme(added=None, removed=None, unchanged=None)

        self.assertEqual(color_scheme.get_color(DiffType.ADDED), GREEN)
        self.assertEqual(color_scheme.get_color(DiffType.REMOVED), RED)
        self.assertEqual(color_scheme.get_color(DiffType.UNCHANGED), RESET)

    def test_color_scheme_used_by_assertions_has_default_colors(self):
        # The module-level instance wired into every assertNumQueries diff,
        # built from unset SQL_TEST_DIFF_* settings
        from django_sql_test.utils import color_scheme

        self.assertEqual(color_scheme.get_color(DiffType.ADDED), GREEN)
        self.assertEqual(color_scheme.get_color(DiffType.REMOVED), RED)
