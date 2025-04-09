import abc
import json
import os

from .app_settings import ENGINE, ENGINE_SETTINGS


class Engine(abc.ABC):
    @abc.abstractmethod
    def get_data_for_testcase(self, testcase): ...

    @abc.abstractmethod
    def set_data_for_testcase(self, testcase, captured_queries): ...


class FileEngine(Engine):
    def __init__(self, filename: str):
        self.filename = filename

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

    def get_data_for_testcase(self, testcase):
        return self.data.get(str(testcase)) or []

    def set_data_for_testcase(self, testcase, captured_queries):
        testcase_name = str(testcase)
        self.data[testcase_name] = captured_queries

        with open(self.filename, "w") as f:
            f.write(json.dumps(self.data))


def get_engine():
    if ENGINE == "file":
        settings = ENGINE_SETTINGS or dict()
        filename = settings.get("filename") or ".django_sql_test_queries"
        return FileEngine(filename)
    else:
        raise Exception("Unknown engine type. Check SQL_TEST_ENGINE value. Possible values: file")
