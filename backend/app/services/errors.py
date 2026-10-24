"""Domain-level exceptions, mapped to HTTP responses in the API layer."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for domain errors."""


class NotFoundError(DomainError):
    """A requested entity does not exist."""


class ValidationError(DomainError):
    """A request is semantically invalid (e.g. illegal status transition)."""
