"""Local filesystem storage for profile avatars (v1).

Files live under `<repo>/uploads/avatars/` (configurable via
`AVATAR_UPLOAD_DIR`) and are served by Flask at `/uploads/avatars/<file>`.
`avatar_url` stores that relative public path so it works across hosts.

Validators: extension allowlist + magic-byte sniffing + size cap
(`AVATAR_MAX_UPLOAD_MB`). No Pillow dependency — signatures are checked
directly. A future S3-backed implementation can replace `save_avatar`
without touching the API layer.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
EXTENSION_TO_KIND = {
    "png": "png",
    "jpg": "jpeg",
    "jpeg": "jpeg",
    "webp": "webp",
    "gif": "gif",
}


def _upload_dir() -> Path:
    from backend.src.shared.config import get_settings

    configured = Path(get_settings().avatar_upload_dir)
    if configured.is_absolute():
        return configured
    repo_root = Path(__file__).resolve().parents[4]
    return repo_root / configured


def upload_dir() -> Path:
    """Public upload directory (shared with the Flask file-serving route)."""
    return _upload_dir()


def _max_bytes() -> int:
    from backend.src.shared.config import get_settings

    return get_settings().avatar_max_upload_mb * 1024 * 1024


def sniff_image_kind(data: bytes) -> str | None:
    """Return image kind from magic bytes, or None if unrecognized."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    return None


def save_avatar(user_id: UUID, filename: str, data: bytes) -> str:
    """Validate and persist an avatar; returns the public `avatar_url` path."""
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '.{ext}'. Allowed: png, jpg, jpeg, webp, gif."
        )
    if len(data) > _max_bytes():
        from backend.src.shared.config import get_settings

        raise ValueError(
            f"File too large ({len(data)} bytes). "
            f"Max is {get_settings().avatar_max_upload_mb} MB."
        )
    kind = sniff_image_kind(data)
    if kind is None:
        raise ValueError("File content is not a recognized image (png/jpg/webp/gif).")
    if kind != EXTENSION_TO_KIND[ext]:
        raise ValueError(
            f"File extension '.{ext}' does not match image content ({kind})."
        )

    upload_dir = _upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored = f"{user_id.hex}-{uuid4().hex[:12]}.{ext}"
    (upload_dir / stored).write_bytes(data)
    return f"/uploads/avatars/{stored}"


def delete_avatar(avatar_url: str | None) -> None:
    """Remove a previously stored avatar file (no-op for external URLs)."""
    if not avatar_url or not avatar_url.startswith("/uploads/avatars/"):
        return
    name = Path(avatar_url).name
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        return
    try:
        (Path(_upload_dir()) / name).unlink(missing_ok=True)
    except OSError:
        pass
