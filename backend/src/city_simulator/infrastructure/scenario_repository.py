from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from city_simulator.domain.entities import Decision, ScenarioResult
from city_simulator.domain.enums import ScenarioStatus
from city_simulator.domain.exceptions import (
    ScenarioNotFoundError,
    ScenarioVersionConflictError,
)
from city_simulator.domain.scenario_ports import ScenarioRepository
from city_simulator.domain.scenarios import Scenario, StoredSimulationResult
from city_simulator.infrastructure.models import (
    ChatConversationModel,
    ChatMessageModel,
    ScenarioDecisionModel,
    ScenarioModel,
    SimulationResultModel,
)
from city_simulator.infrastructure.result_codec import payload_to_result, result_to_payload


class SqlAlchemyScenarioRepository(ScenarioRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, budget_limit: int) -> Scenario:
        model = ScenarioModel(budget_limit=budget_limit)
        self._session.add(model)
        await self._session.commit()
        return await self._get_required(model.id)

    async def get(self, scenario_id: UUID) -> Scenario | None:
        statement = (
            select(ScenarioModel)
            .options(selectinload(ScenarioModel.decisions))
            .where(ScenarioModel.id == scenario_id)
        )
        model = await self._session.scalar(statement)
        return self._to_scenario(model) if model else None

    async def list(self, *, limit: int, offset: int) -> Sequence[Scenario]:
        statement = (
            select(ScenarioModel)
            .options(selectinload(ScenarioModel.decisions))
            .order_by(ScenarioModel.updated_at.desc(), ScenarioModel.id.desc())
            .limit(limit)
            .offset(offset)
        )
        models = (await self._session.scalars(statement)).all()
        return tuple(self._to_scenario(model) for model in models)

    async def count(self) -> int:
        return int(
            await self._session.scalar(select(func.count()).select_from(ScenarioModel)) or 0
        )

    async def replace_decisions(
        self,
        scenario_id: UUID,
        *,
        expected_version: int,
        decisions: Sequence[Decision],
    ) -> Scenario:
        statement = (
            update(ScenarioModel)
            .where(
                ScenarioModel.id == scenario_id,
                ScenarioModel.version == expected_version,
            )
            .values(
                version=ScenarioModel.version + 1,
                status=ScenarioStatus.DRAFT.value,
            )
        )
        result = await self._session.execute(statement)
        if result.rowcount != 1:
            await self._session.rollback()
            await self._raise_missing_or_conflict(
                scenario_id,
                expected_version=expected_version,
            )

        await self._session.execute(
            delete(ScenarioDecisionModel).where(ScenarioDecisionModel.scenario_id == scenario_id)
        )
        self._session.add_all(
            [
                ScenarioDecisionModel(
                    scenario_id=scenario_id,
                    measure_id=item.measure_id.upper(),
                    district_id=item.district_id,
                )
                for item in decisions
            ]
        )
        await self._session.commit()
        return await self._get_required(scenario_id)

    async def save_result(
        self,
        scenario_id: UUID,
        *,
        expected_version: int,
        result: ScenarioResult,
    ) -> StoredSimulationResult:
        status_update = (
            update(ScenarioModel)
            .where(
                ScenarioModel.id == scenario_id,
                ScenarioModel.version == expected_version,
            )
            .values(status=ScenarioStatus.CALCULATED.value)
        )
        update_result = await self._session.execute(status_update)
        if update_result.rowcount != 1:
            await self._session.rollback()
            await self._raise_missing_or_conflict(
                scenario_id,
                expected_version=expected_version,
            )

        existing = await self._find_result(scenario_id, expected_version)
        if existing is not None:
            await self._session.commit()
            return self._to_stored_result(existing)

        model = SimulationResultModel(
            scenario_id=scenario_id,
            scenario_version=expected_version,
            dataset_version=result.dataset_version,
            formula_version=result.formula_version,
            total_cost=result.total_cost,
            remaining_budget=result.remaining_budget,
            score_before=Decimal(str(result.score_before)),
            score_after=Decimal(str(result.score_after)),
            score_delta=Decimal(str(result.score_delta)),
            payload=result_to_payload(result),
        )
        self._session.add(model)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            existing = await self._find_result(scenario_id, expected_version)
            if existing is None:
                raise
            return self._to_stored_result(existing)
        await self._session.refresh(model)
        return self._to_stored_result(model)

    async def get_current_result(self, scenario_id: UUID) -> StoredSimulationResult | None:
        statement = (
            select(SimulationResultModel)
            .join(ScenarioModel, ScenarioModel.id == SimulationResultModel.scenario_id)
            .where(
                SimulationResultModel.scenario_id == scenario_id,
                SimulationResultModel.scenario_version == ScenarioModel.version,
            )
        )
        model = await self._session.scalar(statement)
        return self._to_stored_result(model) if model else None

    async def list_results(self, scenario_id: UUID) -> Sequence[StoredSimulationResult]:
        statement = (
            select(SimulationResultModel)
            .where(SimulationResultModel.scenario_id == scenario_id)
            .order_by(SimulationResultModel.scenario_version.desc())
        )
        models = (await self._session.scalars(statement)).all()
        return tuple(self._to_stored_result(model) for model in models)

    async def delete(self, scenario_id: UUID, *, expected_version: int) -> None:
        statement = delete(ScenarioModel).where(
            ScenarioModel.id == scenario_id,
            ScenarioModel.version == expected_version,
        )
        result = await self._session.execute(statement)
        if result.rowcount != 1:
            await self._session.rollback()
            await self._raise_missing_or_conflict(
                scenario_id,
                expected_version=expected_version,
            )
        # PostgreSQL applies the FK cascades. Explicit child cleanup keeps the
        # repository correct for the local SQLite fallback where FK enforcement
        # may be disabled by the driver.
        await self._session.execute(
            delete(ScenarioDecisionModel).where(
                ScenarioDecisionModel.scenario_id == scenario_id
            )
        )
        await self._session.execute(
            delete(SimulationResultModel).where(
                SimulationResultModel.scenario_id == scenario_id
            )
        )
        conversation_ids = select(ChatConversationModel.id).where(
            ChatConversationModel.scenario_id == scenario_id
        )
        await self._session.execute(
            delete(ChatMessageModel).where(
                ChatMessageModel.conversation_id.in_(conversation_ids)
            )
        )
        await self._session.execute(
            delete(ChatConversationModel).where(
                ChatConversationModel.scenario_id == scenario_id
            )
        )
        await self._session.commit()

    async def _get_required(self, scenario_id: UUID) -> Scenario:
        scenario = await self.get(scenario_id)
        if scenario is None:
            raise ScenarioNotFoundError(scenario_id)
        return scenario

    async def _raise_missing_or_conflict(
        self,
        scenario_id: UUID,
        *,
        expected_version: int,
    ) -> None:
        current_version = await self._session.scalar(
            select(ScenarioModel.version).where(ScenarioModel.id == scenario_id)
        )
        if current_version is None:
            raise ScenarioNotFoundError(scenario_id)
        raise ScenarioVersionConflictError(
            scenario_id,
            expected_version=expected_version,
            current_version=current_version,
        )

    async def _find_result(
        self,
        scenario_id: UUID,
        scenario_version: int,
    ) -> SimulationResultModel | None:
        return await self._session.scalar(
            select(SimulationResultModel).where(
                SimulationResultModel.scenario_id == scenario_id,
                SimulationResultModel.scenario_version == scenario_version,
            )
        )

    @staticmethod
    def _to_scenario(model: ScenarioModel) -> Scenario:
        return Scenario(
            id=model.id,
            status=ScenarioStatus(model.status),
            version=model.version,
            budget_limit=model.budget_limit,
            decisions=tuple(
                Decision(item.measure_id, item.district_id) for item in model.decisions
            ),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _to_stored_result(model: SimulationResultModel) -> StoredSimulationResult:
        return StoredSimulationResult(
            id=model.id,
            scenario_id=model.scenario_id,
            scenario_version=model.scenario_version,
            result=payload_to_result(model.payload),
            created_at=model.created_at,
        )
