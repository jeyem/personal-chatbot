import os
import yaml
from pathlib import Path
from typing import Any, Type

from dotenv import dotenv_values
from pydantic import BaseModel, computed_field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


# ── section models ────────────────────────────────────────

class AppConfig(BaseModel):
    name:    str       = "interview"
    host:    str       = "localhost"
    port:    int       = 8000
    origins: list[str] = ["*"]


class DatabaseConfig(BaseModel):
    host:     str = "localhost"
    port:     int = 5432
    name:     str = "chatbot"
    user:     str = "chatbot"
    password: str = ""


class EmbeddingsConfig(BaseModel):
    model:         str  = "sentence-transformers/all-MiniLM-L6-v2"
    dimensions:    int  = 384
    chunk_size:    int  = 150
    chunk_overlap: int  = 20
    top_k:         int  = 3
    offline:       bool = True


class LLMConfig(BaseModel):
    provider:       str = "ollama"
    model:          str = "gemma3:4b"
    base_url:       str = "http://localhost:11434"
    api_token:      str = ""
    timeout:        int = 120
    max_new_tokens: int = 300


# ── yaml source ───────────────────────────────────────────

class YamlSource(PydanticBaseSettingsSource):
    _yaml_data: dict[str, Any] = {}

    def __init__(self, settings_cls: Type[BaseSettings], path: Path | None):
        super().__init__(settings_cls)
        self._path = path
        self._yaml_data = self._load()

    def _load(self) -> dict[str, Any]:
        if not self._path or not self._path.exists():
            return {}
        with open(self._path) as f:
            data = yaml.safe_load(f) or {}
        return {
            "DEBUG":      data.get("debug"),
            "APP":        data.get("app"),
            "DATABASE":   data.get("database"),
            "EMBEDDINGS": data.get("embeddings"),
            "LLM":        data.get("llm"),
        }

    def get_field_value(self, field: Any, field_name: str) -> Any:
        val = self._yaml_data.get(field_name)
        return val, field_name, self.field_is_complex(field)

    def field_is_complex(self, field: Any) -> bool:
        return True

    def __call__(self) -> dict[str, Any]:
        return self._yaml_data


# ── main config ───────────────────────────────────────────

class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    DEBUG:      bool             = False
    ENV:        str              = "development"
    APP:        AppConfig        = AppConfig()
    DATABASE:   DatabaseConfig   = DatabaseConfig()
    EMBEDDINGS: EmbeddingsConfig = EmbeddingsConfig()
    LLM:        LLMConfig        = LLMConfig()

    TRANSFORMERS_OFFLINE: str = "0"
    HF_DATASETS_OFFLINE:  str = "0"
    HF_HUB_OFFLINE:       str = "0"

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        db = self.DATABASE
        return f"postgresql://{db.user}:{db.password}@{db.host}:{db.port}/{db.name}"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        **kwargs: Any,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        env_file_vars = dotenv_values(".env")
        yaml_path = Path(
            env_file_vars.get("CONFIG_PATH")
            or os.environ.get("CONFIG_PATH")
            or "config.yml"
        )

        dotenv = kwargs.get("dotenv_settings") or kwargs.get("env_file_settings")

        sources: list[PydanticBaseSettingsSource] = [
            kwargs["init_settings"],
            kwargs["env_settings"],
            YamlSource(settings_cls, yaml_path),
        ]

        if dotenv is not None:
            sources.insert(2, dotenv)

        return tuple(sources)