# django-sql-test

Prevent SQL regressions, detect N+1 queries, and visualize query diffs in your Django tests.
A test mixin that captures, snapshots, and diffs all executed SQL queries in your test output.

<a href="https://pypi.org/project/django-sql-test/" target="_blank">
    <img src="https://img.shields.io/pypi/v/django-sql-test?color=%2334D058&label=pypi%20package" alt="Package version">
</a>
<a href="https://pypi.org/project/django-sql-test/" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/django-sql-test.svg?color=%2334D058" alt="Supported Python versions">
</a>
<a href="https://github.com/shaihulud/django-sql-test/blob/main/LICENSE" target="_blank">
    <img src="https://img.shields.io/pypi/l/django-sql-test.svg?color=%2334D058" alt="License">
</a>

```diff
$ poetry run python manage.py test path.to.test.FooTest.test_bar
======================================================================
FAIL: test_bar (path.to.test.FooTest.test_bar)
 ...
AssertionError: 5 != 2 : 5 queries executed, 2 expected
Queries diff:
- SELECT polls_choice.id FROM polls_choice
+ SELECT polls_choice.id FROM polls_choice WHERE polls_choice.votes >= N
+ SELECT polls_question.id FROM polls_question WHERE polls_question.id = N LIMIT N
+ SELECT polls_question.id FROM polls_question WHERE polls_question.id = N LIMIT N
+ SELECT polls_question.id FROM polls_question WHERE polls_question.id = N LIMIT N
  SELECT COUNT(*) AS __count FROM polls_question
```

## Table of Contents

