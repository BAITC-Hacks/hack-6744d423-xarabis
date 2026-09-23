"""Create scenarios, decisions, and simulation results.

Revision ID: 20260923_0001
Revises:
Create Date: 2026-09-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260923_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scenarios",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("budget_limit", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "scenario_decisions",
        sa.Column("scenario_id", sa.Uuid(), nullable=False),
        sa.Column("measure_id", sa.String(length=8), nullable=False),
        sa.Column("district_id", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("scenario_id", "measure_id"),
    )
    op.create_table(
        "simulation_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scenario_id", sa.Uuid(), nullable=False),
        sa.Column("scenario_version", sa.Integer(), nullable=False),
        sa.Column("dataset_version", sa.String(length=32), nullable=False),
        sa.Column("formula_version", sa.String(length=32), nullable=False),
        sa.Column("total_cost", sa.Integer(), nullable=False),
        sa.Column("remaining_budget", sa.Integer(), nullable=False),
        sa.Column("score_before", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("score_after", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("score_delta", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scenario_id",
            "scenario_version",
            name="uq_result_scenario_version",
        ),
    )
    op.create_index(
        "ix_simulation_results_scenario_id",
        "simulation_results",
        ["scenario_id"],
    )
    op.create_index(
        "ix_results_score_after",
        "simulation_results",
        ["score_after"],
    )


def downgrade() -> None:
    op.drop_index("ix_results_score_after", table_name="simulation_results")
    op.drop_index("ix_simulation_results_scenario_id", table_name="simulation_results")
    op.drop_table("simulation_results")
    op.drop_table("scenario_decisions")
    op.drop_table("scenarios")
