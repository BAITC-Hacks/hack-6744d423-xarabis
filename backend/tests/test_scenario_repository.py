from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from city_simulator.domain.entities import Decision
from city_simulator.domain.exceptions import (
    ScenarioNotFoundError,
    ScenarioVersionConflictError,
)
from city_simulator.domain.services import ScoreCalculator
from city_simulator.infrastructure.database import Base
from city_simulator.infrastructure.scenario_repository import SqlAlchemyScenarioRepository


@pytest.fixture
async def session_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_repository_preserves_result_history_and_invalidates_current(
    session_factory,
    dataset,
    example_decisions,
) -> None:
    async with session_factory() as session:
        repository = SqlAlchemyScenarioRepository(session)
        scenario = await repository.create(budget_limit=dataset.rules.budget)
        assert scenario.version == 1
        assert scenario.decisions == ()

        scenario = await repository.replace_decisions(
            scenario.id,
            expected_version=1,
            decisions=example_decisions,
        )
        assert scenario.version == 2
        assert scenario.decisions == tuple(
            sorted(example_decisions, key=lambda item: item.measure_id)
        )

        calculated = ScoreCalculator().calculate(scenario.decisions, dataset)
        stored = await repository.save_result(
            scenario.id,
            expected_version=2,
            result=calculated,
        )
        assert stored.result.score_after == pytest.approx(56.54307)
        assert (await repository.get_current_result(scenario.id)).id == stored.id
        repeated = await repository.save_result(
            scenario.id,
            expected_version=2,
            result=calculated,
        )
        assert repeated.id == stored.id
        assert (await repository.get(scenario.id)).status.value == "calculated"

        replacement = (
            Decision("M9", "nura"),
            Decision("M11", "esil"),
            Decision("M10", "almaty"),
            Decision("M12"),
            Decision("M4", "saryarka"),
        )
        updated = await repository.replace_decisions(
            scenario.id,
            expected_version=2,
            decisions=replacement,
        )
        assert updated.version == 3
        assert await repository.get_current_result(scenario.id) is None
        history = await repository.list_results(scenario.id)
        assert [item.scenario_version for item in history] == [2]


@pytest.mark.asyncio
async def test_repository_detects_stale_version(session_factory, dataset) -> None:
    async with session_factory() as session:
        repository = SqlAlchemyScenarioRepository(session)
        scenario = await repository.create(budget_limit=dataset.rules.budget)
        await repository.replace_decisions(
            scenario.id,
            expected_version=1,
            decisions=(Decision("M12"),),
        )
        with pytest.raises(ScenarioVersionConflictError):
            await repository.replace_decisions(
                scenario.id,
                expected_version=1,
                decisions=(),
            )


@pytest.mark.asyncio
async def test_repository_distinguishes_missing_scenario(session_factory) -> None:
    async with session_factory() as session:
        repository = SqlAlchemyScenarioRepository(session)
        with pytest.raises(ScenarioNotFoundError):
            await repository.replace_decisions(
                uuid4(),
                expected_version=1,
                decisions=(),
            )
