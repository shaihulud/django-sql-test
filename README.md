# django-sql-test

A Django test mixin that captures and analyzes SQL queries during tests, with built-in support for displaying diffs between previous and current queries for spotting unexpected changes or regressions.

<a href="https://pypi.org/project/django-sql-test/" target="_blank">
    <img src="https://img.shields.io/pypi/v/django-sql-test?color=%2334D058&label=pypi%20package" alt="Package version">
</a>
<a href="https://pypi.org/project/django-sql-test/" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/django-sql-test.svg?color=%2334D058" alt="Supported Python versions">
</a>
<a href="https://pypi.org/project/django-sql-test/" target="_blank">
    <img src="https://img.shields.io/pypi/l/django-sql-test.svg?color=%2334D058" alt="License">
</a>

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

* Django >= 4.0
* Python 3.9 and above.

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
        with self.assertNumQueries(2):
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
```shell
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

#### SQL_TEST_GENERALIZED_DIFF = True
True by default.
If set to True, hides all SQL-query parameters replacing them with placeholders:
```shell
Queries diff:
+ SELECT polls_choice.id FROM polls_choice WHERE polls_choice.votes >= N
```

If set to False:
```shell
Queries diff:
+ SELECT "polls_choice"."id" FROM "polls_choice" WHERE "polls_choice"."votes" >= 0
```

#### SQL_TEST_DIFF_ONLY = False
False by default.
If set, hides all unchanged SQL-queries.

#### SQL_TEST_DIFF_DEFAULT_COLOR = "\033[0m"
#### SQL_TEST_DIFF_NEW_COLOR = "\033[1;32m"
#### SQL_TEST_DIFF_OLD_COLOR = "\033[1;31m"
Sets colors for console diff. Git-style by default: red for old, green for new, and default console color for lines that haven't changed.

## API Reference

### `NumNewQueriesMixin`

| Method                                | Description                                                                                                                                                                                                                                                                                          |
| ------------------------------------- |------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `assertNumNewQueries` | Works just like django.test.testcases.TransactionTestCase.assertNumQueries, but also prints the diff of queries compared to the last successful run, if any.                                                                                                                                         |
| `assertNumQueries` | Acts like assertNumNewQueries. It can be used if you don’t want to replace every occurrence of assertNumQueries with assertNumNewQueries in your tests. Simply inherit from it in your test class, for example: class PaginatorsTestCase(NumNewQueriesMixin, ViewTestCase), and everything will work out of the box. |

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
