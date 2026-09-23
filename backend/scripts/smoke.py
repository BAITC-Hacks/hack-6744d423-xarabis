import argparse
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

EXAMPLE_DECISIONS = [
    {"measure_id": "M7", "district_id": "nura"},
    {"measure_id": "M8", "district_id": "nura"},
    {"measure_id": "M10", "district_id": "nura"},
    {"measure_id": "M12", "district_id": None},
    {"measure_id": "M5", "district_id": "saryarka"},
]


def request_json(
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    body = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        method=method,
        headers={
            "Accept": "application/json",
            **({"Content-Type": "application/json"} if body is not None else {}),
        },
    )
    try:
        with urlopen(request, timeout=10) as response:  # noqa: S310 - operator URL
            content = response.read()
            return response.status, json.loads(content) if content else None
    except HTTPError as exc:
        content = exc.read()
        details = json.loads(content) if content else None
        raise RuntimeError(f"{method} {path} returned {exc.code}: {details}") from exc
    except URLError as exc:
        raise RuntimeError(f"Cannot reach backend at {base_url}: {exc.reason}") from exc


def run(base_url: str) -> None:
    status, health = request_json(base_url, "GET", "/api/v1/health")
    if status != 200 or health != {"status": "ok"}:
        raise RuntimeError(f"Unexpected health response: {status} {health}")
    status, ready = request_json(base_url, "GET", "/api/v1/ready")
    if status != 200 or ready != {"status": "ready"}:
        raise RuntimeError(f"Unexpected readiness response: {status} {ready}")

    scenario_id: str | None = None
    version: int | None = None
    try:
        status, scenario = request_json(base_url, "POST", "/api/v1/scenarios")
        if status != 201:
            raise RuntimeError(f"Scenario creation returned {status}")
        scenario_id = scenario["id"]
        version = scenario["version"]

        status, scenario = request_json(
            base_url,
            "PUT",
            f"/api/v1/scenarios/{scenario_id}/decisions",
            {"expected_version": version, "decisions": EXAMPLE_DECISIONS},
        )
        version = scenario["version"]
        status, result = request_json(
            base_url,
            "POST",
            f"/api/v1/scenarios/{scenario_id}/calculate",
            {"expected_version": version},
        )
        if status != 200 or result["simulation"]["score_after"] != 56.54:
            raise RuntimeError(f"Unexpected simulation result: {status} {result}")
    finally:
        if scenario_id is not None and version is not None:
            request_json(
                base_url,
                "DELETE",
                f"/api/v1/scenarios/{scenario_id}?expected_version={version}",
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test a running city simulator backend")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    run(args.base_url)
    print("Backend smoke test passed")


if __name__ == "__main__":
    main()
