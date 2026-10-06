"""Identity API routes."""

from __future__ import annotations
from typing import Any
from uuid import UUID

from flask import Blueprint, Response, jsonify, request, send_from_directory
from werkzeug.exceptions import BadRequest

from backend.src.shared.api import get_bus
from backend.src.identity.api_auth import get_bearer_user_id
from backend.src.identity.commands import (
    GetProfileCommand,
    LoginCommand,
    RefreshTokenCommand,
    RegisterCommand,
    UpdateProfileCommand,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

# Static file serving for locally stored avatars (no /api prefix, so it
# stays out of the OpenAPI spec which only covers /api/* and /health*).
avatar_files_bp = Blueprint("avatar_files", __name__)


@auth_bp.route("/register", methods=["POST"])
def register() -> Response | tuple[Any, ...]:
    """Register a new user (email + password only; no role).

    Reader/Writer capabilities are inferred from activity, never chosen at
    signup: creating a post grants WRITER, subscribing/following grants READER.
    A client-sent `role` field, if present, is ignored for backwards compat.
    """
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        raise BadRequest("Email and password are required")

    def _optional_str(value: object) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text or None

    command = RegisterCommand(
        email=email,
        password=password,
        first_name=_optional_str(data.get("first_name")),
        last_name=_optional_str(data.get("last_name")),
        avatar_url=_optional_str(data.get("avatar_url")),
    )
    bus = get_bus()
    user = bus.handle(command)

    return jsonify(
        {
            "id": str(user.id),
            "email": user.email,
            "created_at": user.created_at.isoformat(),
        }
    ), 201


@auth_bp.route("/login", methods=["POST"])
def login() -> Response | tuple[Any, ...]:
    """Login and get tokens."""
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        raise BadRequest("Email and password are required")

    command = LoginCommand(
        email=email,
        password=password,
        user_agent=request.headers.get("User-Agent"),
        ip=request.remote_addr,
    )
    bus = get_bus()
    tokens = bus.handle(command)

    return jsonify(
        {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "expires_in": tokens.expires_in,
            "token_type": tokens.token_type,
        }
    )


@auth_bp.route("/refresh", methods=["POST"])
def refresh() -> Response | tuple[Any, ...]:
    """Refresh access token."""
    data = request.get_json() or {}
    refresh_token = data.get("refresh_token", "")

    if not refresh_token:
        raise BadRequest("Refresh token is required")

    command = RefreshTokenCommand(
        refresh_token=refresh_token,
        user_agent=request.headers.get("User-Agent"),
        ip=request.remote_addr,
    )
    bus = get_bus()
    tokens = bus.handle(command)

    return jsonify(
        {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "expires_in": tokens.expires_in,
            "token_type": tokens.token_type,
        }
    )


@auth_bp.route("/me", methods=["GET"])
def me() -> Response | tuple[Any, ...]:
    """Get current user profile."""
    user_id = get_bearer_user_id()
    bus = get_bus()

    from backend.src.shared.domain.value_objects import UserId

    command = GetProfileCommand(user_id=UserId(value=user_id))
    user = bus.handle(command)

    return jsonify(_profile_payload(user))


def _profile_payload(user: Any) -> dict[str, Any]:
    """Serialize a User aggregate to the Profile response shape."""
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "avatar_url": user.avatar_url,
        "created_at": user.created_at.isoformat(),
        "is_writer": user.is_writer(),
        "is_reader": user.is_reader(),
    }


@auth_bp.route("/me", methods=["PATCH"])
def update_me() -> Response | tuple[Any, ...]:
    """Update editable profile fields (first/last name, avatar URL).

    Partial update: only keys present in the JSON body are changed.
    Send an empty string or null to clear a field.
    """
    from backend.src.shared.domain.value_objects import UserId

    user_id = get_bearer_user_id()
    data = request.get_json() or {}
    if not isinstance(data, dict):
        raise BadRequest("JSON object body is required")

    kwargs: dict[str, Any] = {}
    for field_name in ("first_name", "last_name"):
        if field_name in data:
            value = data[field_name]
            if value is not None and not isinstance(value, str):
                raise BadRequest(f"{field_name} must be a string or null")
            text = (value or "").strip()
            if len(text) > 120:
                raise BadRequest(f"{field_name} must be at most 120 characters")
            kwargs[field_name] = text or None
    if "avatar_url" in data:
        value = data["avatar_url"]
        if value is not None and not isinstance(value, str):
            raise BadRequest("avatar_url must be a string or null")
        kwargs["avatar_url"] = (value or "").strip() or None

    if not kwargs:
        raise BadRequest(
            "No editable fields provided (first_name, last_name, avatar_url)"
        )

    bus = get_bus()
    user = bus.handle(UpdateProfileCommand(user_id=UserId(value=user_id), **kwargs))
    return jsonify(_profile_payload(user))


@auth_bp.route("/avatar", methods=["POST"])
def upload_avatar() -> Response | tuple[Any, ...]:
    """Upload a profile picture (multipart `file` field: png/jpg/webp/gif).

    Stores the file locally, points the user's `avatar_url` at it, and
    removes the previous locally stored avatar.
    """
    from backend.src.identity.adapters.avatar_storage import (
        delete_avatar,
        save_avatar,
    )
    from backend.src.shared.domain.value_objects import UserId

    user_id = get_bearer_user_id()
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        raise BadRequest("A 'file' multipart field is required")

    bus = get_bus()
    current = bus.handle(GetProfileCommand(user_id=UserId(value=user_id)))
    try:
        avatar_url = save_avatar(UUID(str(current.id)), upload.filename, upload.read())
    except ValueError as e:
        raise BadRequest(str(e))

    user = bus.handle(
        UpdateProfileCommand(user_id=UserId(value=user_id), avatar_url=avatar_url)
    )
    delete_avatar(current.avatar_url)
    return jsonify(_profile_payload(user)), 201


@avatar_files_bp.route("/uploads/avatars/<path:filename>", methods=["GET"])
def serve_avatar(filename: str) -> Response:
    """Serve a locally stored avatar file."""
    from backend.src.identity.adapters.avatar_storage import upload_dir

    return send_from_directory(upload_dir(), filename)
