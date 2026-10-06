"""The migration that moved AI notes to videos keeps existing data (docs/decisions.md §4).

Runs on its own database so it can move the schema up and down freely.
"""
import asyncpg
import pytest

from tests.conftest import TEST_DATABASE_URL, run_alembic

MIGRATION_DB = "brevora_test_migrations"
DSN = TEST_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
ADMIN_DSN = DSN.rsplit("/", 1)[0] + "/postgres"
MIGRATION_DSN = DSN.rsplit("/", 1)[0] + f"/{MIGRATION_DB}"
MIGRATION_URL = TEST_DATABASE_URL.rsplit("/", 1)[0] + f"/{MIGRATION_DB}"

BEFORE = "05b09cb0a09e"  # notes stored per user
AFTER = "7c3e1a9d2b4f"  # notes stored per video

SEED = """
INSERT INTO users (id, google_id, email, created_at, updated_at) VALUES
 ('11111111-1111-1111-1111-111111111111', 'g1', 'a@x.com', now(), now()),
 ('22222222-2222-2222-2222-222222222222', 'g2', 'b@x.com', now(), now());
INSERT INTO videos (id, youtube_id, channel_id, title, fetched_at) VALUES
 ('aaaaaaaa-0000-0000-0000-000000000001', 'vid1', 'ch', 'V1', now()),
 ('aaaaaaaa-0000-0000-0000-000000000002', 'vid2', 'ch', 'V2', now()),
 ('aaaaaaaa-0000-0000-0000-000000000003', 'vid3', 'ch', 'V3', now());
INSERT INTO user_videos (id, user_id, video_id, is_read, is_favorite, note, processing_status,
                         summary, translated_title, processed_at, created_at, updated_at) VALUES
 (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'aaaaaaaa-0000-0000-0000-000000000001',
  true, true, 'my note', 'done', 'OLD note v1', '舊標題', now() - interval '2 days', now(), now()),
 (gen_random_uuid(), '22222222-2222-2222-2222-222222222222', 'aaaaaaaa-0000-0000-0000-000000000001',
  false, false, '', 'done', 'NEW note v1', '新標題', now() - interval '1 day', now(), now()),
 (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'aaaaaaaa-0000-0000-0000-000000000002',
  false, false, '', 'error', NULL, NULL, NULL, now(), now()),
 (gen_random_uuid(), '22222222-2222-2222-2222-222222222222', 'aaaaaaaa-0000-0000-0000-000000000002',
  false, true, '', 'done', 'note v2', NULL, now(), now(), now()),
 (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'aaaaaaaa-0000-0000-0000-000000000003',
  false, false, '', 'processing', NULL, NULL, NULL, now(), now());
"""


@pytest.fixture
async def seeded_db():
    admin = await asyncpg.connect(ADMIN_DSN)
    await admin.execute(f"DROP DATABASE IF EXISTS {MIGRATION_DB}")
    await admin.execute(f"CREATE DATABASE {MIGRATION_DB}")
    await admin.close()
    run_alembic("upgrade", BEFORE, database_url=MIGRATION_URL)
    conn = await asyncpg.connect(MIGRATION_DSN)
    await conn.execute(SEED)
    yield conn
    await conn.close()


async def notes_on_videos(conn):
    rows = await conn.fetch("SELECT youtube_id, processing_status, summary, translated_title FROM videos ORDER BY youtube_id")
    return [tuple(r) for r in rows]


async def test_upgrade_keeps_the_latest_finished_note_per_video(seeded_db):
    run_alembic("upgrade", AFTER, database_url=MIGRATION_URL)

    assert await notes_on_videos(seeded_db) == [
        ("vid1", "done", "NEW note v1", "新標題"),  # latest of two finished notes
        ("vid2", "done", "note v2", None),  # a finished note wins over another user's error
        ("vid3", "pending", None, None),  # a stuck job is reset
    ]
    personal = await seeded_db.fetch(
        "SELECT u.email, v.youtube_id, uv.is_favorite, uv.note FROM user_videos uv "
        "JOIN users u ON u.id = uv.user_id JOIN videos v ON v.id = uv.video_id "
        "WHERE uv.is_favorite OR uv.note <> '' ORDER BY 1, 2"
    )
    assert [tuple(r) for r in personal] == [("a@x.com", "vid1", True, "my note"), ("b@x.com", "vid2", True, "")]


async def test_downgrade_gives_every_user_their_note_back_and_upgrade_again_works(seeded_db):
    run_alembic("upgrade", AFTER, database_url=MIGRATION_URL)
    run_alembic("downgrade", BEFORE, database_url=MIGRATION_URL)

    rows = await seeded_db.fetch(
        "SELECT u.email, v.youtube_id, uv.processing_status, uv.summary FROM user_videos uv "
        "JOIN users u ON u.id = uv.user_id JOIN videos v ON v.id = uv.video_id ORDER BY 1, 2"
    )
    assert [tuple(r) for r in rows] == [
        ("a@x.com", "vid1", "done", "NEW note v1"),
        ("a@x.com", "vid2", "done", "note v2"),
        ("a@x.com", "vid3", "pending", None),
        ("b@x.com", "vid1", "done", "NEW note v1"),
        ("b@x.com", "vid2", "done", "note v2"),
    ]

    run_alembic("upgrade", "head", database_url=MIGRATION_URL)
    assert (await notes_on_videos(seeded_db))[0] == ("vid1", "done", "NEW note v1", "新標題")
