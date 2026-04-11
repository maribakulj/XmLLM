"""Provider profiles — describes a concrete configured provider instance."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from src.app.providers.capabilities import CapabilityMatrix


class RuntimeType(str, Enum):
    LOCAL = "local"
    HUB = "hub"
    API = "api"


class ProviderFamily(str, Enum):
    WORD_BOX_JSON = "word_box_json"
    LINE_BOX_JSON = "line_box_json"
    REGION_LINE_WORD_POLYGON = "region_line_word_polygon"
    TEXT_ONLY = "text_only"


class AuthMode(str, Enum):
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    HF_TOKEN = "hf_token"


class ProviderProfile(BaseModel):
    """A concrete, persisted provider configuration."""

    model_config = ConfigDict(frozen=True)

    provider_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    runtime_type: RuntimeType
    model_id_or_path: str = Field(min_length=1)

    endpoint: str | None = None
    auth_mode: AuthMode = AuthMode.NONE
    auth_secret_ref: str | None = None

    family: ProviderFamily
    capabilities: CapabilityMatrix = Field(default_factory=CapabilityMatrix)

    timeout: int = Field(default=120, gt=0)
    prompt_template: str | None = None

    last_test_status: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
