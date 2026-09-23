"""The backend/consultant contract. No simulation arithmetic lives here."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

DistrictId = Literal['esil', 'almaty', 'saryarka', 'baikonur', 'nura']
IndicatorId = Literal['T1', 'T2', 'E1', 'E2', 'S1', 'S2', 'B1', 'B2', 'C1', 'C2']
MeasureId = Literal['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9', 'M10', 'M11', 'M12', 'M13', 'M14']
Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]
IndicatorValue = Annotated[Number, Field(ge=0, le=100)]
MessageText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
CITY_MEASURES = frozenset({'M2', 'M6', 'M12', 'M14'})


class ContractModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, str_strip_whitespace=True)


class HistoryMessage(ContractModel):
    role: Literal['user', 'assistant']
    content: MessageText


class SelectedMeasure(ContractModel):
    measure_id: MeasureId
    district_id: DistrictId | None

    @model_validator(mode='after')
    def require_matching_target(self):
        if (self.measure_id in CITY_MEASURES) != (self.district_id is None):
            raise ValueError('City measures require null district; local measures require a district')
        return self


class Indicators(ContractModel):
    T1: IndicatorValue
    T2: IndicatorValue
    E1: IndicatorValue
    E2: IndicatorValue
    S1: IndicatorValue
    S2: IndicatorValue
    B1: IndicatorValue
    B2: IndicatorValue
    C1: IndicatorValue
    C2: IndicatorValue


class DistrictResult(ContractModel):
    district_id: DistrictId
    indicators_before: Indicators
    indicators_after: Indicators
    score_before: IndicatorValue
    score_after: IndicatorValue


class CriticalIndicator(ContractModel):
    district_id: DistrictId
    indicator_id: IndicatorId
    value: Annotated[Number, Field(ge=0, lt=40)]


class AppliedEffect(ContractModel):
    measure_ids: Annotated[list[MeasureId], Field(min_length=1, max_length=2)]
    district_id: DistrictId
    indicator_id: IndicatorId
    delta: Number
    kind: Literal['direct', 'synergy']

    @model_validator(mode='after')
    def require_effect_sources(self):
        required = 1 if self.kind == 'direct' else 2
        if len(set(self.measure_ids)) != required or len(self.measure_ids) != required:
            raise ValueError('Direct effects have one source; synergies have two distinct sources')
        return self


class SimulationResult(ContractModel):
    score_before: Number
    score_after: Number
    score_delta: Number
    districts: Annotated[list[DistrictResult], Field(min_length=5, max_length=5)]
    critical_before: Annotated[list[CriticalIndicator], Field(max_length=50)]
    critical_after: Annotated[list[CriticalIndicator], Field(max_length=50)]
    effects: Annotated[list[AppliedEffect], Field(max_length=300)]

    @model_validator(mode='after')
    def require_unique_snapshot_entries(self):
        if len({item.district_id for item in self.districts}) != 5:
            raise ValueError('Exactly five distinct districts are required')
        for entries in (self.critical_before, self.critical_after):
            if len({(item.district_id, item.indicator_id) for item in entries}) != len(entries):
                raise ValueError('Critical indicator pairs must be unique')
        return self


class CityContext(ContractModel):
    selected_measures: Annotated[list[SelectedMeasure], Field(max_length=5)]
    budget_remaining: IndicatorValue
    simulation_result: SimulationResult | None

    @model_validator(mode='after')
    def require_unique_measures(self):
        if len({item.measure_id for item in self.selected_measures}) != len(self.selected_measures):
            raise ValueError('Selected measure IDs must be unique')
        return self


class ChatRequest(ContractModel):
    message: MessageText
    history: Annotated[list[HistoryMessage], Field(max_length=20)]
    context: CityContext


class AnalysisBlock(ContractModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    explanation: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1200)]


class ChatResponse(ContractModel):
    answer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=6000)]
    strengths: Annotated[list[AnalysisBlock], Field(max_length=5)]
    risks: Annotated[list[AnalysisBlock], Field(max_length=5)]
    recommendations: Annotated[list[AnalysisBlock], Field(max_length=5)]
    follow_up_question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)] | None


class ErrorDetail(ContractModel):
    code: str
    message: str


class ErrorResponse(ContractModel):
    error: ErrorDetail
