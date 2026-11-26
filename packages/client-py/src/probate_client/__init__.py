"""Typed sync and async client for the Probate Courthouse public API."""

from probate_client import types
from probate_client.client import (
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    ApiError,
    AsyncProbateClient,
    ProbateClient,
)

__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_TIMEOUT",
    "ApiError",
    "AsyncProbateClient",
    "ProbateClient",
    "types",
]
__version__ = "0.1.1"
