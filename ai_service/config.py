"""Settings from the service's .env, overridden by the server environment."""
import os
from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, SecretStr


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    api_key: SecretStr | None = Field(default=None, repr=False)
    model: str | None = None
    timeout_seconds: float = Field(default=45, gt=0, le=120, allow_inf_nan=False)
    max_output_tokens: int = Field(default=4000, ge=256, le=16000)

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_key.get_secret_value().strip() and self.model and self.model.strip())

    @classmethod
    def from_env(cls):
        # Read a fixed location without modifying os.environ or searching parent folders.
        values = {**dotenv_values(Path(__file__).resolve().parent / '.env',
                                  encoding='utf-8-sig', interpolate=False),
                  **os.environ}
        return cls(api_key=(values.get('OPENAI_API_KEY') or '').strip() or None,
                   model=(values.get('OPENAI_MODEL') or '').strip() or None,
                   timeout_seconds=values.get('OPENAI_TIMEOUT_SECONDS') or '45',
                   max_output_tokens=values.get('OPENAI_MAX_OUTPUT_TOKENS') or '4000')
