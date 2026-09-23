import asyncio
import json

import httpx2
import pytest
from fastapi.testclient import TestClient

from ai_service.app import create_app
from ai_service.config import Settings
from ai_service.provider import OpenAIProvider
from ai_service.tests.test_api import openai_response
from ai_service.tests.test_contract import request_data, report_data


def wire(event):
    return ('event: ' + event['type'] + '\ndata: ' + json.dumps(event, ensure_ascii=False) + '\n\n').encode()


def delta(text):
    return {'type': 'response.output_text.delta', 'delta': text, 'item_id': 'msg_test',
            'output_index': 0, 'content_index': 0, 'sequence_number': 1, 'logprobs': []}


def completed(report=None):
    return {'type': 'response.completed', 'sequence_number': 2, 'response': openai_response(report)}


class ByteStream(httpx2.AsyncByteStream):
    def __init__(self, events):
        self.events = events
        self.closed = False

    async def __aiter__(self):
        for event in self.events:
            yield wire(event)

    async def aclose(self):
        self.closed = True


def streaming_app(stream, *, timeout=45, status=200, captured=None):
    def handler(request):
        if captured is not None:
            captured.append(json.loads(request.content))
        if status != 200:
            return httpx2.Response(status, json={'error': {'message': 'PRIVATE_PROVIDER_DETAILS'}})
        return httpx2.Response(200, headers={'content-type': 'text/event-stream'}, stream=stream)
    settings = Settings(api_key='test-secret', model='test-model', timeout_seconds=timeout)
    provider = OpenAIProvider(settings, http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))
    return create_app(settings=settings, provider=provider)


def parse_events(text):
    events = []
    for frame in text.split('\n\n'):
        if frame.startswith(':') or not frame.strip():
            continue
        lines = dict(line.split(': ', 1) for line in frame.splitlines())
        events.append((lines['event'], json.loads(lines['data'])))
    return events


def test_stream_returns_decoded_answer_chunks_then_a_validated_report():
    report = report_data()
    report['answer'] = 'Нура: "школа"\nПарк 🌳 и путь C:\\город'
    raw = json.dumps(report, ensure_ascii=True)
    upstream = ByteStream([delta(raw[i:i+3]) for i in range(0, len(raw), 3)] + [completed(report)])
    sent = []
    with TestClient(streaming_app(upstream, captured=sent)) as client:
        response = client.post('/chat/stream', json=request_data())
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/event-stream')
    assert response.headers['x-accel-buffering'] == 'no'
    events = parse_events(response.text)
    chunks = [data['delta'] for name, data in events if name == 'answer_delta']
    assert len(chunks) > 1
    assert ''.join(chunks) == report['answer']
    assert events[-1] == ('complete', report)
    assert all(name == 'answer_delta' for name, _ in events[:-1])
    assert sent[0]['stream'] is True and sent[0]['store'] is False
    assert sent[0]['text']['format']['strict'] is True
    assert len(sent) == 1 and upstream.closed


@pytest.mark.parametrize('kind,code', [('eof', 'invalid_ai_response'),
    ('incomplete', 'invalid_ai_response'), ('invalid_report', 'invalid_ai_response'),
    ('refusal', 'ai_refusal'), ('failed', 'ai_unavailable'),
    ('bad_delta', 'invalid_ai_response')])
def test_failed_stream_has_one_sanitized_error_and_no_complete_event(kind, code):
    events = [delta('{"answer":"Частичный ответ')]
    if kind == 'incomplete':
        events.append({'type': 'response.incomplete', 'sequence_number': 2,
                       'response': openai_response(status='incomplete')})
    if kind == 'invalid_report':
        invalid = report_data(); del invalid['risks']
        events.append(completed(invalid))
    if kind == 'refusal':
        events.append({'type': 'response.refusal.delta', 'delta': 'PRIVATE_PROVIDER_DETAILS',
                       'item_id': 'msg_test', 'output_index': 0, 'content_index': 0, 'sequence_number': 2})
    if kind == 'failed':
        failed = openai_response(status='failed')
        failed['error'] = {'code': 'server_error', 'message': 'PRIVATE_PROVIDER_DETAILS'}
        events.append({'type': 'response.failed', 'sequence_number': 2, 'response': failed})
    if kind == 'bad_delta':
        events.append(delta(None))
    upstream = ByteStream(events)
    with TestClient(streaming_app(upstream)) as client:
        response = client.post('/chat/stream', json=request_data())
    assert response.status_code == 200
    received = parse_events(response.text)
    assert received[-1][0] == 'error'
    assert received[-1][1]['error']['code'] == code
    assert [name for name, _ in received].count('error') == 1
    assert all(name != 'complete' for name, _ in received)
    assert 'PRIVATE_PROVIDER_DETAILS' not in response.text and 'test-secret' not in response.text
    assert upstream.closed


@pytest.mark.parametrize('status', [401, 429, 500])
def test_upstream_http_error_is_an_sse_error_without_retries(status):
    sent = []
    with TestClient(streaming_app(ByteStream([]), status=status, captured=sent)) as client:
        response = client.post('/chat/stream', json=request_data())
    assert response.status_code == 200
    assert parse_events(response.text)[0][1]['error']['code'] == 'ai_unavailable'
    assert len(sent) == 1
    assert 'PRIVATE_PROVIDER_DETAILS' not in response.text


def test_unconfigured_and_invalid_requests_fail_before_opening_an_sse_response():
    with TestClient(create_app(settings=Settings())) as client:
        response = client.post('/chat/stream', json=request_data())
        assert response.status_code == 503
        assert response.json()['error']['code'] == 'ai_not_configured'
        assert client.post('/chat/stream', json={}).status_code == 422


def test_total_timeout_closes_a_stalled_upstream_stream():
    class Stalled(ByteStream):
        async def __aiter__(self):
            yield wire(delta('{"answer":"Начало'))
            await asyncio.sleep(1)
    upstream = Stalled([])
    with TestClient(streaming_app(upstream, timeout=.05)) as client:
        response = client.post('/chat/stream', json=request_data())
    assert parse_events(response.text)[-1][1]['error']['code'] == 'ai_timeout'
    assert upstream.closed


def test_http_body_reaches_client_before_model_finishes_and_disconnect_closes_model():
    async def run():
        received_delta = asyncio.Event()
        waiting = asyncio.Event()
        class Gated(ByteStream):
            async def __aiter__(self):
                yield wire(delta('{"answer":"Первый текст'))
                waiting.set()
                await asyncio.Event().wait()
        upstream = Gated([])
        app = streaming_app(upstream)
        body_sent = False
        async def receive():
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {'type': 'http.request', 'body': json.dumps(request_data()).encode(), 'more_body': False}
            await received_delta.wait()
            await waiting.wait()
            return {'type': 'http.disconnect'}
        output = []
        async def send(message):
            output.append(message)
            if message['type'] == 'http.response.body' and b'answer_delta' in message.get('body', b''):
                received_delta.set()
        scope = {'type': 'http', 'asgi': {'version': '3.0', 'spec_version': '2.3'},
                 'http_version': '1.1', 'method': 'POST', 'scheme': 'http', 'path': '/chat/stream',
                 'raw_path': b'/chat/stream', 'query_string': b'',
                 'headers': [(b'content-type', b'application/json')],
                 'client': ('127.0.0.1', 1234), 'server': ('test', 80)}
        async with app.router.lifespan_context(app):
            async with asyncio.timeout(2):
                await app(scope, receive, send)
        assert received_delta.is_set()
        assert upstream.closed
        assert not any(b'event: complete' in item.get('body', b'') for item in output)
    asyncio.run(run())
