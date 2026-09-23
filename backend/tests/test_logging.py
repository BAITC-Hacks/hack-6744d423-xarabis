import json
import logging

from city_simulator.core.logging import JsonFormatter


def test_json_formatter_emits_structured_context() -> None:
    record = logging.LogRecord(
        name="city_simulator.http",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="request_completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "request-1"
    record.status_code = 200

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["message"] == "request_completed"
    assert payload["request_id"] == "request-1"
    assert payload["status_code"] == 200
