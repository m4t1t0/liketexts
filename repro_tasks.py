
from datetime import datetime
from uuid import uuid4
from backend.src.identity.domain.model import User, UserRole
from backend.src.publishing.domain.model import Post
from backend.src.subscriptions.domain.model import Subscription, SubscriptionStatus
from backend.src.subscriptions.adapters.read_model import _insert_follower_ignore, _upsert_subscriber
from backend.src.shared.adapters.unit_of_work import SqlAlchemyUnitOfWork
import backend.src.notifications.tasks as nt

with SqlAlchemyUnitOfWork() as uow:
    suffix = uuid4()
    w = User.register(email=f"t-w-{suffix}@test.com", password_hash=User.hash_password("pw"), first_name="T", last_name="W")
    rs = User.register(email=f"t-s-{suffix}@test.com", password_hash=User.hash_password("pw"), first_name="S", last_name="R")
    rf = User.register(email=f"t-f-{suffix}@test.com", password_hash=User.hash_password("pw"), first_name="F", last_name="R")
    uow.session.add_all([w, rs, rf]); uow.commit()
    rs.add_role(UserRole.READER); rf.add_role(UserRole.READER)
    sub = Subscription.create(reader_id=rs.id, external_subscription_id=f"s-{suffix}", status=SubscriptionStatus.ACTIVE)
    sub.allocate_writer(w.id)
    uow.session.add(sub); uow.session.flush()
    post = Post.create_draft(writer_id=w.id, title="Email me", preview_content="P", subscriber_content="F")
    post.publish(); post.clear_events()
    uow.session.add(post); uow.commit()
    _upsert_subscriber(uow.session, w.id, rs.id, sub.id, datetime.utcnow())
    _insert_follower_ignore(uow.session, w.id, rf.id, datetime.utcnow())
    uow.commit()
    pid = str(post.id)

try:
    print("task result:", nt.send_post_published_emails(pid))
except Exception:
    traceback.print_exc()
