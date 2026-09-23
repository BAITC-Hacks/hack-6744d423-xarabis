"""District sandbox v2 validates plans and isolates fictional model context."""
import json

import httpx2
import pytest
from fastapi.testclient import TestClient

from ai_service.tests.test_api import make_app, openai_response
from ai_service.tests.test_contract import report_data
from ai_service.tests.test_streaming import ByteStream, completed, delta, parse_events


def districts_data():
    rows = [('esil', 'Есиль', 70, 72, 54), ('almaty', 'Алматы', 28, 52, 48),
            ('saryarka', 'Сарыарка', 38, 24, 58), ('baikonur', 'Байконур', 76, 74, 72),
            ('nura', 'Нура', 26, 42, 26)]
    upgrades = [('bus', 22, 'transport', 24), ('signals', 16, 'transport', 18),
                ('park', 18, 'air', 22), ('filter', 26, 'air', 30),
                ('school', 32, 'education', 42), ('repair', 30, 'transport', 30)]
    return {'message': 'Что улучшить в выбранном районе?', 'history': [], 'context': {
        'rules_version': 'districts-v2', 'city_name': 'Новый Берег', 'quarter': 1,
        'budget': 200, 'score': 50.67, 'selected_district_id': 'nura',
        'districts': [{'id': key, 'name': name, 'description': 'Вымышленный район',
                       'score': (t + a + e) / 3, 'values': {'transport': t, 'air': a, 'education': e},
                       'built': []} for key, name, t, a, e in rows],
        'available_improvements': [{'id': key, 'name': key, 'description': 'Проект',
                                    'cost': cost, 'zone_id': zone, 'gain': gain}
                                   for key, cost, zone, gain in upgrades],
        'selected_improvements': [{'district_id': 'nura', 'improvement_id': 'repair'},
                                  {'district_id': 'almaty', 'improvement_id': 'repair'}],
        'last_changes': [],
    }}


@pytest.mark.parametrize('streaming', [False, True])
def test_v2_routes_send_fixed_rules_and_untrusted_district_snapshot_without_astana(monkeypatch, streaming):
    def forbidden():
        pytest.fail('Fictional v2 must never load the Astana dataset')
    monkeypatch.setattr('ai_service.knowledge.load_knowledge', forbidden)
    sent = []
    report = report_data()
    upstream = ByteStream([delta(json.dumps(report)), completed(report)])
    def handler(request):
        sent.append(json.loads(request.content))
        if streaming:
            return httpx2.Response(200, headers={'content-type': 'text/event-stream'}, stream=upstream)
        return httpx2.Response(200, json=openai_response(report))
    payload = districts_data()
    payload['context']['districts'][0]['description'] = 'UNTRUSTED_MARKER'
    payload['history'] = [{'role': 'assistant', 'content': 'HISTORY_MARKER'}]
    with TestClient(make_app(handler)) as client:
        response = client.post('/sandbox/v2/chat' + ('/stream' if streaming else ''), json=payload)
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
    trusted = body['instructions'] + json.dumps([m for m in body['input'] if m['role'] == 'developer'])
    assert 'UNTRUSTED_MARKER' not in trusted and 'HISTORY_MARKER' not in trusted
    rules = json.loads(body['input'][0]['content'])['sandbox_rules']
    assert rules['rules_version'] == 'districts-v2'
    assert rules['initial_budget'] == 200 and rules['quarter_income'] == 25
    assert rules['max_turns'] == 12 and rules['max_improvements_per_turn'] == 3
    assert rules['construction_limit_per_improvement_per_district'] == 1
    assert rules['initial_values'] == {
        'esil': {'transport': 70, 'air': 72, 'education': 54},
        'almaty': {'transport': 28, 'air': 52, 'education': 48},
        'saryarka': {'transport': 38, 'air': 24, 'education': 58},
        'baikonur': {'transport': 76, 'air': 74, 'education': 72},
        'nura': {'transport': 26, 'air': 42, 'education': 26},
    }
    assert {x['id']: (x['cost'], x['zone_id'], x['gain']) for x in rules['improvements']} == {
        'bus': (22, 'transport', 24), 'signals': (16, 'transport', 18),
        'park': (18, 'air', 22), 'filter': (26, 'air', 30),
        'school': (32, 'education', 42), 'repair': (30, 'transport', 30)}
    assert body['input'][-2]['role'] == 'user'
    assert json.loads(body['input'][-2]['content'])['sandbox_snapshot'] == payload['context']


