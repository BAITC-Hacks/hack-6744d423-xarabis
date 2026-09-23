import json

from ai_service.knowledge import build_input, load_knowledge
from ai_service.schemas import ChatRequest
from ai_service.tests.test_contract import request_data


def test_reference_contains_actual_catalogue_and_baseline_not_demo_geometry():
    knowledge = load_knowledge()
    assert len(knowledge.get('districts', [])) == 5
    assert len(knowledge['measures']) == 14
    nura = next(row for row in knowledge['districts'] if row['id'] == 'nura')
    assert nura['indicators']['S1'] == 38
    assert nura['indicators']['S2'] == 35
    school = next(row for row in knowledge['measures'] if row['id'] == 'M7')
    assert (school['cost'], school['lag_quarters'], school['effects']) == (24, 3, {'S1': 16})
    crossing = next(row for row in knowledge['measures'] if row['id'] == 'M11')
    assert crossing['effects']['T1'] == -2


def test_model_input_keeps_history_order_and_separates_latest_state():
    data = request_data()
    data['history'] = [{'role': 'user', 'content': 'Я построил школу'},
                       {'role': 'assistant', 'content': 'Обсудим школу'}]
    data['message'] = 'Теперь я отменил школу'
    messages = build_input(ChatRequest.model_validate(data))
    assert len(messages) == 4
    assert messages[0]['role'] == 'developer'
    assert json.loads(messages[0]['content'])['current_scenario']['selected_measures'] == []
    assert messages[1:3] == data['history']
    assert messages[-1] == {'role': 'user', 'content': 'Теперь я отменил школу'}


def test_different_requests_do_not_share_conversation_history():
    first=request_data();first['history']=[{'role':'user','content':'PRIVATE_FIRST_CONVERSATION'}]
    build_input(ChatRequest.model_validate(first))
    second = build_input(ChatRequest.model_validate(request_data()))
    assert len(second) == 2
    assert 'PRIVATE_FIRST_CONVERSATION' not in json.dumps(second)
