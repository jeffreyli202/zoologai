"""add_video_analysis_progress_fields

Revision ID: da8276b85b7c
Revises: 66c68ab396a3
Create Date: 2026-10-23 15:07:48.725921

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "da8276b85b7c"
down_revision: Union[str, Sequence[str], None] = "66c68ab396a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite requires a non-NULL server_default when adding NOT NULL columns.
    with op.batch_alter_table("videos", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "analysis_progress",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(sa.Column("analysis_message", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("analysis_error", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "analysis_frames_total",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column(
                "analysis_frames_done",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column(
                "analysis_ai_calls",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(sa.Column("analysis_started_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("analysis_finished_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("videos", schema=None) as batch_op:
        batch_op.drop_column("analysis_finished_at")
        batch_op.drop_column("analysis_started_at")
        batch_op.drop_column("analysis_ai_calls")
        batch_op.drop_column("analysis_frames_done")
        batch_op.drop_column("analysis_frames_total")
        batch_op.drop_column("analysis_error")
        batch_op.drop_column("analysis_message")
        batch_op.drop_column("analysis_progress")
