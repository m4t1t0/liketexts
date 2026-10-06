"""Seed development data.

Idempotent: skips entirely if reader1@example.com already exists. Creates
writers with generated SVG avatars, readers with subscriptions/allocations,
followers, and a realistic post mix (published / draft / scheduled).

Run: `make seed` (docker compose run --rm api python -m scripts.seed_dev)
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from backend.src.shared.adapters.unit_of_work import SqlAlchemyUnitOfWork
from backend.src.identity.adapters.orm import (
    create_tables as create_identity_tables,
    start_mappers as start_identity_mappers,
)
from backend.src.subscriptions.adapters.orm import (
    create_tables as create_sub_tables,
    start_mappers as start_sub_mappers,
)
from backend.src.publishing.adapters.orm import (
    create_tables as create_pub_tables,
    start_mappers as start_pub_mappers,
)
from backend.src.identity.adapters.sqlalchemy_repository import (
    SqlAlchemyUserRepository,
)
from backend.src.identity.domain.model import User, UserRole
from backend.src.identity.adapters.avatar_storage import upload_dir
from backend.src.subscriptions.adapters.read_model import (
    _insert_follower_ignore,
    _upsert_subscriber,
)
from backend.src.subscriptions.domain.model import Subscription, SubscriptionStatus
from backend.src.publishing.domain.model import Post

PASSWORD = "password123"

# (first, last, email, tagline colour index)
WRITERS = [
    ("Mara", "Voss", "mara@example.com", 0),
    ("Dev", "Okonkwo", "dev@example.com", 1),
    ("June", "Park", "june@example.com", 2),
    ("Tomás", "Rivera", "tomas@example.com", 3),
    ("Ingrid", "Halvorsen", "ingrid@example.com", 4),
    ("Sam", "Whitaker", "sam@example.com", 5),
]

READERS = [
    ("Alice", "Reader", "reader1@example.com"),
    ("Bob", "Reader", "reader2@example.com"),
    ("Carmen", "Diaz", "reader3@example.com"),
]

# reader email -> writer emails they subscribe to (allocate slots)
ALLOCATIONS = {
    "reader1@example.com": ["mara@example.com", "dev@example.com", "june@example.com"],
    "reader2@example.com": ["mara@example.com", "tomas@example.com"],
}

# reader email -> writer emails they follow WITHOUT an allocation (preview emails)
FOLLOWS = {
    "reader2@example.com": ["dev@example.com", "june@example.com"],
    "reader3@example.com": ["mara@example.com", "sam@example.com", "ingrid@example.com"],
}

# title, preview, subscriber content, published offset in hours (None = draft,
# negative handled as scheduled in SCHEDULED below)
POSTS = {
    "mara@example.com": [
        (
            "Reading the trail before the map existed",
            "Long before surveyors drew lines, people read the land itself — "
            "moss, grain of stone, the bend of trees. What did they know that we forgot?",
            "## Reading the trail before the map existed\n\n"
            "Long before surveyors drew lines, people read the land itself.\n\n"
            "- Moss as a compass (and when it lies)\n"
            "- Sheep paths as the oldest infrastructure\n"
            "- Why desire lines beat master plans\n\n"
            "This week I walked the old drove road above the valley with a 1747 "
            "map in one hand and no signal in the other — and the landscape "
            "corrected the map more often than the map corrected the landscape.",
            5 * 24,
        ),
        (
            "The last lighthouse keeper's logbook",
            "Forty-one years of weather in pencil. Entry 3,102 just says: "
            "\"Fog. Wound the clock. Listened.\"",
            "## The last lighthouse keeper's logbook\n\n"
            "Forty-one years of weather in pencil.\n\n"
            "The logbook is a masterclass in restraint: tides, wind, ships "
            "passed, nothing else. Entry 3,102 just says: *\"Fog. Wound the "
            "clock. Listened.\"*\n\n"
            "We talk about attention as if it were new. He had it in 1962, "
            "in a room the size of a kitchen, with the sea doing the talking.",
            2 * 24,
        ),
    ],
    "dev@example.com": [
        (
            "Your deploy pipeline doesn't need another tool",
            "Every green checkmark you add is a promise you'll keep at 2am. "
            "Most pipelines need fewer gates, not more.",
            "## Your deploy pipeline doesn't need another tool\n\n"
            "Every green checkmark you add is a promise you'll keep at 2am.\n\n"
            "1. Merge queues are a queue because you don't trust main — fix that\n"
            "2. Feature flags beat release branches\n"
            "3. If rollback is scary, deploy more often, not less\n\n"
            "The best pipeline I ever ran had three steps and ran in ninety "
            "seconds. We spent the saved time on sleep.",
            3 * 24,
        ),
        (
            "The bug that only happened on Tuesdays",
            "A cache, a cron, and a timezone walked into a bar. This one took "
            "us six days to find and one line to fix.",
            "## The bug that only happened on Tuesdays\n\n"
            "A cache, a cron, and a timezone walked into a bar.\n\n"
            "The report queue drained correctly every day except Tuesday, when "
            "it double-counted a window. The cause: a weekly job keyed its "
            "cache on ISO week number, and our reports cut over at midnight — "
            "except on Mondays that were also first-of-month. Six days of "
            "digging, one line to fix, and a new team rule: **no date math "
            "without UTC**.",
            6 * 24,
        ),
    ],
    "june@example.com": [
        (
            "Why your grinder matters more than your beans",
            "Unpopular in specialty circles: a $200 grinder with honest beans "
            "beats a $40 bag through a dull blade. Here's the taste math.",
            "## Why your grinder matters more than your beans\n\n"
            "Unpopular in specialty circles: a $200 grinder with honest beans "
            "beats a $40 bag through a dull blade.\n\n"
            "Grind distribution is the hidden variable in every cup. Boulders "
            "over-extract, fines under-settle, and your tongue reads the mess "
            "as \"sour OR bitter\" when it's really both. I cupped the same "
            "Ethiopian through five grinders — the spread was wider than "
            "between roasts.",
            30,
        ),
        (
            "A field guide to water",
            "The recipe everyone argues about (ratio) matters less than the "
            "two things nobody measures: hardness and temperature stability.",
            "## A field guide to water\n\n"
            "The recipe everyone argues about — ratio — matters less than the "
            "two things nobody measures: hardness and temperature stability.\n\n"
            "I tested six waters against one roast. Soft water muted the "
            "acidity; the mineral-heavy one turned chocolate into celery. "
            "Start with the water, and the beans stop being a lottery.",
            4 * 24,
        ),
    ],
    "tomas@example.com": [
        (
            "Border lines that were drawn in a single afternoon",
            "Some of the world's straightest borders were settled over one "
            "table, one bottle, and one ruler. The consequences outlasted "
            "all three.",
            "## Border lines that were drawn in a single afternoon\n\n"
            "Some of the world's straightest borders were settled over one "
            "table, one bottle, and one ruler.\n\n"
            "A ruler on a map is a promise someone else has to keep — "
            "usually in desert, without water. This essay walks three such "
            "lines and the towns that live on the wrong side of a pencil "
            "stroke.",
            5 * 24 + 12,
        ),
        (
            "The map that refused to be wrong",
            "For sixty years, one survey chart kept being reprinted with the "
            "same island on it. The island did not exist.",
            "## The map that refused to be wrong\n\n"
            "For sixty years, one survey chart kept being reprinted with the "
            "same island on it. The island did not exist.\n\n"
            "Sandy Island was 'discovered' in 1876 and 'undiscovered' in "
            "2012 — but the funny part is the middle: decades of cartographers "
            "copying each other rather than going to look. A parable about "
            "citations, and how error compounds politely.",
            9 * 24,
        ),
    ],
    "ingrid@example.com": [
        (
            "Fermentation is just patience with a lid on it",
            "My grandmother made sauerkraut in a bucket; I make it in a jar "
            "with an airlock. Same microbe, same trick: salt, time, silence.",
            "## Fermentation is just patience with a lid on it\n\n"
            "My grandmother made sauerkraut in a bucket; I make it in a jar "
            "with an airlock. Same microbe, same trick: salt, time, silence.\n\n"
            "This week: a 2.5% brine, a dark cupboard, and the discipline to "
            "not open it for ten days. The payoff is crunch you cannot buy "
            "and a fridge that smells like victory.",
            26,
        ),
    ],
    "sam@example.com": [
        (
            "What we lost when we stopped printing corrections",
            "A printed error is permanent, so newspapers printed corrections "
            "prominently. A digital edit leaves no scar — and we edit like it.",
            "## What we lost when we stopped printing corrections\n\n"
            "A printed error is permanent, so newspapers printed corrections "
            "prominently. A digital edit leaves no scar — and we edit like it.\n\n"
            "The correction box was a daily institution of humility: set in "
            "type, paid for in ink. This essay argues for the return of "
            "'edited at' stamps, and what honest versioning could look like "
            "on the web.",
            12 * 24,
        ),
    ],
}

# (title, preview, subscriber content) — kept out of the reader feed
DRAFT = {
    "mara@example.com": (
        "Winter hedgerows (draft)",
        "Notes toward a January walk — holly, haw, and the geometry of bare fields.",
        "Draft notes. Probably three sections: holly as boundary marker, "
        "the hawthorn's folklore debt, and what a bare field reveals about slope.",
    ),
    "dev@example.com": (
        "Postmortem template (draft)",
        "The five-question postmortem we actually fill in — blameless, short, boring.",
        "Draft. Five questions, one page, no action-item theater.",
    ),
}

# title, preview, subscriber content, hours from now
SCHEDULED = {
    "june@example.com": (
        "Cupping notes: three Kenyas, one table",
        "This Thursday's cupping: three Kenyan lots side by side. Notes go out "
        "with the full scorecard.",
        "Full cupping scorecard and tasting notes for the three-lot Kenya "
        "comparison, plus the roast curves behind each.",
    ),
}


AVATAR_COLORS = [
    ("#0f766e", "#ccfbf1"),
    ("#7c3aed", "#ede9fe"),
    ("#b45309", "#fef3c7"),
    ("#1d4ed8", "#dbeafe"),
    ("#be185d", "#fce7f3"),
    ("#4d7c0f", "#ecfccb"),
]


def _avatar_svg(initials: str, idx: int) -> str:
    """Round initials avatar as inline SVG (offline fallback, no Pillow)."""
    bg, fg = AVATAR_COLORS[idx % len(AVATAR_COLORS)]
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        f'<circle cx="32" cy="32" r="32" fill="{bg}"/>'
        f'<text x="32" y="40" font-family="Georgia, serif" font-size="26" '
        f'font-weight="bold" text-anchor="middle" fill="{fg}">{initials}</text>'
        "</svg>"
    )


def _fake_person_avatar(slug: str, idx: int) -> bytes | None:
    """Download an illustrated 'fake person' avatar (DiceBear), or None offline.

    Deterministic per slug: same seed -> same face. Not a real photo.
    """
    import urllib.request

    bg = AVATAR_COLORS[idx % len(AVATAR_COLORS)][0].lstrip("#")
    url = (
        "https://api.dicebear.com/9.x/avataaars/svg"
        f"?seed={slug}&backgroundColor={bg}"
    )
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            if resp.status == 200:
                return resp.read()
    except Exception:  # noqa: BLE001 - offline dev machines fall back to initials
        return None
    return None


def _write_avatar(slug: str, initials: str, idx: int) -> str:
    """Write an avatar next to uploaded ones; returns its public URL.

    Prefers a downloaded illustrated persona; falls back to a generated
    initials SVG when there is no network.
    """
    directory = Path(upload_dir())
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{slug}.svg"

    data = _fake_person_avatar(slug, idx)
    if data:
        path.write_bytes(data)
    else:
        path.write_text(_avatar_svg(initials, idx))
    return f"/uploads/avatars/{slug}.svg"


def refresh_avatars() -> None:
    """Regenerate avatar files and avatar_url for the seeded users."""
    start_identity_mappers()
    email_color = {w[2]: w[3] for w in WRITERS}
    email_color.update({r[2]: len(WRITERS) + i for i, r in enumerate(READERS)})
    with SqlAlchemyUnitOfWork() as uow:
        repo = SqlAlchemyUserRepository(uow.session)
        for email, idx in email_color.items():
            user = repo.get_by_email(email)
            if user is None:
                continue
            slug = email.split("@")[0]
            initials = "".join(part[0] for part in (user.first_name, user.last_name) if part)
            user.avatar_url = _write_avatar(slug, initials, idx)
        uow.commit()
    print("Avatars refreshed.")


def seed() -> None:
    """Seed development database with test data."""
    print("Creating tables...")
    start_identity_mappers()
    start_sub_mappers()
    start_pub_mappers()
    with SqlAlchemyUnitOfWork() as uow:
        create_identity_tables(uow.session.bind)
        create_sub_tables(uow.session.bind)
        create_pub_tables(uow.session.bind)
        uow.commit()

    with SqlAlchemyUnitOfWork() as uow:
        if SqlAlchemyUserRepository(uow.session).get_by_email("reader1@example.com"):
            print("Already seeded — nothing to do.")
            return

    users: dict[str, User] = {}

    print("Seeding users...")
    with SqlAlchemyUnitOfWork() as uow:
        # Writers (roles inferred the same way production would: posting first
        # grants WRITER; we add roles directly because the seed bypasses the API)
        for i, (first, last, email, idx) in enumerate(WRITERS):
            initials = f"{first[0]}{last[0]}"
            user = User.register(
                email=email,
                password_hash=User.hash_password(PASSWORD),
                first_name=first,
                last_name=last,
            )
            user.avatar_url = _write_avatar(email.split("@")[0], initials, idx)
            users[email] = user

        for w in WRITERS:
            users[w[2]].add_role(UserRole.WRITER)
            users[w[2]].add_role(UserRole.READER)
        for first, last, email in READERS:
            user = User.register(
                email=email,
                password_hash=User.hash_password(PASSWORD),
                first_name=first,
                last_name=last,
            )
            user.add_role(UserRole.READER)
            users[email] = user

        uow.session.add_all(users.values())
        uow.commit()
        print(f"Created {len(users)} users (avatars written to {upload_dir()})")

    print("Seeding subscriptions, allocations, followers...")
    with SqlAlchemyUnitOfWork() as uow:
        for reader_email, writer_emails in ALLOCATIONS.items():
            sub = Subscription.create(
                reader_id=users[reader_email].id,
                external_subscription_id=f"sub_mock_{reader_email.split('@')[0]}",
                status=SubscriptionStatus.ACTIVE,
            )
            for writer_email in writer_emails:
                sub.allocate_writer(users[writer_email].id)
            uow.session.add(sub)
            uow.session.flush()  # subscription row must exist before projections
            for writer_email in writer_emails:
                # Project the read models (command handlers don't publish via bus)
                _upsert_subscriber(
                    uow.session,
                    users[writer_email].id,
                    users[reader_email].id,
                    sub.id,
                    datetime.utcnow(),
                )

        for reader_email, writer_emails in FOLLOWS.items():
            for writer_email in writer_emails:
                _insert_follower_ignore(
                    uow.session,
                    users[writer_email].id,
                    users[reader_email].id,
                    datetime.utcnow(),
                )
        uow.commit()
        print("Created subscriptions, allocations and followers")

    print("Seeding posts...")
    now = datetime.utcnow()
    created = 0
    with SqlAlchemyUnitOfWork() as uow:
        for writer_email, posts in POSTS.items():
            writer = users[writer_email]
            for title, preview, full, hours_ago in posts:
                post = Post.create_draft(
                    writer_id=writer.id,
                    title=title,
                    preview_content=preview,
                    subscriber_content=full,
                )
                post.publish()
                # Stagger publish dates so the feed looks lived-in
                post.published_at = now - timedelta(hours=hours_ago)
                post.updated_at = post.published_at
                uow.session.add(post)
                created += 1

        for writer_email, (title, preview, full) in DRAFT.items():
            uow.session.add(
                Post.create_draft(
                    writer_id=users[writer_email].id,
                    title=title,
                    preview_content=preview,
                    subscriber_content=full,
                )
            )
            created += 1

        for writer_email, (title, preview, full) in SCHEDULED.items():
            uow.session.add(
                Post.create_scheduled(
                    writer_id=users[writer_email].id,
                    title=title,
                    preview_content=preview,
                    subscriber_content=full,
                    scheduled_for=now + timedelta(hours=2),
                )
            )
            created += 1
        uow.commit()
        print(f"Created {created} posts")

    print("\nSeed complete!")
    print("\nTest accounts (all passwords: password123):")
    print("  Writers:  mara@, dev@, june@, tomas@, ingrid@, sam@example.com")
    print("  Readers:  reader1@, reader2@, reader3@example.com")


if __name__ == "__main__":
    import sys

    if "--avatars-only" in sys.argv:
        refresh_avatars()
    else:
        seed()
