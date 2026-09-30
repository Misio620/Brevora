"""move AI notes from user_videos to videos

A note depends only on the video, but it was stored once per user, so every
user who opened a video paid for another Gemini call. Notes now live on the
shared videos row. Existing notes are kept: for each video the most recently
processed one is copied over.

Revision ID: 7c3e1a9d2b4f
Revises: 05b09cb0a09e
Create Date: 2026-09-30 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c3e1a9d2b4f'
down_revision: Union[str, None] = '05b09cb0a09e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NOTE_COLUMNS = ('processing_status', 'summary', 'translated_title', 'error_message', 'processed_at')


def upgrade() -> None:
    op.add_column('videos', sa.Column('processing_status', sa.String(length=20), nullable=False, server_default='pending'))
    op.add_column('videos', sa.Column('processing_started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('videos', sa.Column('summary', sa.Text(), nullable=True))
    op.add_column('videos', sa.Column('translated_title', sa.Text(), nullable=True))
    op.add_column('videos', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('videos', sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('videos', sa.Column('summary_model', sa.String(length=100), nullable=True))
    op.add_column('videos', sa.Column('summary_chapters', sa.Integer(), nullable=True))
    op.add_column('videos', sa.Column('summary_prompt_version', sa.String(length=20), nullable=True))

    # Keep existing notes: the latest finished note per video wins
    op.execute("""
        UPDATE videos v
        SET processing_status = 'done',
            summary = uv.summary,
            translated_title = uv.translated_title,
            processed_at = uv.processed_at
        FROM (
            SELECT DISTINCT ON (video_id) video_id, summary, translated_title, processed_at
            FROM user_videos
            WHERE processing_status = 'done' AND summary IS NOT NULL
            ORDER BY video_id, processed_at DESC NULLS LAST, updated_at DESC
        ) uv
        WHERE v.id = uv.video_id
    """)
    # In-flight or failed jobs are not carried over: they were per user, and the
    # video can simply be processed again

    for column in NOTE_COLUMNS:
        op.drop_column('user_videos', column)


def downgrade() -> None:
    op.add_column('user_videos', sa.Column('processing_status', sa.String(length=20), nullable=False, server_default='pending'))
    op.add_column('user_videos', sa.Column('summary', sa.Text(), nullable=True))
    op.add_column('user_videos', sa.Column('translated_title', sa.Text(), nullable=True))
    op.add_column('user_videos', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('user_videos', sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True))

    # Give every user who has the video a copy of its note
    op.execute("""
        UPDATE user_videos uv
        SET processing_status = 'done',
            summary = v.summary,
            translated_title = v.translated_title,
            processed_at = v.processed_at
        FROM videos v
        WHERE uv.video_id = v.id AND v.processing_status = 'done'
    """)
    op.alter_column('user_videos', 'processing_status', server_default=None)

    for column in ('processing_status', 'processing_started_at', 'summary', 'translated_title', 'error_message',
                   'processed_at', 'summary_model', 'summary_chapters', 'summary_prompt_version'):
        op.drop_column('videos', column)
