from app.state import get_embedder
from app.db import get_session
from app.models import Chunk




def embed(text: str) -> list[float]:
    emb = get_embedder()
    return emb.encode(text).tolist()


def search_chunks(query: str, top_k: int = 5) -> list[str]:
    query_embedding = embed(query)
    with get_session() as session:
        chunks = Chunk.search(session, query_embedding, top_k)
        return [chunk.content for chunk in chunks]