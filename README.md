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
1. SELECT "polls_choice"."id", "polls_choice"."question_id", "polls_choice"."choice_text", "polls_choice"."votes" FROM "polls_choice" WHERE "polls_choice"."votes" >= 0
2. SELECT "polls_question"."id", "polls_question"."question_text", "polls_question"."pub_date" FROM "polls_question" WHERE "polls_question"."id" = 1 LIMIT 21
3. SELECT "polls_question"."id", "polls_question"."question_text", "polls_question"."pub_date" FROM "polls_question" WHERE "polls_question"."id" = 1 LIMIT 21
4. SELECT "polls_question"."id", "polls_question"."question_text", "polls_question"."pub_date" FROM "polls_question" WHERE "polls_question"."id" = 1 LIMIT 21
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
- SELECT polls_choice.id, polls_choice.question_id, polls_choice.choice_text, polls_choice.votes FROM polls_choice
+ SELECT polls_choice.id, polls_choice.question_id, polls_choice.choice_text, polls_choice.votes FROM polls_choice WHERE polls_choice.votes >= N
+ SELECT polls_question.id, polls_question.question_text, polls_question.pub_date FROM polls_question WHERE polls_question.id = N LIMIT N
+ SELECT polls_question.id, polls_question.question_text, polls_question.pub_date FROM polls_question WHERE polls_question.id = N LIMIT N
+ SELECT polls_question.id, polls_question.question_text, polls_question.pub_date FROM polls_question WHERE polls_question.id = N LIMIT N
  SELECT COUNT(*) AS __count FROM polls_question
```

### Settings
#### GENERALIZED_DIFF = True
True by default.
If set to True, hides all SQL-query parameters replacing them with placeholders:
```shell
Queries diff:
+ SELECT polls_choice.id, polls_choice.question_id, polls_choice.choice_text, polls_choice.votes FROM polls_choice WHERE polls_choice.votes >= N
```

If set to False:
```shell
Queries diff:
+ SELECT "polls_choice"."id", "polls_choice"."question_id", "polls_choice"."choice_text", "polls_choice"."votes" FROM "polls_choice" WHERE "polls_choice"."votes" >= 0
```

#### DIFF_ONLY = False
False by default.
If set, hides all unchanged SQL-queries.
