"""add_observation_frame_link_and_evidence

Revision ID: 66c68ab396a3
Revises: 8ea3e24a7236
Create Date: 2026-10-23 14:42:50.964416

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "66c68ab396a3"
down_revision: Union[str, Sequence[str], None] = "8ea3e24a7236"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("observations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("frame_id", sa.Integer(), nullable=False))
        batch_op.add_column(sa.Column("visible_evidence", sa.Text(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_observations_frame_id"), ["frame_id"], unique=False
        )
        batch_op.create_unique_constraint("uq_observations_frame_id", ["frame_id"])
        batch_op.create_foreign_key(
            "fk_observations_frame_id_frames",
            "frames",
            ["frame_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("observations", schema=None) as batch_op:
        batch_op.drop_constraint("fk_observations_frame_id_frames", type_="foreignkey")
        batch_op.drop_constraint("uq_observations_frame_id", type_="unique")
        batch_op.drop_index(batch_op.f("ix_observations_frame_id"))
        batch_op.drop_column("visible_evidence")
        batch_op.drop_column("frame_id")
