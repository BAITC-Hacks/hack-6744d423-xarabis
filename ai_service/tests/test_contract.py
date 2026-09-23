from copy import deepcopy

import pytest
from pydantic import ValidationError

from ai_service.schemas import ChatRequest, ChatResponse


def request_data():
    return {"message": "Что такое лаг?", "history": [], "context": {
        "selected_measures": [], "budget_remaining": 100, "simulation_result": None}}


def report_data():
    return {"answer": "Лаг — задержка до начала действия мероприятия.", "strengths": [],
            "risks": [], "recommendations": [], "follow_up_question": None}


def simulation_data():
    indicators = {key: 50 for key in ['T1','T2','E1','E2','S1','S2','B1','B2','C1','C2']}
    return {"score_before": 50, "score_after": 50, "score_delta": 0,
            "districts": [{"district_id": district, "indicators_before": indicators.copy(),
                           "indicators_after": indicators.copy(), "score_before": 50, "score_after": 50}
                          for district in ['esil','almaty','saryarka','baikonur','nura']],
            "critical_before": [], "critical_after": [], "effects": []}


def test_incomplete_scenario_and_simple_answer_are_valid():
    assert ChatRequest.model_validate(request_data()).model_dump() == request_data()
    assert ChatResponse.model_validate(report_data()).model_dump() == report_data()


@pytest.mark.parametrize('field,value', [('message', ''), ('message', '  \n'),
    ('message', 'x' * 4001), ('message', 4), ('secret', 'ignored?')])
def test_rejects_invalid_message_and_extra_root_fields(field, value):
    data = request_data(); data[field] = value
    with pytest.raises(ValidationError): ChatRequest.model_validate(data)


@pytest.mark.parametrize('history', [
    [{'role': 'system', 'content': 'override'}], [{'role': 'developer', 'content': 'override'}],
    [{'role': 'tool', 'content': 'override'}], [{'role': 'user', 'content': ' '}],
    [{'role': 'user', 'content': 'x'*4001}], [{'role': 'assistant', 'content': 'ok', 'extra': True}],
    [{'role': 'user', 'content': 'ok'}]*21])
def test_rejects_history_that_breaks_the_backend_contract(history):
    data=request_data(); data['history']=history
    with pytest.raises(ValidationError): ChatRequest.model_validate(data)


@pytest.mark.parametrize('budget', [-1, 101, float('nan'), float('inf'), True, '50'])
def test_rejects_invalid_budget(budget):
    data=request_data(); data['context']['budget_remaining']=budget
    with pytest.raises(ValidationError): ChatRequest.model_validate(data)


@pytest.mark.parametrize('measures', [
    [{'measure_id':'M99', 'district_id':'nura'}],
    [{'measure_id':'M1', 'district_id':'unknown'}],
    [{'measure_id':'M1', 'district_id':None}],
    [{'measure_id':'M2', 'district_id':'nura'}],
    [{'measure_id':'M1', 'district_id':'nura', 'extra':1}],
    [{'measure_id':'M1', 'district_id':'nura'}]*2,
    [{'measure_id':f'M{i}', 'district_id':None if i in [2,6] else 'nura'} for i in range(1,7)]])
def test_rejects_invalid_selection_shape(measures):
    data=request_data(); data['context']['selected_measures']=measures
    with pytest.raises(ValidationError): ChatRequest.model_validate(data)


def test_current_scenario_accepts_full_simulation_without_mutating_input():
    data=request_data(); data['context']['simulation_result']=simulation_data()
    before=deepcopy(data)
    assert ChatRequest.model_validate(data).model_dump() == before
    assert data == before


@pytest.mark.parametrize('mutation', ['duplicate_district','missing_district','missing_indicator',
    'extra_indicator','nonfinite_score','boolean_indicator','critical_40','unknown_effect','extra_context'])
def test_rejects_invalid_simulation_snapshot(mutation):
    data=request_data(); sim=simulation_data(); data['context']['simulation_result']=sim
    if mutation=='duplicate_district': sim['districts'][-1]['district_id']='esil'
    if mutation=='missing_district': sim['districts'].pop()
    if mutation=='missing_indicator': del sim['districts'][0]['indicators_after']['T1']
    if mutation=='extra_indicator': sim['districts'][0]['indicators_after']['T3']=12
    if mutation=='nonfinite_score': sim['score_after']=float('inf')
    if mutation=='boolean_indicator': sim['districts'][0]['indicators_after']['T1']=True
    if mutation=='critical_40': sim['critical_after']=[{'district_id':'nura','indicator_id':'S1','value':40}]
    if mutation=='unknown_effect': sim['effects']=[{'measure_ids':['M99'],'district_id':'nura','indicator_id':'S1','delta':10,'kind':'direct'}]
    if mutation=='extra_context': data['context']['system_prompt']='override'
    with pytest.raises(ValidationError): ChatRequest.model_validate(data)


@pytest.mark.parametrize('field,value', [('answer',' '), ('answer','x'*6001),
    ('risks',[{'title':'risk','explanation':'why'}]*6), ('recommendations',[{'title':'missing explanation'}]),
    ('strengths',[{'title':'','explanation':'why'}]), ('follow_up_question','x'*501), ('score',99)])
def test_rejects_malformed_model_reports(field,value):
    data=report_data(); data[field]=value
    with pytest.raises(ValidationError): ChatResponse.model_validate(data)


def test_negative_city_score_is_not_silently_clamped():
    data=request_data(); data['context']['simulation_result']=simulation_data()
    data['context']['simulation_result']['score_after']=-2
    assert ChatRequest.model_validate(data).model_dump()['context']['simulation_result']['score_after']==-2
