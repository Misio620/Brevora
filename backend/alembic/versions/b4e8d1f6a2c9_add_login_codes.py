"""add one-time login codes

The login callback used to redirect to /callback#token=<JWT>. Browsers write that
URL to their global history before the page can erase it, so a 7-day JWT stayed in
Chrome's history. The callback now hands over a 60-second, single-use code instead,
which the frontend exchanges for the JWT. Only the code's hash is stored.

Revision ID: b4e8d1f6a2c9
Revises: 7c3e1a9d2b4f
Create Date: 2026-10-06 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b4e8d1f6a2c9'
down_revision: Union[str, None] = '7c3e1a9d2b4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'login_codes',
        sa.Column('code_hash', sa.String(length=64), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('code_hash'),
    )
    op.create_index('ix_login_codes_expires_at', 'login_codes', ['expires_at'])


def downgrade() -> None:
    op.drop_index('ix_login_codes_expires_at', table_name='login_codes')
    op.drop_table('login_codes')
