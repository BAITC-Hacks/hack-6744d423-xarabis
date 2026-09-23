"""Sandbox boundaries exercise the real SDK with only HTTP transport replaced."""
import asyncio
import json

import httpx
import httpx2
import pytest
from fastapi.testclient import TestClient

from ai_service.app import create_app
from ai_service.config import Settings
from ai_service.tests.test_api import make_app, openai_response
from ai_service.tests.test_contract import request_data, report_data
from ai_service.tests.test_streaming import ByteStream, completed, delta, parse_events


def sandbox_data():
    return {'message': 'Что улучшить в Новом Береге?', 'history': [], 'context': {
        'city_name': 'Новый Берег', 'quarter': 1, 'budget': 100, 'score': 29,
        'zones': [
            {'id': 'transport', 'name': 'Транспорт', 'value': 28, 'description': 'Пробки'},
            {'id': 'air', 'name': 'Воздух', 'value': 34, 'description': 'Мало зелени'},
            {'id': 'education', 'name': 'Образование', 'value': 26, 'description': 'Мало школ'},
        ], 'built': [], 'available_improvements': [
            {'id': 'bus', 'name': 'Автобусы', 'description': 'Новые маршруты',
             'cost': 22, 'zone_id': 'transport', 'gain': 24},
            {'id': 'school', 'name': 'Школа', 'description': 'Новая школа',
             'cost': 32, 'zone_id': 'education', 'gain': 42},
        ], 'last_changes': [],
    }}


@pytest.mark.parametrize('streaming', [False, True])
def test_sandbox_uses_fictional_reference_and_untrusted_snapshot_without_reading_astana(monkeypatch, streaming):
    def forbidden():
        pytest.fail('Sandbox must not load Astana reference')
    monkeypatch.setattr('ai_service.knowledge.load_knowledge', forbidden)
    sent = []
    report = report_data(); report['answer'] = 'Начните с транспорта Нового Берега.'
    upstream = ByteStream([delta(json.dumps(report, ensure_ascii=False)), completed(report)])
    def handler(request):
        sent.append(json.loads(request.content))
        if streaming:
            return httpx2.Response(200, headers={'content-type': 'text/event-stream'}, stream=upstream)
        return httpx2.Response(200, json=openai_response(report))
    payload = sandbox_data()
    payload['history'] = [{'role': 'user', 'content': 'HISTORY_ONLY'}]
    payload['context']['zones'][0]['description'] = 'UNTRUSTED_CONTEXT_MARKER'
    with TestClient(make_app(handler)) as client:
        response = client.post('/sandbox/chat' + ('/stream' if streaming else ''), json=payload)
    assert response.status_code == 200
    if streaming:
        events = parse_events(response.text)
        assert events[-1] == ('complete', report)
        assert ''.join(data['delta'] for name, data in events if name == 'answer_delta') == report['answer']
        assert upstream.closed
    else:
        assert response.json() == report
    assert len(sent) == 1
    body = sent[0]
    assert body['store'] is False
    assert body['input'][-1] == {'role': 'user', 'content': payload['message']}
    trusted = body['instructions'] + json.dumps([m for m in body['input'] if m['role'] == 'developer'], ensure_ascii=False)
    assert 'UNTRUSTED_CONTEXT_MARKER' not in trusted
    assert 'HISTORY_ONLY' not in trusted
    reference = json.loads(body['input'][0]['content'])['sandbox_rules']
    assert reference['city_name'] == 'Новый Берег'
    assert reference['initial_budget'] == 100 and reference['quarter_income'] == 12
    assert reference['max_turns'] == 12 and reference['target'] == 65
    assert reference['initial_values'] == {'transport': 28, 'air': 34, 'education': 26}
    assert {item['id']: (item['cost'], item['gain']) for item in reference['improvements']} == {
        'bus': (22, 24), 'signals': (16, 18), 'park': (18, 22), 'filter': (26, 30), 'school': (32, 42)}
    snapshot = next(m for m in body['input'] if 'UNTRUSTED_CONTEXT_MARKER' in m['content'])
    assert snapshot['role'] == 'user'
    assert json.loads(snapshot['content'])['sandbox_snapshot'] == {**payload['context'], 'selected_improvements': []}


@pytest.mark.parametrize('selected', [None, [], ['bus'], ['bus', 'school']])
def test_pending_plan_reaches_advisor_without_becoming_built_or_changing_score(selected):
    sent = []
    def handler(request):
        sent.append(json.loads(request.content))
        return httpx2.Response(200, json=openai_response())
    payload = sandbox_data()
    if selected is not None:
        payload['context']['selected_improvements'] = selected
    with TestClient(make_app(handler)) as client:
        response = client.post('/sandbox/chat', json=payload)
    assert response.status_code == 200
    messages = sent[0]['input']
    assert json.loads(messages[0]['content'])['sandbox_rules']['max_improvements_per_turn'] == 3
    snapshot = json.loads(messages[-2]['content'])['sandbox_snapshot']
    assert messages[-2]['role'] == 'user'
    assert snapshot['selected_improvements'] == (selected or [])
    assert snapshot['built'] == []
    assert snapshot['score'] == 29 and snapshot['budget'] == 100


@pytest.mark.parametrize('selected', [['bus', 'bus'], ['signals'], ['unknown'], 'bus',
                                      ['bus', 'school', 'park', 'filter']])
def test_invalid_pending_plan_is_rejected_before_provider(selected):
    payload = sandbox_data(); payload['context']['selected_improvements'] = selected
    def forbidden(request):
        pytest.fail('Invalid plans must not reach provider')
    with TestClient(make_app(forbidden)) as client:
        response = client.post('/sandbox/chat', json=payload)
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'invalid_request'


