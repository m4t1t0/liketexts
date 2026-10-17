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



class TestSendPostPublishedEmails:
    def test_db_loaded_post_with_string_status_sends_both_kinds(self) -> None:
        """Regression (2026-10): post.status was a plain string when loaded
        from the DB, and the task crashed on post.status.value."""
        from datetime import datetime

        from backend.src.identity.domain.model import UserRole
        from backend.src.subscriptions.adapters.read_model import (
            _insert_follower_ignore,
            _upsert_subscriber,
        )
        from backend.src.subscriptions.domain.model import SubscriptionStatus

        with SqlAlchemyUnitOfWork() as uow:
            suffix = uuid4()
            writer = User.register(
                email=f"mail-w-{suffix}@test.com",
                password_hash=User.hash_password("password123"),
                first_name="Mail",
                last_name="Writer",
            )
            reader_sub = User.register(
                email=f"mail-sub-{suffix}@test.com",
                password_hash=User.hash_password("password123"),
                first_name="Sub",
                last_name="Reader",
            )
            reader_fol = User.register(
                email=f"mail-fol-{suffix}@test.com",
                password_hash=User.hash_password("password123"),
                first_name="Fol",
                last_name="Reader",
            )
            uow.session.add_all([writer, reader_sub, reader_fol])
            uow.commit()
            reader_sub.add_role(UserRole.READER)
            reader_fol.add_role(UserRole.READER)

            sub = Subscription.create(
                reader_id=reader_sub.id,
                external_subscription_id=f"mail-test-{suffix}",
                status=SubscriptionStatus.ACTIVE,
            )
            sub.allocate_writer(writer.id)
            uow.session.add(sub)
            uow.session.flush()  # subscription row must exist before projections

            post = Post.create_draft(
                writer_id=writer.id,
                title="Email me",
                preview_content="PREVIEW",
                subscriber_content="FULL",
            )
            post.publish()
            post.clear_events()
            uow.session.add(post)
            uow.commit()

            _upsert_subscriber(
                uow.session, writer.id, reader_sub.id, sub.id, datetime.utcnow()
            )
            _insert_follower_ignore(
                uow.session, writer.id, reader_fol.id, datetime.utcnow()
            )
            uow.commit()

        result = notifications_tasks.send_post_published_emails(str(post.id))

        assert result["status"] == "sent"
        assert result["subscribers_notified"] == 1
        assert result["followers_notified"] == 1
        assert result["emails_logged"] == 2
