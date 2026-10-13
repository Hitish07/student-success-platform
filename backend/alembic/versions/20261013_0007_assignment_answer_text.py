"""Add answer text to assignment submissions.

Revision ID: 20261013_0007
Revises: 20261013_0006
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261013_0007"
down_revision: str | None = "20261013_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("assignment_submissions", sa.Column("answer_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("assignment_submissions", "answer_text")
