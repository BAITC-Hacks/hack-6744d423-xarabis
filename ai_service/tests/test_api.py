import asyncio
import json

import httpx
import httpx2
import pytest
from fastapi.testclient import TestClient

from ai_service.app import create_app
from ai_service.config import Settings
from ai_service.provider import OpenAIProvider
from ai_service.tests.test_contract import request_data, report_data


def openai_response(report=None, *, status='completed', content=None):
    """HTTP-level Responses fixture, including fields the SDK consumes."""
    return {
        'id':'resp_test', 'object':'response', 'created_at':1, 'status':status,
        'error':None, 'incomplete_details':{'reason':'max_output_tokens'} if status=='incomplete' else None,
        'instructions':None, 'max_output_tokens':4000, 'model':'test-model',
        'output':[{'id':'msg_test','type':'message','status':'completed','role':'assistant',
                   'content':content if content is not None else [{'type':'output_text',
                     'text':json.dumps(report if report is not None else report_data(),ensure_ascii=False),
                     'annotations':[]}]}],
        'parallel_tool_calls':False, 'previous_response_id':None,
        'reasoning':{'effort':None,'summary':None}, 'store':False, 'temperature':1,
        'text':{'format':{'type':'text'}}, 'tool_choice':'auto', 'tools':[], 'top_p':1,
        'truncation':'disabled', 'metadata':{},
        'usage':{'input_tokens':10,'input_tokens_details':{'cached_tokens':0},'output_tokens':10,
                 'output_tokens_details':{'reasoning_tokens':0},'total_tokens':20}}


def make_app(handler, timeout=45):
    settings=Settings(api_key='test-secret',model='test-model',timeout_seconds=timeout)
    client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    provider=OpenAIProvider(settings,http_client=client)
    return create_app(settings=settings,provider=provider)


def test_health_is_local_and_missing_configuration_is_an_explicit_chat_error():
    with TestClient(create_app(settings=Settings())) as client:
        assert client.get('/health').json()=={'status':'ok'}
        response=client.post('/chat',json=request_data())
        assert response.status_code==503
        assert response.json()['error']['code']=='ai_not_configured'


def test_real_http_route_sdk_and_schema_return_the_six_report_fields():
    captured=[]
    def handler(request):
        captured.append(json.loads(request.content))
        return httpx2.Response(200,json=openai_response())
    with TestClient(make_app(handler)) as client:
        data=request_data();data['history']=[{'role':'user','content':'Предыдущий вопрос'}]
        response=client.post('/chat',json=data)
        assert response.status_code==200
        assert response.json()==report_data()
        schema=client.get('/openapi.json').json()
        assert 'ChatRequest' in schema['components']['schemas']
        assert 'ChatResponse' in schema['components']['schemas']
    assert len(captured)==1
    sent=captured[0]
    assert sent['store'] is False
    assert sent['model']=='test-model'
    assert sent['input'][-1]=={'role':'user','content':'Что такое лаг?'}
    assert sent['input'][1]=={'role':'user','content':'Предыдущий вопрос'}
    assert json.loads(sent['input'][0]['content'])['current_scenario']['simulation_result'] is None
    assert sent['text']['format']['type']=='json_schema'
    assert sent['text']['format']['strict'] is True
    assert set(sent['text']['format']['schema']['required'])==set(report_data())
    assert sent['instructions']
    assert 'previous_response_id' not in sent and 'conversation' not in sent


def test_invalid_input_is_rejected_before_any_provider_call_without_echoing_it():
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx2.Response(200,json=openai_response())
    with TestClient(make_app(handler)) as client:
        data=request_data();data['history']=[{'role':'system','content':'DO_NOT_ECHO_SECRET'}]
        response=client.post('/chat',json=data)
        assert response.status_code==422
        assert response.json()['error']['code']=='invalid_request'
        assert 'DO_NOT_ECHO_SECRET' not in response.text
        malformed=client.post('/chat',content='{',headers={'Content-Type':'application/json'})
        assert malformed.status_code==422
        assert malformed.json()['error']['code']=='invalid_request'
    assert calls==[]


@pytest.mark.parametrize('status', [400,401,403,429,500,503])
def test_upstream_failures_are_sanitized_and_never_retried(status):
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx2.Response(status,json={'error':{'message':'LEAK_TEST_SECRET','type':'api_error','code':'bad'}})
    with TestClient(make_app(handler)) as client:
        response=client.post('/chat',json=request_data())
        assert response.status_code==503
        assert response.json()['error']['code']=='ai_unavailable'
        assert 'LEAK_TEST_SECRET' not in response.text and 'test-secret' not in response.text
    assert len(calls)==1


