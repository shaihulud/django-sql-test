import abc
import json
import os

from django.test.testcases import TransactionTestCase
from django.utils.module_loading import import_string

from .app_settings import ENGINE, ENGINE_SETTINGS


class Engine(abc.ABC):
    def __init__(self, settings: dict):
        self.settings = settings or {}

    @abc.abstractmethod
    def get_data_for_testcase(self, testcase: TransactionTestCase) -> list[dict]: ...

    @abc.abstractmethod
    def set_data_for_testcase(self, testcase: TransactionTestCase, captured_queries: list[dict]) -> None: ...


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

    def get_data_for_testcase(self, testcase: TransactionTestCase) -> list[dict]:
        testcase_name = str(testcase)
        return self.data.get(testcase_name) or []

    def set_data_for_testcase(self, testcase: TransactionTestCase, captured_queries: list[dict]) -> None:
        testcase_name = str(testcase)
        self.data[testcase_name] = captured_queries

        with open(self.filename, "w") as f:
            f.write(json.dumps(self.data))


def get_engine() -> Engine:
    settings = ENGINE_SETTINGS or dict()

    if ENGINE == "file":
        return FileEngine(settings)

    engine_cls = import_string(ENGINE)
    return engine_cls(settings)
