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

| Setting                       | Default        | Description                                                                                                                                                                                                                                                                                                                                                                                                     |
|-------------------------------|----------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `SQL_TEST_GENERALIZED_DIFF`   | `True`         | Hides SQL query parameters by replacing them with placeholders.                                                                                                                                                                                                                                                                                                                                                 |
| `SQL_TEST_DIFF_ONLY`          | `False`        | If set to True, shows only SQL queries that were added or removed; otherwise, shows all queries.                                                                                                                                                                                                                                                                                                                |
| `SQL_TEST_DIFF_NEW_COLOR`     | `"\033[1;32m"` | Color code for newly added SQL queries (green).                                                                                                                                                                                                                                                                                                                                                                 |
| `SQL_TEST_DIFF_OLD_COLOR`     | `"\033[1;31m"` | Color code for removed SQL queries (red).                                                                                                                                                                                                                                                                                                                                                                       |
| `SQL_TEST_DIFF_DEFAULT_COLOR` | `"\033[0m"`    | Base console color code for unchanged SQL queries.                                                                                                                                                                                                                                                                                                                                                              |
| `SQL_TEST_ENGINE`             | `"file"`       | Engine used to store the last successful SQL queries. Default `"file"` engine stores data in the file from `SQL_TEST_ENGINE_SETTINGS["filename"]`, or in `.django_sql_test_queries` at the project root if not set. You can implement a custom engine by inheriting from `django_sql_test.engine.Engine`, overriding its methods, and specifying its full path, e.g., `SQL_TEST_ENGINE = "path.to.YourEngine".` |
| `SQL_TEST_ENGINE_SETTINGS`    | `{}`           | Dictionary of settings passed to the engine's constructor. For the default `"file"` engine, you can pass the path to the file where queries will be stored in JSON format.                                                                                                                                                                                                                                      |

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
