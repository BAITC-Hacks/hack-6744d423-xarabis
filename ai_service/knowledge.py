"""Build per-request model input from a fixed reference and backend snapshot."""
import json
from pathlib import Path

from .schemas import ChatRequest

PACKAGE_DIR = Path(__file__).resolve().parent


def load_knowledge() -> dict:
    return json.loads((PACKAGE_DIR / 'data' / 'city.json').read_text(encoding='utf-8'))


def build_input(request: ChatRequest) -> list[dict]:
    context = {'reference_dataset': load_knowledge(),
               'current_scenario': request.context.model_dump(mode='json')}
    return [
        {'role': 'developer', 'content': json.dumps(context, ensure_ascii=False, allow_nan=False)},
        *[entry.model_dump() for entry in request.history],
        {'role': 'user', 'content': request.message},
    ]


def load_instructions() -> str:
    return (PACKAGE_DIR / 'prompts' / 'consultant.txt').read_text(encoding='utf-8')
