from dataclasses import dataclass
import yaml
from pathlib import Path


@dataclass
class Database:
    host:     str
    user:     str
    port:     int
    password: str
    name:     str

@dataclass
class Embeddings:
    model:         str
    dimensions:    int
    chunk_size:    int
    chunk_overlap: int
    top_k:         int

@dataclass
class LLM:
    provider:       str  = ""
    model:          str  = ""
    timeout:        int  = 100
    base_url:       str  = ""
    api_token:      str  = ""
    max_new_tokens: int  = 300

@dataclass
class App:
    host:   str = "127.0.0.1"
    port:   int = 8000
    orgins: str = "*"


class Config:

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._raw = self._load_yaml(self._path)

        if not self._raw:
            raise ValueError("Configuration failed to load: config.yml file is empty or missing.")

        # Check for mandatory sections
        required_sections = ["database", "embeddings", "llm", "app"]
        for section in required_sections:
            if section not in self._raw:
                raise KeyError(f"Configuration missing mandatory section: '{section}'. Please check your config.yml.")

        self.DEBUG        = self._raw.get("debug", False)
        self.ENV          = self._raw.get("env", "development")
        self.DATABASE_URL = self.db_url(Database(**self._raw["database"]))
        self.EMBEDDINGS   = Embeddings(**self._raw["embeddings"])
        self.LLM          = LLM(**self._raw["llm"])
        self.APP          = App(**self._raw["app"])
        

    def __repr__(self):
        return f"<Config env={self.ENV} config={self._path}>"
    
    def db_url(self, db) -> str:
        return f"postgresql://{db.user}:{db.password}@{db.host}:{db.port}/{db.name}"
    
    def _load_yaml(self, path: Path) -> dict:
        if not path.exists():
            return {}
        with open(path) as f:
            return yaml.safe_load(f) or {}
        