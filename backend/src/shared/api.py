"""Shared Flask request-layer helpers (bus access, id parsing)."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from flask import current_app
from werkzeug.exceptions import BadRequest

from backend.src.shared.service_layer.messagebus import MessageBus


def get_bus() -> MessageBus:
    """Get the message bus attached to the app context."""
    return cast(MessageBus, getattr(current_app, "message_bus"))


def parse_uuid(value: Any, name: str = "id") -> UUID:
    """Parse an id from a request path or body; raises BadRequest on garbage.

    Keeps \"malformed id -> 400\" consistent across API modules instead of a
    try/except ValueError cascade repeated per route.
    """
    try:
        return UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        raise BadRequest(f"Invalid {name} format")