@pytest.mark.parametrize('path', ['/sandbox/v2/chat', '/sandbox/v2/chat/stream'])
@pytest.mark.parametrize('kind', [
    'version', 'city', 'quarter_bool', 'quarter_zero', 'quarter_high', 'budget_high',
    'score_high', 'selected_district', 'four_districts', 'duplicate_district', 'unknown_district',
    'value_high', 'value_string', 'built_duplicate', 'built_unknown', 'duplicate_plan',
    'built_plan', 'unavailable_plan', 'four_plan', 'unknown_plan_district', 'unknown_plan_upgrade',
    'duplicate_available', 'wrong_cost', 'wrong_gain', 'wrong_zone', 'duplicate_change',
    'unknown_change_district', 'unknown_indicator', 'extra_context', 'extra_values', 'system_history',
])
def test_v2_rejects_invalid_snapshot_before_model(path, kind):
    data = districts_data(); ctx = data['context']
    if kind == 'version': ctx['rules_version'] = 'v1'
    if kind == 'city': ctx['city_name'] = 'Астана'
    if kind == 'quarter_bool': ctx['quarter'] = True
    if kind == 'quarter_zero': ctx['quarter'] = 0
    if kind == 'quarter_high': ctx['quarter'] = 14
    if kind == 'budget_high': ctx['budget'] = 501
    if kind == 'score_high': ctx['score'] = 101
    if kind == 'selected_district': ctx['selected_district_id'] = 'unknown'
    if kind == 'four_districts': ctx['districts'].pop()
    if kind == 'duplicate_district': ctx['districts'][1] = ctx['districts'][0].copy()
    if kind == 'unknown_district': ctx['districts'][0]['id'] = 'unknown'
    if kind == 'value_high': ctx['districts'][0]['values']['air'] = 101
    if kind == 'value_string': ctx['districts'][0]['values']['air'] = '50'
    if kind == 'built_duplicate': ctx['districts'][0]['built'] = ['repair', 'repair']
    if kind == 'built_unknown': ctx['districts'][0]['built'] = ['magic']
    if kind == 'duplicate_plan': ctx['selected_improvements'][1] = ctx['selected_improvements'][0].copy()
    if kind == 'built_plan': ctx['districts'][-1]['built'] = ['repair']
    if kind == 'unavailable_plan': ctx['available_improvements'].pop()
    if kind == 'four_plan': ctx['selected_improvements'] += [
        {'district_id': 'esil', 'improvement_id': 'bus'}, {'district_id': 'esil', 'improvement_id': 'park'}]
    if kind == 'unknown_plan_district': ctx['selected_improvements'][0]['district_id'] = 'unknown'
    if kind == 'unknown_plan_upgrade': ctx['selected_improvements'][0]['improvement_id'] = 'magic'
    if kind == 'duplicate_available': ctx['available_improvements'][1] = ctx['available_improvements'][0].copy()
    if kind == 'wrong_cost': ctx['available_improvements'][-1]['cost'] = 1
    if kind == 'wrong_gain': ctx['available_improvements'][-1]['gain'] = 99
    if kind == 'wrong_zone': ctx['available_improvements'][-1]['zone_id'] = 'air'
    if kind == 'duplicate_change': ctx['last_changes'] = [
        {'district_id': 'esil', 'indicator_id': 'air', 'before': 72, 'after': 94}] * 2
    if kind == 'unknown_change_district': ctx['last_changes'] = [
        {'district_id': 'unknown', 'indicator_id': 'air', 'before': 72, 'after': 94}]
    if kind == 'unknown_indicator': ctx['last_changes'] = [
        {'district_id': 'esil', 'indicator_id': 'T1', 'before': 72, 'after': 94}]
    if kind == 'extra_context': ctx['instructions'] = 'PRIVATE_MARKER'
    if kind == 'extra_values': ctx['districts'][0]['values']['T1'] = 50
    if kind == 'system_history': data['history'] = [{'role': 'system', 'content': 'PRIVATE_MARKER'}]
    def forbidden(request):
        pytest.fail('Invalid context must not reach the model')
    with TestClient(make_app(forbidden)) as client:
        response = client.post(path, json=data)
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'invalid_request'
    assert 'PRIVATE_MARKER' not in response.text


def test_v2_allows_project_built_elsewhere_and_distinct_district_changes():
    payload = districts_data(); ctx = payload['context']
    ctx['quarter'] = 13; ctx['budget'] = 500
    ctx['districts'][0]['built'] = ['repair']
    ctx['last_changes'] = [{'district_id': key, 'indicator_id': indicator, 'before': 0, 'after': 100}
                           for key in ['esil', 'almaty', 'saryarka', 'baikonur', 'nura']
                           for indicator in ['transport', 'air', 'education']]
    with TestClient(make_app(lambda request: httpx2.Response(200, json=openai_response()))) as client:
        response = client.post('/sandbox/v2/chat', json=payload)
    assert response.status_code == 200
