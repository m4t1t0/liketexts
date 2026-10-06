"""Writers Catalog API routes (/api/v1/writers)."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, jsonify, request
from werkzeug.exceptions import BadRequest, NotFound

from backend.src.identity.api_auth import get_current_user, get_optional_reader_id
from backend.src.shared.api import parse_uuid
from backend.src.shared.domain.value_objects import as_status_str

writers_bp = Blueprint("writers", __name__, url_prefix="/api/v1/writers")


@writers_bp.route("", methods=["GET"])
def list_writers() -> Response | tuple[Any, ...]:
    """Searchable list of public writers."""
    from backend.src.identity.adapters.sqlalchemy_repository import (
        SqlAlchemyUserRepository,
    )
    from backend.src.shared.adapters.unit_of_work import SqlAlchemyUnitOfWork

    query = request.args.get("q", "").strip().lower()
    limit = request.args.get("limit", 20, type=int)
    offset = request.args.get("offset", 0, type=int)

    with SqlAlchemyUnitOfWork() as uow:
        user_repo = SqlAlchemyUserRepository(uow.session)
        users = user_repo.list()
        writers = [u for u in users if u.is_writer()]
        if query:
            writers = [
                w
                for w in writers
                if query in w.display_name.lower()
                or query in (w.first_name or "").lower()
                or query in (w.last_name or "").lower()
            ]
        total = len(writers)
        writers = writers[offset : offset + limit]
        result = [
            {
                "id": str(w.id),
                "display_name": w.display_name,
                "first_name": w.first_name,
                "last_name": w.last_name,
                "avatar_url": w.avatar_url,
                "created_at": w.created_at.isoformat(),
            }
            for w in writers
        ]
    return jsonify({"writers": result, "total": total})


@writers_bp.route("/<writer_id>", methods=["GET"])
def get_writer(writer_id: str) -> Response | tuple[Any, ...]:
    """Writer profile & past newsletters (paywall-masked for non-subscribers)."""
    writer_uuid = parse_uuid(writer_id, "writer_id")

    from backend.src.identity.adapters.sqlalchemy_repository import (
        SqlAlchemyUserRepository,
    )
    from backend.src.publishing.adapters.sqlalchemy_repository import (
        SqlAlchemyPostRepository,
    )
    from backend.src.subscriptions.adapters.sqlalchemy_repository import (
        SqlAlchemySubscriptionRepository,
    )
    from backend.src.publishing.domain.model import PostStatus
    from backend.src.shared.adapters.unit_of_work import SqlAlchemyUnitOfWork

    reader_id = get_optional_reader_id()

    with SqlAlchemyUnitOfWork() as uow:
        user_repo = SqlAlchemyUserRepository(uow.session)
        writer = user_repo.get(writer_uuid)
        if not writer or not writer.is_writer():
            raise NotFound("Writer not found")

        post_repo = SqlAlchemyPostRepository(uow.session)
        posts = post_repo.get_by_writer(writer_uuid, PostStatus.PUBLISHED)

        has_allocation = False
        is_following_writer = False
        if reader_id:
            from backend.src.subscriptions.adapters.read_model import is_following

            sub_repo = SqlAlchemySubscriptionRepository(uow.session)
            subscription = sub_repo.get_by_reader(reader_id)
            if subscription:
                status = as_status_str(subscription.status)
                if status == "active":
                    has_allocation = subscription.is_writer_allocated(writer_uuid)
            is_following_writer = is_following(uow.session, writer_uuid, reader_id)

        post_data = [
            {
                **p.get_content_for_reader(has_allocation, reader_id),
                "writer_name": writer.display_name,
                "writer_avatar_url": writer.avatar_url,
            }
            for p in posts
        ]

        result = {
            "id": str(writer.id),
            "display_name": writer.display_name,
            "first_name": writer.first_name,
            "last_name": writer.last_name,
            "avatar_url": writer.avatar_url,
            "created_at": writer.created_at.isoformat(),
            "subscriber_post_count": len(post_data),
            "is_following": is_following_writer,
            "posts": post_data,
        }
    return jsonify(result)


@writers_bp.route("/<writer_id>/follow", methods=["POST"])
def follow_writer(writer_id: str) -> Response | tuple[Any, ...]:
    """Follow a writer (preview emails, no allocation slot)."""
    from datetime import datetime

    from backend.src.identity.adapters.sqlalchemy_repository import (
        SqlAlchemyUserRepository,
    )
    from backend.src.shared.adapters.unit_of_work import SqlAlchemyUnitOfWork
    from backend.src.subscriptions.adapters.read_model import (
        _insert_follower_ignore,
    )

    reader = get_current_user()
    writer_uuid = parse_uuid(writer_id, "writer_id")
    reader_id = parse_uuid(str(reader["id"]), "reader_id")
    if reader_id == writer_uuid:
        raise BadRequest("Cannot follow yourself")

    with SqlAlchemyUnitOfWork() as uow:
        writer = SqlAlchemyUserRepository(uow.session).get(writer_uuid)
        if not writer or not writer.is_writer():
            raise NotFound("Writer not found")
        _insert_follower_ignore(uow.session, writer_uuid, reader_id, datetime.utcnow())
        uow.commit()
    return jsonify({"following": True}), 201


@writers_bp.route("/<writer_id>/follow", methods=["DELETE"])
def unfollow_writer(writer_id: str) -> Response | tuple[Any, ...]:
    """Stop following a writer."""
    from backend.src.identity.adapters.sqlalchemy_repository import (
        SqlAlchemyUserRepository,
    )
    from backend.src.shared.adapters.unit_of_work import SqlAlchemyUnitOfWork
    from backend.src.subscriptions.adapters.read_model import remove_follower

    reader = get_current_user()
    writer_uuid = parse_uuid(writer_id, "writer_id")

    with SqlAlchemyUnitOfWork() as uow:
        writer = SqlAlchemyUserRepository(uow.session).get(writer_uuid)
        if not writer or not writer.is_writer():
            raise NotFound("Writer not found")
        remove_follower(uow.session, writer_uuid, parse_uuid(str(reader["id"]), "reader_id"))
        uow.commit()
    return jsonify({"following": False})
