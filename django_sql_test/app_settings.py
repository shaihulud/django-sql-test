from django.conf import settings


ENGINE = getattr(settings, "SQL_TEST_ENGINE", "file")
ENGINE_SETTINGS = getattr(settings, "SQL_TEST_ENGINE_SETTINGS", dict())
GENERALIZED_DIFF = getattr(settings, "SQL_TEST_GENERALIZED_DIFF", True)
DIFF_ONLY = getattr(settings, "SQL_TEST_DIFF_ONLY", False)
DIFF_NEW_COLOR = getattr(settings, "SQL_TEST_DIFF_NEW_COLOR", None)
DIFF_OLD_COLOR = getattr(settings, "SQL_TEST_DIFF_OLD_COLOR", None)
DIFF_DEFAULT_COLOR = getattr(settings, "SQL_TEST_DIFF_DEFAULT_COLOR", None)
