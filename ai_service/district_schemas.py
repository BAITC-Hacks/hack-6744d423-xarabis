"""Additive v2 snapshot contract, independent of the v1 city simulation."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .districts import DISTRICT_IMPROVEMENTS
from .schemas import (ContractModel, DistrictId, HistoryMessage, IndicatorValue, MessageText,
                      Number, SandboxDescription, SandboxName, SandboxZoneId)

DistrictImprovementId = Literal['bus', 'signals', 'park', 'filter', 'school', 'repair']


class DistrictValues(ContractModel):
    transport: IndicatorValue
    air: IndicatorValue
    education: IndicatorValue


class SandboxDistrict(ContractModel):
    id: DistrictId
    name: SandboxName
    description: SandboxDescription
    score: IndicatorValue
    values: DistrictValues
    built: Annotated[list[DistrictImprovementId], Field(max_length=6)]

    @model_validator(mode='after')
    def require_unique_built(self):
        if len(set(self.built)) != len(self.built):
            raise ValueError('Built improvement IDs must be unique within each district')
        return self


class DistrictImprovement(ContractModel):
    id: DistrictImprovementId
    name: SandboxName
    description: SandboxDescription
    cost: Annotated[Number, Field(ge=0, le=500)]
    zone_id: SandboxZoneId
    gain: IndicatorValue

    @model_validator(mode='after')
    def require_fixed_rules(self):
        reference = DISTRICT_IMPROVEMENTS[self.id]
        if any(getattr(self, field) != reference[field] for field in ('cost', 'zone_id', 'gain')):
            raise ValueError('Improvement must match the fixed districts-v2 rules')
        return self


class DistrictSelection(ContractModel):
    district_id: DistrictId
    improvement_id: DistrictImprovementId


class DistrictChange(ContractModel):
    district_id: DistrictId
    indicator_id: SandboxZoneId
    before: IndicatorValue
    after: IndicatorValue


class SandboxV2Context(ContractModel):
    rules_version: Literal['districts-v2']
    city_name: Literal['Новый Берег']
    quarter: Annotated[int, Field(ge=1, le=13)]
    budget: Annotated[Number, Field(ge=0, le=500)]
    score: IndicatorValue
    districts: Annotated[list[SandboxDistrict], Field(min_length=5, max_length=5)]
    selected_district_id: DistrictId
    selected_improvements: Annotated[list[DistrictSelection], Field(max_length=3)]
    available_improvements: Annotated[list[DistrictImprovement], Field(max_length=6)]
    last_changes: Annotated[list[DistrictChange], Field(max_length=15)]

    @model_validator(mode='after')
    def require_consistent_entries(self):
        groups = [
            [district.id for district in self.districts],
            [improvement.id for improvement in self.available_improvements],
            [(item.district_id, item.improvement_id) for item in self.selected_improvements],
            [(item.district_id, item.indicator_id) for item in self.last_changes],
        ]
        if any(len(set(group)) != len(group) for group in groups):
            raise ValueError('Districts, catalogue IDs, plan pairs and change pairs must be unique')
        built = {district.id: set(district.built) for district in self.districts}
        available = {item.id for item in self.available_improvements}
        for selected in self.selected_improvements:
            if selected.improvement_id not in available or selected.improvement_id in built[selected.district_id]:
                raise ValueError('Planned project must be available and unbuilt in its target district')
        return self


class SandboxV2ChatRequest(ContractModel):
    message: MessageText
    history: Annotated[list[HistoryMessage], Field(max_length=20)]
    context: SandboxV2Context
