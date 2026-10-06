"""AI notes are generated once per video and shared by every user (docs/decisions.md §4)."""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.database import async_session
from app.models.video import Video
from app.routers import videos as videos_router
from app.services import ai
from tests.conftest import auth_header, make_user, make_videos


async def set_video(youtube_id: str, **values):
    async with async_session() as db:
        await db.execute(update(Video).where(Video.youtube_id == youtube_id).values(**values))
        await db.commit()


async def test_note_made_for_one_user_is_served_to_others(client, fake_ai, fake_chapters):
    a, b = await make_user("a@example.com"), await make_user("b@example.com")
    await make_videos(1, users=[a, b])

    r = await client.post("/videos/vid0/process", headers=auth_header(a))
    assert r.status_code == 202 and r.json()["status"] == "processing"

    note = (await client.get("/videos/vid0", headers=auth_header(b))).json()
    assert note["processing_status"] == "done"
    assert "note for vid0" in note["summary"]
    assert note["translated_title"] == "譯：Title 0"

    again = await client.post("/videos/vid0/process", headers=auth_header(b))
    assert again.json()["status"] == "done"
    assert fake_ai.calls == ["vid0"]


async def test_concurrent_requests_start_one_gemini_call(client, fake_ai, fake_chapters):
    users = [await make_user(f"u{i}@example.com") for i in range(3)]
    await make_videos(1, users=users)
    fake_ai.delay = 0.3  # keep the first job running while the others arrive

    responses = await asyncio.gather(*(client.post("/videos/vid0/process", headers=auth_header(u)) for u in users))

    assert {r.json()["status"] for r in responses} == {"processing"}
    assert fake_ai.calls == ["vid0"]


async def test_note_records_how_it_was_made(client, fake_ai, fake_chapters):
    user = await make_user()
    await make_videos(1, users=[user])
    await client.post("/videos/vid0/process", headers=auth_header(user))

    async with async_session() as db:
        video = (await db.execute(select(Video))).scalar_one()
    assert (video.summary_model, video.summary_chapters, video.summary_prompt_version) == ("fake-model", 3, ai.PROMPT_VERSION)


async def test_fresh_job_is_left_alone_and_stale_job_is_restarted(client, fake_ai, fake_chapters):
    user = await make_user()
    await make_videos(2, users=[user])
    now = datetime.now(timezone.utc)
    await set_video("vid0", processing_status="processing", processing_started_at=now - timedelta(minutes=1))
    await set_video("vid1", processing_status="processing", processing_started_at=now - timedelta(minutes=20))

    fresh = await client.post("/videos/vid0/process", headers=auth_header(user))
    await client.post("/videos/vid1/process", headers=auth_header(user))

    assert fresh.json()["status"] == "processing"
    assert fake_ai.calls == ["vid1"]


async def test_failed_note_can_be_retried_by_anyone(client, fake_ai, fake_chapters):
    a, b = await make_user("a@example.com"), await make_user("b@example.com")
    await make_videos(1, users=[a, b])
    await set_video("vid0", processing_status="error", error_message="old failure")

    await client.post("/videos/vid0/process", headers=auth_header(b))

    note = (await client.get("/videos/vid0", headers=auth_header(a))).json()
    assert note["processing_status"] == "done" and note["error_message"] is None


async def test_failure_is_shared_with_a_safe_message(client, fake_ai, fake_chapters):
    a, b = await make_user("a@example.com"), await make_user("b@example.com")
    await make_videos(1, users=[a, b])
    fake_ai.fail = RuntimeError("internal detail that must not leak")

    await client.post("/videos/vid0/process", headers=auth_header(a))

    note = (await client.get("/videos/vid0", headers=auth_header(b))).json()
    assert note["processing_status"] == "error"
    assert note["error_message"] == "筆記生成失敗，請稍後再試"


async def test_superseded_run_cannot_overwrite_the_newer_claim(client, fake_ai, fake_chapters):
    user = await make_user()
    [video] = await make_videos(1, users=[user])
    new_claim = datetime.now(timezone.utc)
    await set_video("vid0", processing_status="processing", processing_started_at=new_claim)

    await videos_router._run_ai_processing(
        str(uuid.uuid4()), video.id, "vid0", "Title 0", claimed_at=new_claim - timedelta(minutes=20)
    )

    note = (await client.get("/videos/vid0", headers=auth_header(user))).json()
    assert note["processing_status"] == "processing" and note["summary"] is None


async def test_unknown_video_returns_404(client, fake_ai):
    user = await make_user()
    assert (await client.post("/videos/nope/process", headers=auth_header(user))).status_code == 404


async def test_feed_filters_use_the_shared_note_and_favorites_stay_personal(client, fake_ai, fake_chapters):
    a, b = await make_user("a@example.com"), await make_user("b@example.com")
    await make_videos(3, users=[a, b])
    await client.post("/videos/vid0/process", headers=auth_header(a))
    await client.post("/videos/vid1/process", headers=auth_header(b))
    await client.patch("/videos/vid0/metadata", headers=auth_header(a), json={"is_favorite": True})

    def ids(feed):
        return sorted(v["youtube_id"] for v in feed["videos"])

    done_a = (await client.get("/videos/feed?status=done", headers=auth_header(a))).json()
    done_b = (await client.get("/videos/feed?status=done", headers=auth_header(b))).json()
    pending = (await client.get("/videos/feed?status=pending", headers=auth_header(b))).json()
    assert ids(done_a) == ids(done_b) == ["vid0", "vid1"]
    assert ids(pending) == ["vid2"]

    favorite = {v["youtube_id"]: v["is_favorite"] for v in done_a["videos"]}
    others = {v["youtube_id"]: v["is_favorite"] for v in done_b["videos"]}
    assert favorite["vid0"] is True and others["vid0"] is False


async def test_search_matches_shared_note_and_translated_title(client, fake_ai, fake_chapters):
    user = await make_user()
    await make_videos(2, users=[user])
    await client.post("/videos/vid1/process", headers=auth_header(user))

    by_note = (await client.get("/videos/feed", params={"search": "note for vid1"}, headers=auth_header(user))).json()
    by_title = (await client.get("/videos/feed", params={"search": "譯：Title 1"}, headers=auth_header(user))).json()
    assert [v["youtube_id"] for v in by_note["videos"]] == ["vid1"]
    assert [v["youtube_id"] for v in by_title["videos"]] == ["vid1"]
