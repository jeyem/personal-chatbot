#!/usr/bin/env python3
import os
import re
import argparse
from pathlib import Path

os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"]  = "1"
os.environ["HF_HUB_OFFLINE"]       = "1"

from app.config import Config
from app.state import set_states
from app.db import init_db, get_session
from app.models import Chunk


def clean_text(text: str) -> str:
    text = re.sub(r"#{1,6}\s*", "", text)        # markdown headers
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)  # bold/italic
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)   # code blocks
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)  # links
    text = re.sub(r"[-*•]\s+", "", text)          # bullet points
    text = re.sub(r"\n{3,}", "\n\n", text)        # excess newlines
    text = re.sub(r"[ \t]+", " ", text)           # excess spaces
    return text.strip()


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    words  = text.split()
    chunks = []
    step   = size - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i: i + size])
        if chunk:
            chunks.append(chunk)
    return chunks


def read_file(path: Path) -> str:
    if path.suffix == ".pdf":
        import pypdf
        reader = pypdf.PdfReader(str(path))
        return "\n".join(page.extract_text() for page in reader.pages)
    try:
        return path.read_text()
    except Exception:
        print(f"  ⚠ could not read {path.name}, skipping.")
        return ""


def ingest_file(path: Path, cfg) -> None:
    from app.state import get_embedder
    print(f"→ reading {path.name}")
    text   = read_file(path)
    text   = clean_text(text)
    chunks = chunk_text(text, cfg.EMBEDDINGS.chunk_size, cfg.EMBEDDINGS.chunk_overlap)
    print(f"  {len(chunks)} chunks")

    embedder   = get_embedder()
    embeddings = embedder.encode(chunks)
    print(f"  embedded")

    with get_session() as session:
        for content, emb in zip(chunks, embeddings):
            session.add(Chunk(
                source    = path.name,
                content   = content,
                embedding = emb.tolist(),
            ))
    print(f"  ✓ saved")


parser = argparse.ArgumentParser(prog="ingest.py")
parser.add_argument("-c", "--config", default=Path(__file__).parent / "config.yml", metavar="PATH")

src = parser.add_mutually_exclusive_group(required=True)
src.add_argument("--file", metavar="FILE")
src.add_argument("--dir",  metavar="DIR")

args = parser.parse_args()
cfg  = Config(args.config)

set_states(cfg)
init_db(cfg.DATABASE_URL)

paths = (
    [Path(args.file)] if args.file
    else list(Path(args.dir).glob("**/*.md")) + list(Path(args.dir).glob("**/*.pdf"))
)

if not paths:
    print("No files found.")
    raise SystemExit(1)

for path in paths:
    ingest_file(path, cfg)

print(f"\n✓ {len(paths)} file(s) ingested.")