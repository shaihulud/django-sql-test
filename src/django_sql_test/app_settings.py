from django.conf import settings


ENGINE = getattr(settings, "SQL_TEST_ENGINE", "file")
ENGINE_SETTINGS = getattr(settings, "SQL_TEST_ENGINE_SETTINGS", dict())
GENERALIZED_DIFF = getattr(settings, "SQL_TEST_GENERALIZED_DIFF", True)