def test_pending_plan_cannot_include_already_built_improvement():
    payload = sandbox_data()
    payload['context']['built'] = ['bus']
    payload['context']['available_improvements'] = payload['context']['available_improvements'][1:]
    payload['context']['selected_improvements'] = ['bus']
    with TestClient(create_app(settings=Settings())) as client:
        response = client.post('/sandbox/chat', json=payload)
    assert response.status_code == 422


@pytest.mark.parametrize('field,value', [
    ('city_name', 'Астана'), ('quarter', 0), ('quarter', 14), ('quarter', True),
    ('budget', -1), ('budget', 245), ('budget', '100'), ('score', 101),
    ('built', ['unknown']), ('built', ['bus', 'bus']), ('zones', []),
])
@pytest.mark.parametrize('path', ['/sandbox/chat', '/sandbox/chat/stream'])
def test_invalid_sandbox_context_never_reaches_provider(field, value, path):
    def forbidden(request):
        pytest.fail('Invalid requests must not reach provider')
    data = sandbox_data(); data['context'][field] = value
    data['message'] = 'DO_NOT_ECHO_SECRET'
    with TestClient(make_app(forbidden)) as client:
        response = client.post(path, json=data)
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'invalid_request'
    assert 'DO_NOT_ECHO_SECRET' not in response.text


@pytest.mark.parametrize('kind', ['duplicate_zone', 'duplicate_upgrade', 'duplicate_change', 'unknown_upgrade',
    'oversize_description', 'wrong_cost', 'wrong_gain', 'wrong_zone', 'built_available_overlap', 'unknown_field', 'system_history'])
def test_nested_sandbox_contract_rejects_ambiguous_or_unbounded_input(kind):
    data = sandbox_data(); context = data['context']
    if kind == 'duplicate_zone': context['zones'][1] = context['zones'][0].copy()
    if kind == 'duplicate_upgrade': context['available_improvements'].append(context['available_improvements'][0].copy())
    if kind == 'duplicate_change': context['last_changes'] = [{'zone_id': 'air', 'before': 34, 'after': 56}] * 2
    if kind == 'unknown_upgrade': context['available_improvements'][0]['id'] = 'magic'
    if kind == 'oversize_description': context['zones'][0]['description'] = 'x' * 501
    if kind == 'wrong_cost': context['available_improvements'][0]['cost'] = 1
    if kind == 'wrong_gain': context['available_improvements'][0]['gain'] = 100
    if kind == 'wrong_zone': context['available_improvements'][0]['zone_id'] = 'air'
    if kind == 'built_available_overlap': context['built'] = ['bus']
    if kind == 'unknown_field': context['instructions'] = 'DO_NOT_ECHO_SECRET'
    if kind == 'system_history': data['history'] = [{'role': 'system', 'content': 'DO_NOT_ECHO_SECRET'}]
    with TestClient(create_app(settings=Settings())) as client:
        response = client.post('/sandbox/chat', json=data)
    assert response.status_code == 422
    assert 'DO_NOT_ECHO_SECRET' not in response.text


@pytest.mark.parametrize('streaming', [False, True])
def test_sandbox_provider_errors_are_sanitized(streaming):
    def handler(request):
        return httpx2.Response(401, json={'error': {'message': 'PRIVATE_PROVIDER_SECRET'}})
    with TestClient(make_app(handler)) as client:
        response = client.post('/sandbox/chat' + ('/stream' if streaming else ''), json=sandbox_data())
    if streaming:
        assert response.status_code == 200
        events = parse_events(response.text)
        assert len(events) == 1 and events[0][0] == 'error'
        assert events[0][1]['error']['code'] == 'ai_unavailable'
    else:
        assert response.status_code == 503
        assert response.json()['error']['code'] == 'ai_unavailable'
    assert 'PRIVATE_PROVIDER_SECRET' not in response.text and 'test-secret' not in response.text


def test_sandbox_and_astana_streams_keep_reference_and_history_separate_concurrently():
    async def handler(request):
        body = json.loads(request.content)
        marker = body['input'][-1]['content']
        serialized = json.dumps(body, ensure_ascii=False)
        if marker == 'SANDBOX_MARKER':
            assert 'ASTANA_HISTORY' not in serialized and 'reference_dataset' not in serialized
            assert 'sandbox_rules' in serialized
        else:
            assert 'SANDBOX_HISTORY' not in serialized and 'sandbox_rules' not in serialized
            assert 'reference_dataset' in serialized
        await asyncio.sleep(.01)
        report = report_data(); report['answer'] = marker
        return httpx2.Response(200, headers={'content-type': 'text/event-stream'},
                               stream=ByteStream([delta(json.dumps(report)), completed(report)]))
    async def run():
        app = make_app(handler)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                sandbox = sandbox_data(); sandbox['message'] = 'SANDBOX_MARKER'
                sandbox['history'] = [{'role': 'user', 'content': 'SANDBOX_HISTORY'}]
                astana = request_data(); astana['message'] = 'ASTANA_MARKER'
                astana['history'] = [{'role': 'user', 'content': 'ASTANA_HISTORY'}]
                first, second = await asyncio.gather(client.post('/sandbox/chat/stream', json=sandbox),
                                                     client.post('/chat/stream', json=astana))
                assert first.status_code == second.status_code == 200
                assert parse_events(first.text)[-1][1]['answer'] == 'SANDBOX_MARKER'
                assert parse_events(second.text)[-1][1]['answer'] == 'ASTANA_MARKER'
    asyncio.run(run())
