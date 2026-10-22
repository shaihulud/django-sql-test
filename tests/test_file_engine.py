import os
import tempfile
import warnings
from unittest import TestCase

from django_sql_test.engine import FileEngine


class FileEngineCorruptionTestCase(TestCase):
    def setUp(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_file:
            self.temp_filename = temp_file.name
        self.addCleanup(os.unlink, self.temp_filename)

    def test_corrupt_json_warns_and_falls_back_to_empty(self):
        with open(self.temp_filename, "w") as f:
            f.write("{not valid json!!!")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            engine = FileEngine({"filename": self.temp_filename})

        self.assertEqual(engine.data, {})
        self.assertEqual(len(caught), 1)
        self.assertIn(self.temp_filename, str(caught[0].message))

    def test_pristine_empty_file_does_not_warn(self):
        # tempfile.NamedTemporaryFile already leaves the file empty; this is "no data yet", not corruption.
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            engine = FileEngine({"filename": self.temp_filename})

        self.assertEqual(engine.data, {})
        self.assertEqual(len(caught), 0)
