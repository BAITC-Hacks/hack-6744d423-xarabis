"""Build per-request model input from a fixed reference and backend snapshot."""
import json
from pathlib import Path

from .sandbox import sandbox_rules
from .districts import district_rules
from .district_schemas import SandboxV2ChatRequest
from .schemas import ChatRequest, SandboxChatRequest

PACKAGE_DIR = Path(__file__).resolve().parent


def load_knowledge() -> dict:
    return json.loads((PACKAGE_DIR / 'data' / 'city.json').read_text(encoding='utf-8'))


def build_input(request: ChatRequest | SandboxChatRequest | SandboxV2ChatRequest) -> list[dict]:
    if isinstance(request, (SandboxChatRequest, SandboxV2ChatRequest)):
        rules = district_rules() if isinstance(request, SandboxV2ChatRequest) else sandbox_rules()
        return [
            {'role': 'developer', 'content': json.dumps({'sandbox_rules': rules},
                                                       ensure_ascii=False, allow_nan=False)},
            *[entry.model_dump() for entry in request.history],
            {'role': 'user', 'content': json.dumps({'sandbox_snapshot': request.context.model_dump(mode='json')},
                                                  ensure_ascii=False, allow_nan=False)},
            {'role': 'user', 'content': request.message},
        ]
    context = {'reference_dataset': load_knowledge(),
               'current_scenario': request.context.model_dump(mode='json')}
    return [
        {'role': 'developer', 'content': json.dumps(context, ensure_ascii=False, allow_nan=False)},
        *[entry.model_dump() for entry in request.history],
        {'role': 'user', 'content': request.message},
    ]


def load_instructions(request: ChatRequest | SandboxChatRequest | SandboxV2ChatRequest | None = None) -> str:
    if isinstance(request, SandboxV2ChatRequest):
        filename = 'districts.txt'
    else:
        filename = 'sandbox.txt' if isinstance(request, SandboxChatRequest) else 'consultant.txt'
    return (PACKAGE_DIR / 'prompts' / filename).read_text(encoding='utf-8')
