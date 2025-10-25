"""Compatibility helpers for working with JMX connections.

This module provides a small wrapper around the optional
``jmxquery`` dependency so the rest of the codebase can safely
instantiate :class:`~jmxquery.JMXConnection` objects regardless of
the library version that is installed.

Some releases of ``jmxquery`` do not accept a ``timeout`` keyword
argument on ``JMXConnection.__init__``.  The wrapper implemented here
attempts to pass the timeout when requested and gracefully falls back
to instantiating the connection without it when the class raises a
``TypeError`` complaining about the unexpected keyword argument.
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Type

logger = logging.getLogger(__name__)

try:  # pragma: no cover - exercised indirectly in tests via dependency injection
    from jmxquery import JMXConnection as _DefaultJMXConnection
except ImportError:  # pragma: no cover - dependency is optional in tests
    _DefaultJMXConnection = None  # type: ignore[assignment]


class JMXConnectionFactoryError(ImportError):
    """Raised when a JMX connection cannot be constructed."""


def _resolve_connection_class(connection_class: Optional[Type[Any]]) -> Type[Any]:
    """Return the connection class that should be instantiated.

    Parameters
    ----------
    connection_class:
        The explicit connection class provided by the caller.  When ``None``,
        the function attempts to use :class:`jmxquery.JMXConnection` if the
        package is available.

    Raises
    ------
    JMXConnectionFactoryError
        If the caller did not supply a class and ``jmxquery`` is not
        installed.
    """

    if connection_class is not None:
        return connection_class
    if _DefaultJMXConnection is None:
        raise JMXConnectionFactoryError(
            "jmxquery is not installed so a connection class must be provided"
        )
    return _DefaultJMXConnection


def create_jmx_connection(
    *args: Any,
    timeout: Optional[float] = None,
    connection_class: Optional[Type[Any]] = None,
    **kwargs: Any,
) -> Any:
    """Instantiate a JMX connection with optional timeout handling.

    The function tries to pass the provided ``timeout`` keyword argument to the
    connection class' constructor.  If the class raises a ``TypeError`` stating
    that the keyword is unexpected (which happens on older versions of
    ``jmxquery``), the function logs a warning and retries without the timeout
    so the application can continue operating.
    """

    cls = _resolve_connection_class(connection_class)

    if timeout is None:
        return cls(*args, **kwargs)

    try:
        return cls(*args, timeout=timeout, **kwargs)
    except TypeError as exc:
        message = str(exc)
        if "timeout" not in message:
            raise
        logger.warning(
            "JMX connection class %s does not accept a timeout argument; "
            "retrying without it.",
            getattr(cls, "__name__", cls),
        )
        return cls(*args, **kwargs)
