from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from city_simulator.domain.enums import ScenarioStatus
from city_simulator.infrastructure.database import Base


class ScenarioModel(Base):
    __tablename__ = "scenarios"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ScenarioStatus.DRAFT.value,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    budget_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    decisions: Mapped[list["ScenarioDecisionModel"]] = relationship(
        back_populates="scenario",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ScenarioDecisionModel.measure_id",
    )
    results: Mapped[list["SimulationResultModel"]] = relationship(
        back_populates="scenario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ScenarioDecisionModel(Base):
    __tablename__ = "scenario_decisions"

    scenario_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("scenarios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    measure_id: Mapped[str] = mapped_column(String(8), primary_key=True)
    district_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    scenario: Mapped[ScenarioModel] = relationship(back_populates="decisions")


class SimulationResultModel(Base):
    __tablename__ = "simulation_results"
    __table_args__ = (
        UniqueConstraint("scenario_id", "scenario_version", name="uq_result_scenario_version"),
        Index("ix_results_score_after", "score_after"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    scenario_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_version: Mapped[int] = mapped_column(Integer, nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False)
    formula_version: Mapped[str] = mapped_column(String(32), nullable=False)
    total_cost: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_budget: Mapped[int] = mapped_column(Integer, nullable=False)
    score_before: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    score_after: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    score_delta: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    scenario: Mapped[ScenarioModel] = relationship(back_populates="results")
