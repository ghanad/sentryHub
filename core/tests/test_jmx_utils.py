from django.test import TestCase

from core.utils.jmx import JMXConnectionFactoryError, create_jmx_connection


class _ConnectionWithTimeout:
    def __init__(self, *args, timeout=None, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.timeout = timeout


class _LegacyConnection:
    def __init__(self, *args):
        self.args = args
        self.kwargs = {}


class _ExplodingConnection:
    def __init__(self, *args, timeout=None, **kwargs):
        raise TypeError("boom")


class JMXConnectionFactoryTests(TestCase):
    def test_requires_connection_class_when_dependency_missing(self):
        with self.assertRaisesRegex(
            JMXConnectionFactoryError, "connection class must be provided"
        ):
            create_jmx_connection("service:jmx:foo")

    def test_supports_timeout_when_constructor_accepts_it(self):
        connection = create_jmx_connection(
            "service:jmx:foo", timeout=5, connection_class=_ConnectionWithTimeout
        )
        self.assertIsInstance(connection, _ConnectionWithTimeout)
        self.assertEqual(connection.timeout, 5)
        self.assertEqual(connection.args, ("service:jmx:foo",))

    def test_retries_without_timeout_on_type_error(self):
        with self.assertLogs("core.utils.jmx", level="WARNING") as captured:
            connection = create_jmx_connection(
                "service:jmx:foo", timeout=10, connection_class=_LegacyConnection
            )
        self.assertIsInstance(connection, _LegacyConnection)
        self.assertEqual(connection.args, ("service:jmx:foo",))
        # No timeout should be persisted in kwargs when we retry without it
        self.assertNotIn("timeout", connection.kwargs)
        self.assertIn("does not accept a timeout argument", captured.output[0])

    def test_propagates_unrelated_type_error(self):
        with self.assertRaisesRegex(TypeError, "boom"):
            create_jmx_connection(
                "service:jmx:foo", timeout=1, connection_class=_ExplodingConnection
            )