@pytest.mark.parametrize('kind,code', [('refusal','ai_refusal'),('incomplete','invalid_ai_response'),
    ('bad_json','invalid_ai_response'),('missing_field','invalid_ai_response'),
    ('extra_field','invalid_ai_response'),('whitespace','invalid_ai_response'),
    ('empty_output','invalid_ai_response')])
def test_unusable_model_output_never_becomes_a_successful_answer(kind,code):
    body=openai_response()
    if kind=='refusal': body['output'][0]['content']=[{'type':'refusal','refusal':'Refused'}]
    if kind=='incomplete': body['status']='incomplete';body['incomplete_details']={'reason':'max_output_tokens'}
    if kind=='bad_json': body['output'][0]['content'][0]['text']='not JSON'
    if kind in ('missing_field','extra_field','whitespace'):
        report=report_data()
        if kind=='missing_field': del report['risks']
        if kind=='extra_field': report['made_up_score']=99
        if kind=='whitespace': report['answer']=' '
        body=openai_response(report)
    if kind=='empty_output': body['output']=[]
    with TestClient(make_app(lambda request: httpx2.Response(200,json=body))) as client:
        response=client.post('/chat',json=request_data())
        assert response.status_code==502
        assert response.json()['error']['code']==code


def test_network_timeout_returns_504():
    def handler(request): raise httpx2.ReadTimeout('PRIVATE_URL',request=request)
    with TestClient(make_app(handler)) as client:
        response=client.post('/chat',json=request_data())
        assert response.status_code==504
        assert response.json()['error']['code']=='ai_timeout'
        assert 'PRIVATE_URL' not in response.text


def test_total_deadline_stops_a_slow_provider():
    async def handler(request):
        await asyncio.sleep(.15)
        return httpx2.Response(200,json=openai_response())
    with TestClient(make_app(handler,timeout=.02)) as client:
        response=client.post('/chat',json=request_data())
        assert response.status_code==504
        assert response.json()['error']['code']=='ai_timeout'


def test_concurrent_chats_do_not_mix_their_histories():
    async def handler(request):
        sent=json.loads(request.content)
        marker=sent['input'][-1]['content']
        await asyncio.sleep(.01)
        report=report_data();report['answer']=json.dumps(sent['input'][1:],ensure_ascii=False)
        assert marker in ('FIRST_USER','SECOND_USER')
        return httpx2.Response(200,json=openai_response(report))
    async def run():
        app=make_app(handler)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://local') as client:
                a=request_data();a['message']='FIRST_USER';a['history']=[{'role':'user','content':'FIRST_HISTORY'}]
                b=request_data();b['message']='SECOND_USER';b['history']=[{'role':'user','content':'SECOND_HISTORY'}]
                first,second=await asyncio.gather(client.post('/chat',json=a),client.post('/chat',json=b))
                assert first.status_code==second.status_code==200
                assert 'FIRST_HISTORY' in first.json()['answer'] and 'SECOND_HISTORY' not in first.json()['answer']
                assert 'SECOND_HISTORY' in second.json()['answer'] and 'FIRST_HISTORY' not in second.json()['answer']
    asyncio.run(run())


@pytest.mark.parametrize('kind', ['null', 'array', 'plain_text', 'missing_status',
    'null_content', 'missing_content', 'null_content_item', 'null_output_item', 'numeric_text'])
def test_malformed_upstream_envelopes_return_502_instead_of_an_internal_error(kind):
    body=openai_response()
    if kind=='null': body=None
    if kind=='array': body=[]
    if kind=='missing_status': del body['status']
    if kind=='null_content': body['output'][0]['content']=None
    if kind=='missing_content': del body['output'][0]['content']
    if kind=='null_content_item': body['output'][0]['content']=[None]
    if kind=='null_output_item': body['output']=[None]
    if kind=='numeric_text': body['output'][0]['content'][0]['text']=123
    def handler(request):
        return httpx2.Response(200, content='upstream gateway failure' if kind=='plain_text' else json.dumps(body),
                               headers={'content-type':'application/json'})
    with TestClient(make_app(handler),raise_server_exceptions=False) as client:
        response=client.post('/chat',json=request_data())
        assert response.status_code==502
        assert response.json()['error']['code']=='invalid_ai_response'
