"""Integration tests for the Celery scheduled-post beat task.

Regression context (2026-10): the Celery worker process never runs the Flask
app factory, so ORM mappers were unmapped in tasks until
`_ensure_orm_mappers()` was added — `query(Post)` raised an SQLAlchemy
coercion error on every beat tick.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.orm import class_mapper

from backend.src.identity.domain.model import User
from backend.src.notifications import tasks as notifications_tasks
from backend.src.publishing.domain.model import Post, PostStatus
from backend.src.subscriptions.domain.model import Subscription
from backend.src.shared.adapters.unit_of_work import SqlAlchemyUnitOfWork


def _due_scheduled_post(writer_id: UUID) -> Post:
    post = Post.create_scheduled(
        writer_id=writer_id,
        title="Due now",
        preview_content="PRE",
        subscriber_content="FULL",
        scheduled_for=datetime.utcnow() + timedelta(seconds=2),
    )
    # Backdate so it is immediately due for the beat task
    post.scheduled_for = datetime.utcnow() - timedelta(seconds=1)
    return post


class TestEnsureOrmMappers:
    def test_maps_all_aggregates_and_is_idempotent(self) -> None:
        notifications_tasks._ensure_orm_mappers()
        notifications_tasks._ensure_orm_mappers()  # idempotent (no error)

        for model in (User, Post, Subscription):
            class_mapper(model)  # raises if the aggregate is unmapped


class TestProcessScheduledPosts:
    def test_publishes_due_post_and_enqueues_email(self, monkeypatch) -> None:
        enqueued: list[str] = []
        monkeypatch.setattr(
            notifications_tasks,
            "send_post_published_emails",
            type(
                "StubEmailTask",
                (),
                {"delay": staticmethod(lambda post_id: enqueued.append(post_id))},
            )(),
        )

        with SqlAlchemyUnitOfWork() as uow:
            user = User.register(
                email=f"beat-{uuid4()}@test.com",
                password_hash=User.hash_password("password123"),
            )
            uow.session.add(user)
            uow.commit()
            post = _due_scheduled_post(user.id)
            uow.session.add(post)
            uow.commit()
            post_id = str(post.id)

        result = notifications_tasks.process_scheduled_posts()

        assert post_id in result["published_posts"]
        assert enqueued == [post_id]

        with SqlAlchemyUnitOfWork() as uow:
            refreshed = uow.session.get(Post, UUID(post_id))
            assert refreshed is not None
            assert refreshed.status == PostStatus.PUBLISHED
            assert refreshed.published_at is not None
