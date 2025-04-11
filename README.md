# django-sql-test

A Django test mixin that captures and analyzes SQL queries during tests, with built-in support for displaying diffs between previous and current queries for spotting unexpected changes or regressions.

## Usage

### Requirements

* Django >= 4.0
* Python 3.9 and above.

### Installation

Install with:

```shell
pip install django-sql-test
```

### Quickstart

In your test.py just import NumNewQueriesMixin and add it as a parent:

```python
from django.test import TestCase
from django_sql_test.utils import NumNewQueriesMixin

class FooTest(NumNewQueriesMixin, TestCase):
    def test_bar(self):
        with self.assertNumQueries(3):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

```
