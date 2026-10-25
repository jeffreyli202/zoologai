"""camera animal optional; multiple animals per capture

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-24 02:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("camera_sources", schema=None) as batch_op:
        batch_op.alter_column(
            "animal_id",
            existing_type=sa.Integer(),
            nullable=True,
        )

    with op.batch_alter_table("observations", schema=None) as batch_op:
        batch_op.drop_constraint(
            "uq_observations_camera_capture_id", type_="unique"
        )
        batch_op.create_unique_constraint(
            "uq_observations_capture_animal",
            ["camera_capture_id", "animal_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("observations", schema=None) as batch_op:
        batch_op.drop_constraint(
            "uq_observations_capture_animal", type_="unique"
        )
        batch_op.create_unique_constraint(
            "uq_observations_camera_capture_id",
            ["camera_capture_id"],
        )

    with op.batch_alter_table("camera_sources", schema=None) as batch_op:
        batch_op.alter_column(
            "animal_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
