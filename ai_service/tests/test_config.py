"""Configuration must behave the same after deployment to another directory."""
import os

import pytest
from pydantic import ValidationError

from ai_service import config
from ai_service.config import Settings


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    for name in ('OPENAI_API_KEY', 'OPENAI_MODEL', 'OPENAI_TIMEOUT_SECONDS',
                 'OPENAI_MAX_OUTPUT_TOKENS'):
        monkeypatch.delenv(name, raising=False)
    service_dir = tmp_path / 'ai_service'
    service_dir.mkdir()
    monkeypatch.setattr(config, '__file__', str(service_dir / 'config.py'))
    other_dir = tmp_path / 'another-working-directory'
    other_dir.mkdir()
    monkeypatch.chdir(other_dir)
    return service_dir / '.env'


def test_loads_service_env_even_when_started_from_another_directory(env_file):
    # UTF-8 BOM is common in files saved by Windows editors/PowerShell.
    env_file.write_text('OPENAI_API_KEY="test-key#literal"\n'
                        'OPENAI_MODEL="test-model"\n'
                        'OPENAI_TIMEOUT_SECONDS=12\n'
                        'OPENAI_MAX_OUTPUT_TOKENS=800\n', encoding='utf-8-sig')
    settings = Settings.from_env()
    assert settings.configured
    assert settings.api_key.get_secret_value() == 'test-key#literal'
    assert settings.model == 'test-model'
    assert settings.timeout_seconds == 12
    assert settings.max_output_tokens == 800


def test_server_environment_takes_priority_over_file(env_file, monkeypatch):
    env_file.write_text('OPENAI_API_KEY=file-key\nOPENAI_MODEL=file-model\n'
                        'OPENAI_TIMEOUT_SECONDS=12\nOPENAI_MAX_OUTPUT_TOKENS=800\n')
    monkeypatch.setenv('OPENAI_API_KEY', 'server-key')
    monkeypatch.setenv('OPENAI_MODEL', 'server-model')
    monkeypatch.setenv('OPENAI_TIMEOUT_SECONDS', '30')
    monkeypatch.setenv('OPENAI_MAX_OUTPUT_TOKENS', '1000')
    settings = Settings.from_env()
    assert settings.api_key.get_secret_value() == 'server-key'
    assert settings.model == 'server-model'
    assert settings.timeout_seconds == 30
    assert settings.max_output_tokens == 1000


def test_reading_file_does_not_change_process_environment_or_cache_values(env_file):
    env_file.write_text('OPENAI_API_KEY=file-key\nOPENAI_MODEL=first-model\n')
    assert Settings.from_env().model == 'first-model'
    assert 'OPENAI_API_KEY' not in os.environ
    assert 'OPENAI_MODEL' not in os.environ
    env_file.write_text('OPENAI_API_KEY=file-key\nOPENAI_MODEL=second-model\n')
    assert Settings.from_env().model == 'second-model'


@pytest.mark.parametrize('content', [None, '', 'OPENAI_API_KEY=\nOPENAI_MODEL=\n'
                                    'OPENAI_TIMEOUT_SECONDS=\nOPENAI_MAX_OUTPUT_TOKENS=\n'])
def test_missing_or_unfilled_env_keeps_service_unconfigured_with_defaults(env_file, content):
    if content is not None:
        env_file.write_text(content)
    settings = Settings.from_env()
    assert not settings.configured
    assert settings.timeout_seconds == 45
    assert settings.max_output_tokens == 4000


@pytest.mark.parametrize('content', ['OPENAI_TIMEOUT_SECONDS=0',
                                    'OPENAI_TIMEOUT_SECONDS=nan',
                                    'OPENAI_MAX_OUTPUT_TOKENS=255',
                                    'OPENAI_MAX_OUTPUT_TOKENS=hello'])
def test_invalid_file_limits_fail_configuration_validation(env_file, content):
    env_file.write_text(content)
    with pytest.raises(ValidationError):
        Settings.from_env()


def test_does_not_load_env_from_launch_directory(env_file):
    from pathlib import Path
    Path('.env').write_text('OPENAI_API_KEY=wrong-key\nOPENAI_MODEL=wrong-model\n')
    assert not Settings.from_env().configured
