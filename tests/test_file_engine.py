import json
import os
import tempfile
import warnings
from unittest import TestCase
from unittest.mock import patch

from django_sql_test import engine as engine_module
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


class _MockTestCase:
    _testMethodName = "test_method"

    @property
    def __class__(self):
        class MockClass:
            __module__ = "tests"
            __qualname__ = "TestClass"

        return MockClass


class LegacyKeyMigrationTestCase(TestCase):
    """set_data_for_testcase must only migrate the pre-1.0 str(testcase) key on call_index == 0."""

    def setUp(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_file:
            self.temp_filename = temp_file.name
        self.addCleanup(os.unlink, self.temp_filename)
        self.test_case = _MockTestCase()

    def _engine_with_legacy_data(self, legacy_queries):
        with open(self.temp_filename, "w") as f:
            json.dump({str(self.test_case): legacy_queries}, f)
        return FileEngine({"filename": self.temp_filename})

    def test_call_index_above_0_does_not_pop_legacy_key(self):
        engine = self._engine_with_legacy_data([{"sql": "SELECT 1"}])
        engine.set_data_for_testcase(self.test_case, [{"sql": "SELECT 2"}], call_index=1)

        # call_index=0 never ran this session (e.g. its own assertion failed), so the legacy
        # baseline must still be there for it to read/migrate on a later successful run.
        self.assertIn(str(self.test_case), engine.data)
        self.assertEqual(engine.get_data_for_testcase(self.test_case, call_index=0), [{"sql": "SELECT 1"}])


class GetEngineCachingTestCase(TestCase):
    """get_engine() must not re-read/re-parse the whole snapshot file on every call."""

    def setUp(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_file:
            self.temp_filename = temp_file.name
        os.unlink(self.temp_filename)  # start with no file, like a fresh project
        self.addCleanup(lambda: os.path.exists(self.temp_filename) and os.unlink(self.temp_filename))

        # get_engine()'s cache is a module-level global; reset it so tests don't leak state into each other.
        engine_module._engine_instance = None
        self.addCleanup(setattr, engine_module, "_engine_instance", None)

        self._patches = [
            patch.object(engine_module, "ENGINE", "file"),
            patch.object(engine_module, "ENGINE_SETTINGS", {"filename": self.temp_filename}),
        ]
        for p in self._patches:
            p.start()
            self.addCleanup(p.stop)

    def test_returns_the_same_instance_across_calls(self):
        self.assertIs(engine_module.get_engine(), engine_module.get_engine())

    def test_does_not_pick_up_external_writes_after_first_call(self):
        engine = engine_module.get_engine()

        with open(self.temp_filename, "w") as f:
            json.dump({"external.write:0": [{"sql": "SELECT 1"}]}, f)

        # Same cached instance, so the external write made after the first get_engine() call is invisible.
        self.assertIs(engine_module.get_engine(), engine)
        self.assertNotIn("external.write:0", engine.data)

    def test_set_data_does_not_clobber_external_writes_made_since_caching(self):
        # Simulates another process (e.g. a Django --parallel worker) sharing this file and
        # writing to it after this engine was cached.
        engine = engine_module.get_engine()

        with open(self.temp_filename, "w") as f:
            json.dump({"external.write:0": [{"sql": "SELECT 1"}]}, f)

        test_case = _MockTestCase()
        engine.set_data_for_testcase(test_case, [{"sql": "SELECT 2"}], call_index=0)

        with open(self.temp_filename) as f:
            data = json.load(f)
        self.assertIn("external.write:0", data)  # not clobbered by this engine's stale in-memory copy
        self.assertIn("tests.TestClass.test_method:0", data)

    def test_writes_through_cached_instance_still_persist_to_disk(self):
        test_case = _MockTestCase()
        engine_module.get_engine().set_data_for_testcase(test_case, [{"sql": "SELECT 1"}], call_index=0)
        engine_module.get_engine().set_data_for_testcase(test_case, [{"sql": "SELECT 2"}], call_index=1)

        engine = engine_module.get_engine()
        self.assertEqual(engine.get_data_for_testcase(test_case, call_index=0), [{"sql": "SELECT 1"}])
        self.assertEqual(engine.get_data_for_testcase(test_case, call_index=1), [{"sql": "SELECT 2"}])
        with open(self.temp_filename) as f:
            self.assertEqual(json.load(f), engine.data)
