import abc
import json
import os
from unittest.util import strclass

from django.test.testcases import TransactionTestCase
from django.utils.module_loading import import_string

from .app_settings import ENGINE, ENGINE_SETTINGS


def get_testcase_name(testcase: TransactionTestCase, call_index: int) -> str:
    class_name = strclass(testcase.__class__)
    method_name = getattr(testcase, "_testMethodName", "unknown_test")
    testcase_name = f"{class_name}.{method_name}:{call_index}"
    return testcase_name


class Engine(abc.ABC):
    def __init__(self, settings: dict):
        self.settings = settings or {}

    @abc.abstractmethod
    def get_data_for_testcase(self, testcase: TransactionTestCase, call_index: int = 0) -> list[dict]: ...

    @abc.abstractmethod
    def set_data_for_testcase(
        self, testcase: TransactionTestCase, captured_queries: list[dict], call_index: int = 0
    ) -> None: ...


class FileEngine(Engine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.filename = self.settings.get("filename") or ".django_sql_test_queries"

        if not os.path.exists(self.filename):
            with open(self.filename, "w") as f:
                f.write("{}")
            self.data = {}
        else:
            with open(self.filename, "r") as f:
                data = f.read()
            try:
                self.data = json.loads(data) or {}
            except Exception:
                self.data = {}

    def get_data_for_testcase(self, testcase: TransactionTestCase, call_index: int = 0) -> list[dict]:
        testcase_name = get_testcase_name(testcase, call_index)
        data = self.data.get(testcase_name)
        if data is None and call_index == 0:
            # Snapshots written before 1.0 are keyed by str(testcase) and have no call_index
            data = self.data.get(str(testcase))
        return data or []

    def set_data_for_testcase(
        self, testcase: TransactionTestCase, captured_queries: list[dict], call_index: int = 0
    ) -> None:
        testcase_name = get_testcase_name(testcase, call_index)
        self.data.pop(str(testcase), None)  # migrate away the pre-1.0 entry, if any
        self.data[testcase_name] = captured_queries

        with open(self.filename, "w") as f:
            f.write(json.dumps(self.data))


def get_engine() -> Engine:
    settings = ENGINE_SETTINGS or dict()

    if ENGINE == "file":
        return FileEngine(settings)

    engine_cls = import_string(ENGINE)
    return engine_cls(settings)
