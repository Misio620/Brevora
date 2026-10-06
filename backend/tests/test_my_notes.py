"""Personal notes: private to their author, limited to 5,000 characters (docs/decisions.md §7)."""
from tests.conftest import auth_header, make_user, make_videos


def ids(feed: dict) -> list[str]:
    return sorted(v["youtube_id"] for v in feed["videos"])


async def test_note_is_saved_and_only_its_author_sees_it(client):
    a, b = await make_user("a@example.com"), await make_user("b@example.com")
    await make_videos(1, users=[a, b])

    await client.patch("/videos/vid0/metadata", headers=auth_header(a), json={"note": "我的心得"})

    assert (await client.get("/videos/vid0", headers=auth_header(a))).json()["note"] == "我的心得"
    assert (await client.get("/videos/vid0", headers=auth_header(b))).json()["note"] == ""


async def test_length_limit_is_5000_characters(client):
    user = await make_user()
    await make_videos(1, users=[user])

    ok = await client.patch("/videos/vid0/metadata", headers=auth_header(user), json={"note": "字" * 5000})
    too_long = await client.patch("/videos/vid0/metadata", headers=auth_header(user), json={"note": "字" * 5001})

    assert ok.status_code == 200 and too_long.status_code == 422


async def test_has_note_filter_and_search_only_use_your_own_notes(client):
    a, b = await make_user("a@example.com"), await make_user("b@example.com")
    await make_videos(3, users=[a, b])
    await client.patch("/videos/vid0/metadata", headers=auth_header(a), json={"note": "secret idea"})
    await client.patch("/videos/vid1/metadata", headers=auth_header(a), json={"note": " \n\t "})  # whitespace only

    with_note_a = (await client.get("/videos/feed?has_note=true", headers=auth_header(a))).json()
    with_note_b = (await client.get("/videos/feed?has_note=true", headers=auth_header(b))).json()
    search_a = (await client.get("/videos/feed", params={"search": "secret idea"}, headers=auth_header(a))).json()
    search_b = (await client.get("/videos/feed", params={"search": "secret idea"}, headers=auth_header(b))).json()

    assert ids(with_note_a) == ["vid0"]
    assert ids(with_note_b) == []
    assert ids(search_a) == ["vid0"]
    assert ids(search_b) == []
