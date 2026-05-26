import sys

from sentence_transformers import SentenceTransformer

from app.config import Config

_config: Config | None = None
_embedder: SentenceTransformer | None = None


def set_states(cfg: Config) -> None:
    global _config, _embedder
    _config = cfg
    _embedder = SentenceTransformer(cfg.EMBEDDINGS.model)


def get_config() -> Config:
    if _config is None:
        print("Config is not initialised.", file=sys.stderr)
        sys.exit(1)
    return _config


def get_embedder() -> SentenceTransformer:
    if _embedder is None:
        print("Embedder is not initialised.", file=sys.stderr)
        sys.exit(1)
    return _embedder
