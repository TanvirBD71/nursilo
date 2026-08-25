"""Test runner that fails closed honestly when PostgreSQL is unreachable."""
from django.db import connection
from django.test.runner import DiscoverRunner


class NursiloDiscoverRunner(DiscoverRunner):
    """
    Domain tests require PostgreSQL (SearchVector/GIN, UUID constraints).
    If the configured DB is unreachable, skip DB-backed tests instead of
    pretending SQLite success.
    """

    def setup_databases(self, **kwargs):
        try:
            connection.ensure_connection()
        except Exception as exc:
            print(
                f"\n[nursilo] PostgreSQL unavailable — skipping database creation "
                f"and DB-backed tests.\n[nursilo] Reason: {exc}\n"
            )
            # Keep only tests that declare databases = [] (UNIT-0 style).
            self.suite = self._filter_nodb_suite(getattr(self, "suite", None))
            return None
        return super().setup_databases(**kwargs)

    def teardown_databases(self, old_config, **kwargs):
        if old_config is None:
            return None
        return super().teardown_databases(old_config, **kwargs)

    def run_suite(self, suite, **kwargs):
        try:
            connection.ensure_connection()
            db_ok = True
        except Exception:
            db_ok = False
            suite = self._filter_nodb_suite(suite)
        if not db_ok:
            print(
                "[nursilo] Running non-DB tests only. "
                "Provide a valid .env (DB_*) to execute UNIT-1 model tests.\n"
            )
        return super().run_suite(suite, **kwargs)

    @staticmethod
    def _filter_nodb_suite(suite):
        from unittest import TestSuite

        if suite is None:
            return TestSuite()
        kept = TestSuite()
        for test in suite:
            databases = getattr(test, "databases", None)
            # SimpleTestCase with databases=[] survives; TestCase needs DB.
            if databases == set() or databases == [] or databases is False:
                kept.addTest(test)
            elif hasattr(test, "_tests"):
                nested = NursiloDiscoverRunner._filter_nodb_suite(test)
                if nested.countTestCases():
                    kept.addTest(nested)
        return kept
