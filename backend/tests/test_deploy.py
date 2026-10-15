"""Settings a hosted deployment needs (Render + Neon, see README)."""
import pytest
from sqlalchemy.engine import make_url

from app.config import Settings


@pytest.mark.parametrize(
    "given, expected",
    [
        # What Neon's dashboard hands out
        (
            "postgresql://user:p%40ss@ep-x.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
            "postgresql+asyncpg://user:p%40ss@ep-x.aws.neon.tech/neondb?ssl=require",
        ),
        ("postgres://user:pw@host:5432/db", "postgresql+asyncpg://user:pw@host:5432/db"),
        # Already in asyncpg form: left alone
        ("postgresql+asyncpg://user:pw@host/db?ssl=require", "postgresql+asyncpg://user:pw@host/db?ssl=require"),
        ("postgresql+asyncpg://localhost:5432/youtube_reader", "postgresql+asyncpg://localhost:5432/youtube_reader"),
    ],
)
def test_database_url_accepts_hosted_postgres_strings(given, expected):
    settings = Settings(DATABASE_URL=given, _env_file=None)
    assert settings.DATABASE_URL == expected
    # The password survives, so the server can still log in
    assert make_url(settings.DATABASE_URL).password == make_url(given).password


def test_asyncpg_accepts_the_converted_url():
    from sqlalchemy.dialects.postgresql.asyncpg import dialect

    url = Settings(
        DATABASE_URL="postgresql://u:pw@h/db?sslmode=require&channel_binding=require", _env_file=None
    ).DATABASE_URL
    _, kwargs = dialect().create_connect_args(make_url(url))
    assert kwargs["ssl"] == "require"
    assert "sslmode" not in kwargs and "channel_binding" not in kwargs
