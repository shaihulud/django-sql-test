from django.conf import settings


ENGINE = getattr(settings, "SQL_TEST_ENGINE", "file")
ENGINE_SETTINGS = getattr(settings, "SQL_TEST_ENGINE_SETTINGS", dict())
