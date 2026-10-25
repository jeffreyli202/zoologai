"""hourly journals: hour column + last_journal_hour_at

Revision ID: a1b2c3d4e5f6
Revises: 2c2bab6fc90d
Create Date: 2026-10-23 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "2c2bab6fc90d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("daily_journals", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("hour", sa.Integer(), nullable=False, server_default="-1")
        )
        batch_op.drop_constraint("uq_daily_journals_animal_date", type_="unique")
        batch_op.create_unique_constraint(
            "uq_daily_journals_animal_date_hour",
            ["animal_id", "date", "hour"],
        )

    with op.batch_alter_table("camera_sources", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("last_journal_hour_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("camera_sources", schema=None) as batch_op:
        batch_op.drop_column("last_journal_hour_at")

    with op.batch_alter_table("daily_journals", schema=None) as batch_op:
        batch_op.drop_constraint(
            "uq_daily_journals_animal_date_hour", type_="unique"
        )
        batch_op.create_unique_constraint(
            "uq_daily_journals_animal_date", ["animal_id", "date"]
        )
        batch_op.drop_column("hour")