* [Requirements](#requirements)
* [Installation](#installation)
* [Quickstart](#quickstart)
* [Configuration](#configuration)
* [N+1 Query Detection](#n1-query-detection)
* [API Reference](#api-reference)
* [Contributing](#contributing)
* [License](#license)
* [Changelog](#changelog)

## Requirements

- Django >= 4.0  
- Python >= 3.9

## Installation

```shell
pip install django-sql-test
```

## Quickstart

In your test.py just import NumNewQueriesMixin and add it as a parent:

```python
from django.test import TestCase
from django_sql_test import NumNewQueriesMixin

class FooTest(NumNewQueriesMixin, TestCase):
    def test_bar(self):
        with self.assertNumNewQueries(2):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

```

What you got before adding NumNewQueriesMixin:

```shell
$ poetry run python manage.py test path.to.test.FooTest.test_bar
======================================================================
FAIL: test_bar (path.to.test.FooTest.test_bar)
  ...
AssertionError: 5 != 2 : 5 queries executed, 2 expected
Captured queries were:
1. SELECT "polls_choice"."id" FROM "polls_choice" WHERE "polls_choice"."votes" >= 0
2. SELECT "polls_question"."id" FROM "polls_question" WHERE "polls_question"."id" = 1 LIMIT 21
3. SELECT "polls_question"."id" FROM "polls_question" WHERE "polls_question"."id" = 1 LIMIT 21
4. SELECT "polls_question"."id" FROM "polls_question" WHERE "polls_question"."id" = 1 LIMIT 21
5. SELECT COUNT(*) AS "__count" FROM "polls_question"
```

What you get after adding NumNewQueriesMixin:
```diff
$ poetry run python manage.py test path.to.test.FooTest.test_bar
======================================================================
FAIL: test_bar (path.to.test.FooTest.test_bar)
 ...
AssertionError: 5 != 2 : 5 queries executed, 2 expected
Queries diff:
- SELECT polls_choice.id FROM polls_choice
+ SELECT polls_choice.id FROM polls_choice WHERE polls_choice.votes >= N
+ SELECT polls_question.id FROM polls_question WHERE polls_question.id = N LIMIT N
+ SELECT polls_question.id FROM polls_question WHERE polls_question.id = N LIMIT N
+ SELECT polls_question.id FROM polls_question WHERE polls_question.id = N LIMIT N
  SELECT COUNT(*) AS __count FROM polls_question
```

## Configuration

Configure via your Django settings:

| Setting                         | Default        | Description                                                                                                                                                                                                                                                                                                                                                                                                     |
|---------------------------------|----------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `SQL_TEST_GENERALIZED_DIFF`     | `True`         | Hides SQL query parameters by replacing them with placeholders.                                                                                                                                                                                                                                                                                                                                                 |
| `SQL_TEST_DIFF_ONLY`            | `False`        | If set to True, shows only SQL queries that were added or removed; otherwise, shows all queries.                                                                                                                                                                                                                                                                                                                |
| `SQL_TEST_DIFF_NEW_COLOR`       | `"\033[1;32m"` | Color code for newly added SQL queries (green).                                                                                                                                                                                                                                                                                                                                                                 |
| `SQL_TEST_DIFF_OLD_COLOR`       | `"\033[1;31m"` | Color code for removed SQL queries (red).                                                                                                                                                                                                                                                                                                                                                                       |
| `SQL_TEST_DIFF_DEFAULT_COLOR`   | `"\033[0m"`    | Base console color code for unchanged SQL queries.                                                                                                                                                                                                                                                                                                                                                              |
| `SQL_TEST_SHOW_UPDATED_QUERIES` | `False`        | When set to True, SQL query diffs will be displayed even if the number of executed queries matches the expected count. The test will not fail; the diff is printed once and then overwritten.                                                                                                                                                                                                                   |
| `SQL_TEST_ENGINE`               | `"file"`       | Engine used to store the last successful SQL queries. Default `"file"` engine stores data in the file from `SQL_TEST_ENGINE_SETTINGS["filename"]`, or in `.django_sql_test_queries` at the project root if not set. You can implement a custom engine by inheriting from `django_sql_test.engine.Engine`, overriding its methods, and specifying its full path, e.g., `SQL_TEST_ENGINE = "path.to.YourEngine".` |
| `SQL_TEST_ENGINE_SETTINGS`      | `{}`           | Dictionary of settings passed to the engine's constructor. For the default `"file"` engine, you can pass the path to the file where queries will be stored in JSON format.                                                                                                                                                                                                                                      |
| `SQL_TEST_DETECT_N_PLUS_ONE`    | `False`        | If set to True, warns about potential N+1 query patterns in the captured queries every time `assertNumQueries` runs. See [N+1 Query Detection](#n1-query-detection).                                                                                                                                                                                                                                           |
| `SQL_TEST_N_PLUS_ONE_SEVERITY_THRESHOLD` | `"medium"` | Minimum severity (`"low"`, `"medium"`, or `"high"`) a detected N+1 pattern must reach to be reported.                                                                                                                                                                                                                                                                                                  |

### Upgrading from 0.x

Version 1.0 supports multiple `assertNumQueries` calls per test method, which required two breaking changes:

- **Custom engines**: `Engine.get_data_for_testcase` and `Engine.set_data_for_testcase` now take an additional
  `call_index: int = 0` parameter. Add it to your subclass's method signatures.
- **Snapshot file format**: stored queries are now keyed by `<module>.<Class>.<method>:<call_index>` instead of
  `str(testcase)`. The built-in `"file"` engine still reads old-format entries and migrates them to the new format
  automatically on the next successful run, so no action is needed.
- **`diff_utils` exports removed**: `create_queries_diff` and the module-level `old_color`/`new_color`/
  `default_color`/`reset_color` constants are gone. Replace them with `QueryDiffBuilder` and `ColorScheme`:
  ```python
  from django_sql_test.diff_utils import ColorScheme, QueryDiffBuilder

  # added/removed/unchanged take ANSI color codes, or None to use ColorScheme's own defaults
  color_scheme = ColorScheme(added="\033[1;32m", removed="\033[1;31m", unchanged="\033[0m")
  builder = QueryDiffBuilder(new_captured_queries, old_captured_queries, color_scheme)
  diff = builder.build_queries_diff(show_diff_only=diff_only, show_generalized_diff=generalized_diff)
  ```

Note that `call_index` is the position of the `assertNumQueries` call within the test method. Keep the number and
order of calls per test stable: adding, removing, or conditionally executing a call shifts the indices of all
subsequent calls, so their snapshots are compared against the wrong baseline until the next successful run
rewrites them.

`get_engine()` now constructs the engine once per process and caches it, instead of rebuilding it (and re-reading
the snapshot file) on every `assertNumQueries` call. Like every `SQL_TEST_*` setting, `SQL_TEST_ENGINE` and
`SQL_TEST_ENGINE_SETTINGS` are read once when Django starts and were never re-read on later changes (e.g. via
`override_settings`), even before 1.0 — the new caching doesn't change that. If you need a genuinely different
engine/settings per test run, start a separate process (e.g. per-worker when using `--parallel`) rather than
changing settings mid-run.

With `SQL_TEST_DIFF_ONLY` enabled, a test with no stored baseline yet (e.g. the first run after adding
`assertNumQueries`) now shows every captured query as added, instead of printing an empty diff.

### SQL_TEST_GENERALIZED_DIFF

If set to True:
```diff
Queries diff:
+ SELECT polls_choice.id FROM polls_choice WHERE polls_choice.votes >= N
```

If set to False:
```diff
Queries diff:
+ SELECT "polls_choice"."id" FROM "polls_choice" WHERE "polls_choice"."votes" >= 0
```

## N+1 Query Detection

With `SQL_TEST_DETECT_N_PLUS_ONE` set to `True`, every `assertNumQueries` call scans its captured queries for
repeated query patterns against different parameters (a common sign of an N+1 problem) and prints a warning with
the offending pattern, affected table, severity, and suggestions — without failing the test:

```
============================================================
POTENTIAL N+1 QUERY PROBLEMS DETECTED
============================================================

1. N+1 Problem: 5 similar queries on polls_choice
   Severity: MEDIUM
   Pattern: SELECT polls_choice.id FROM polls_choice WHERE polls_choice.question_id = N
   Example queries:
     1. SELECT polls_choice.id FROM polls_choice WHERE polls_choice.question_id = 0
     2. SELECT polls_choice.id FROM polls_choice WHERE polls_choice.question_id = 1
     3. SELECT polls_choice.id FROM polls_choice WHERE polls_choice.question_id = 2
     ... and 2 more
   Suggestions:
     - Use prefetch_related() to fetch related polls_choice objects in batches
     - Review if all these queries are necessary

============================================================
```

Only patterns at or above `SQL_TEST_N_PLUS_ONE_SEVERITY_THRESHOLD` are reported.

### `analyze_n_plus_one` management command

Queries saved by the `"file"` engine (or any custom engine implementing `get_all_data()`) can also be analyzed in
bulk, across all previously recorded test cases:

```shell
poetry run python manage.py analyze_n_plus_one
```

| Option           | Description                                                                 |
|------------------|-------------------------------------------------------------------------------|
| `--severity`     | Minimum severity to report: `low`, `medium`, or `high` (default: `medium`).   |
| `--test-pattern` | Only analyze test cases whose stored key contains this substring.             |
| `--top`          | Show at most this many problems, worst first (default: `10`).                |
| `--detailed`     | Include all example queries for each problem, not just a few.                 |
| `--format`       | `text` (default) or `json`. With `--format json`, stdout is valid JSON (status messages go to stderr), so it can be piped straight into tools like `jq`. |

Custom engines must implement `get_all_data()` (returning `{testcase_name: captured_queries}`) to be usable with
this command; otherwise it raises a `CommandError`.

## API Reference

### `NumNewQueriesMixin`

| Method                | Description                                                                                                                                                                                                                                                                                                          |
|-----------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `assertNumNewQueries` | Works just like django.test.testcases.TransactionTestCase.assertNumQueries, but also prints the diff of queries compared to the last successful run, if any.                                                                                                                                                         |
| `assertNumQueries`    | Acts like assertNumNewQueries. It can be used if you don’t want to replace every occurrence of assertNumQueries with assertNumNewQueries in your tests. Simply inherit from it in your test class, for example: class PaginatorsTestCase(NumNewQueriesMixin, ViewTestCase), and everything will work out of the box. |

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/YourFeature`)
3. Write tests and ensure coverage
4. Run and pass:
    ```shell
    poetry run isort -c --diff --settings-file pyproject.toml .
    poetry run black --diff --config pyproject.toml --check .
    poetry run python runtests.py
    ```
5. Submit a pull request

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Changelog

All notable changes are documented on the [Releases page](https://github.com/shaihulud/django-sql-test/releases).
