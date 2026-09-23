import json
from pathlib import Path

import pytest

from ai_service.schemas import ChatRequest

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples'


@pytest.mark.parametrize('filename', ['chat-request.json', 'chat-with-result.json'])
def test_documented_payloads_match_the_actual_http_contract(filename):
    data=json.loads((EXAMPLES/filename).read_text(encoding='utf-8'))
    request=ChatRequest.model_validate(data)
    assert request.model_dump(mode='json')==data


def test_evaluation_questions_are_usable_with_the_real_request_schema():
    cases=json.loads((EXAMPLES/'evaluation.json').read_text(encoding='utf-8'))
    for case in cases:
        data=json.loads((EXAMPLES/case['context']).read_text(encoding='utf-8'))
        data['message']=case['question']
        data['history']=case.get('history',data['history'])
        assert ChatRequest.model_validate(data).message==case['question']
