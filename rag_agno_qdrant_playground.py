#!/usr/bin/env python3
"""
Agno RAG Playground — Qdrant + PDFReader + OpenAI Chat
- Try multiple chunking strategies
- Try OpenAI embedding variants
- Try vector/keyword/hybrid search (if supported by your Qdrant build)
- Optional reranker (Cohere)
- Interactive chat loop

Usage (examples):
  python rag_agno_qdrant_playground.py \
    --docs ./docs/my_pdfs \
    --collection my_kb \
    --chunk semantic \
    --embedder-id text-embedding-3-small \
    --search hybrid \
    --model-id gpt-4o-mini \
    --max-results 6

  python rag_agno_qdrant_playground.py --help
"""

import os
import time
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

# --- Agno imports (kept identical to docs) ---
from agno.agent import Agent
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.reader.pdf_reader import PDFReader

# Chunking strategies
from agno.knowledge.chunking.fixed import FixedSizeChunking
from agno.knowledge.chunking.semantic import SemanticChunking
from agno.knowledge.chunking.recursive import RecursiveChunking
from agno.knowledge.chunking.document import DocumentChunking
from agno.knowledge.chunking.agentic import AgenticChunking

# Embeddings (OpenAI)
from agno.knowledge.embedder.openai import OpenAIEmbedder

# Optional reranker
try:
    from agno.knowledge.reranker.cohere import CohereReranker
    _HAS_COHERE = True
except Exception:
    _HAS_COHERE = False

# Qdrant + Search type
from agno.vectordb.qdrant import Qdrant
try:
    # Most examples import SearchType from generic search
    from agno.vectordb.search import SearchType
except Exception:
    # Some vector DB pages expose SearchType per-DB; fall back if needed.
    from agno.vectordb.qdrant import SearchType  # type: ignore

# OpenAI chat model
from agno.models.openai import OpenAIChat


console = Console()
app = typer.Typer(add_completion=False)


# --------------------------
# Builders / factory helpers
# --------------------------

def build_chunker(
    strategy: str,
    chunk_size: int = 1000,
    overlap: int = 100,
    similarity_threshold: float = 0.7,
) -> object:
    """Return an Agno chunking strategy instance."""
    s = strategy.lower().strip()
    if s in ("fixed", "fixed_size", "fixed-size"):
        return FixedSizeChunking(chunk_size=chunk_size, overlap=overlap)
    if s in ("semantic", "sem"):
        # similarity_threshold shown in docs; tune if you like
        return SemanticChunking(similarity_threshold=similarity_threshold)
    if s in ("agentic", "sem"):
        # similarity_threshold shown in docs; tune if you like
        return AgenticChunking(max_chunk_size=chunk_size)
    if s in ("recursive", "rec"):
        return RecursiveChunking(chunk_size=chunk_size, overlap=overlap)
    if s in ("document", "doc"):
        # DocumentChunking also supports chunk_size/overlap in docs (defaults shown)
        return DocumentChunking(chunk_size=chunk_size, overlap=overlap)
    raise ValueError(f"Unsupported chunking strategy: {strategy}")


def build_pdf_reader(
    chunker: object,
    split_on_pages: bool = False,
    read_images: bool = False,
) -> PDFReader:
    """Build the PDFReader with the provided chunker."""
    return PDFReader(
        chunking_strategy=chunker,
        split_on_pages=split_on_pages,
        read_images=read_images,
    )


def _dims_for_openai_embedder(model_id: str) -> Optional[int]:
    """Return dimensions matching OpenAI text-embedding-3 models (docs default 1536)."""
    mid = model_id.lower()
    if "text-embedding-3-large" in mid:
        return 3072
    if "text-embedding-3-small" in mid:
        return 1536
    # let the embedder defaults handle it
    return None


def build_embedder(embedder_id: str) -> OpenAIEmbedder:
    dims = _dims_for_openai_embedder(embedder_id)
    if dims:
        return OpenAIEmbedder(id=embedder_id, dimensions=dims)
    return OpenAIEmbedder(id=embedder_id)


def _parse_search_type(search: str) -> Optional[SearchType]:
    s = search.lower().strip()
    if s == "vector":
        return SearchType.vector
    if s == "keyword":
        return SearchType.keyword
    if s == "hybrid":
        return SearchType.hybrid
    return None  # None --> let DB default


def build_qdrant(
    collection: str,
    url: Optional[str],
    # api_key: Optional[str],
    embedder: OpenAIEmbedder,
    search_type: Optional[SearchType] = None,
    use_reranker: bool = False,
) -> Qdrant:
    """Create Qdrant vector DB with robust handling of SearchType + optional reranker."""
    kwargs = dict(collection=collection, url=url, embedder=embedder)

    # Optional reranker
    if use_reranker and _HAS_COHERE and os.getenv("CO_API_KEY"):
        kwargs["reranker"] = CohereReranker()  # model default per docs
    elif use_reranker:
        console.print("[yellow]Reranker requested but Cohere not available or API key missing. Skipping.[/yellow]")

    # SearchType is documented per-DB; Qdrant reference sometimes omits it.
    if search_type is not None:
        try:
            return Qdrant(search_type=search_type, **kwargs)  # type: ignore[arg-type]
        except TypeError:
            console.print("[yellow]Qdrant build lacks 'search_type' support; falling back to vector-only.[/yellow]")
            return Qdrant(**kwargs)

    return Qdrant(**kwargs)


def build_knowledge(
    vector_db: Qdrant,
    max_results: int = 5,
) -> Knowledge:
    """Create a Knowledge instance bound to the vector DB."""
    return Knowledge(
        vector_db=vector_db,
        max_results=max_results,
    )


def ingest_content(
    knowledge: Knowledge,
    pdf_reader: PDFReader,
    sources: Iterable[str],
    skip_if_exists: bool = True,
) -> None:
    """
    Add PDFs by path (file or directory) or URL into Knowledge via the PDFReader.

    This is synchronous for clarity; switch to .add_content_async in batch scenarios.
    """
    for src in sources:
        src = str(src)
        # Heuristic: simple URL-ish check
        if src.startswith("http://") or src.startswith("https://"):
            knowledge.add_content(url=src, reader=pdf_reader, skip_if_exists=skip_if_exists)
        else:
            p = Path(src)
            if p.is_dir():
                knowledge.add_content(path=str(p), reader=pdf_reader, skip_if_exists=skip_if_exists)
            else:
                knowledge.add_content(path=str(p), reader=pdf_reader, skip_if_exists=skip_if_exists)


def build_agent(
    knowledge: Knowledge,
    model_id: str = "gpt-4o-mini",
    search_knowledge: bool = True,
    markdown: bool = True,
    debug_mode: bool = False,
) -> Agent:
    """Create the Agno Agent with OpenAIChat and Knowledge attached."""
    return Agent(
        model=OpenAIChat(id=model_id),
        knowledge=knowledge,
        search_knowledge=search_knowledge,
        markdown=markdown,
        debug_mode=debug_mode,
    )


# --------------------------
# Experiment Helpers (quick)
# --------------------------

def quick_eval(
    knowledge: Knowledge,
    queries: List[str],
    title: str = "Quick Retrieval Eval",
    max_results: Optional[int] = None,
) -> None:
    """
    Simple timing + snippet view for a set of queries against the Knowledge instance.
    Prints a rich table: query, latency, first-hit (truncated).
    """
    table = Table(title=title)
    table.add_column("Query", style="bold")
    table.add_column("Latency (ms)", justify="right")
    table.add_column("Top Snippet", overflow="fold")

    for q in queries:
        t0 = time.perf_counter()
        results = knowledge.search(q, max_results=max_results) if max_results else knowledge.search(q)
        dt_ms = (time.perf_counter() - t0) * 1000.0

        top_snippet = ""
        if results:
            # Each result is a Document; access .content (truncate to keep view tidy)
            top_snippet = (results[0].content or "")[:160].replace("\n", " ") + ("…" if len(results[0].content or "") > 160 else "")
        table.add_row(q, f"{dt_ms:,.0f}", top_snippet)

    console.print(table)


# --------------------------
# Chat loop
# --------------------------

def chat_loop(agent: Agent, user_label: str = "you") -> None:
    """Interactive loop; type 'exit'/'quit' to end."""
    console.print(Panel.fit(f"Agno Agent ready — ask questions! (type 'exit' or 'quit' to stop)", title="RAG Chat", border_style="green"))
    while True:
        message = Prompt.ask(f"[bold cyan]{user_label}[/bold cyan]")
        if message.strip().lower() in ("exit", "quit", "q", "bye"):
            console.print("[green]Bye![/green]")
            break

        console.print(Panel.fit(message, title="You", border_style="cyan"))
        t0 = time.perf_counter()
        run = agent.run(message)  # returns RunOutput; docs show .content
        dt = (time.perf_counter() - t0) * 1000.0

        content = run.content if hasattr(run, "content") else str(run)
        console.print(Panel(Markdown(content), title=f"Agent — {dt:,.0f} ms", border_style="green"))


# --------------------------
# CLI
# --------------------------

@app.command()
def main(
    docs: List[str] = typer.Option(
        ...,
        "--docs",
        help="One or more PDF paths (file/dir) or URLs. Repeat the flag for multiple.",
    ),
    collection: str = typer.Option(
        "recipes",
        help="Qdrant collection name to use/create.",
    ),
    qdrant_url: Optional[str] = typer.Option(
        os.getenv("QDRANT_URL", "http://localhost:6333"),
        help="Qdrant URL (default reads QDRANT_URL env, else http://localhost:6333).",
    ),
    qdrant_api_key: Optional[str] = typer.Option(
        os.getenv("QDRANT_API_KEY"),
        help="Qdrant API key if required (reads QDRANT_API_KEY).",
    ),
    # RAG knobs
    chunk: str = typer.Option(
        "semantic",
        help="Chunking strategy: fixed | semantic | recursive | document",
    ),
    chunk_size: int = typer.Option(
        1000, help="Chunk size for fixed/recursive/document strategies."
    ),
    overlap: int = typer.Option(
        100, help="Chunk overlap for fixed/recursive/document strategies."
    ),
    similarity_threshold: float = typer.Option(
        0.7, help="Similarity threshold for SemanticChunking."
    ),
    embedder_id: str = typer.Option(
        "text-embedding-3-small",
        help="OpenAI embedder model id (e.g., text-embedding-3-small | text-embedding-3-large).",
    ),
    search: str = typer.Option(
        "hybrid",
        help="Search type: vector | keyword | hybrid (hybrid requires DB support).",
    ),
    use_reranker: bool = typer.Option(
        False, help="Enable Cohere reranker if available (requires CO_API_KEY)."
    ),
    max_results: int = typer.Option(
        5, help="Default retrieval size for Knowledge."
    ),
    model_id: str = typer.Option(
        "gpt-4o-mini",
        help="OpenAI chat model id for the Agent (e.g., gpt-4o | gpt-4o-mini).",
    ),
    debug_mode: bool = typer.Option(
        False, help="Set Agent(debug_mode=True) to see detailed logs."
    ),
    # Optional quick eval before chat
    eval_queries: List[str] = typer.Option(
        [],
        help="Optional: repeat --eval-queries 'question' to sanity-check retrieval before chat."
    ),
):
    # Build pipeline pieces
    chunker = build_chunker(
        strategy=chunk,
        chunk_size=chunk_size,
        overlap=overlap,
        similarity_threshold=similarity_threshold,
    )
    reader = build_pdf_reader(chunker)
    embedder = build_embedder(embedder_id)
    search_type = _parse_search_type(search)

    # Create vector DB (Qdrant) and Knowledge
    vector_db = build_qdrant(
        collection=collection,
        url=qdrant_url,
        # api_key=qdrant_api_key,
        embedder=embedder,
        search_type=search_type,
        # use_reranker=use_reranker,
    )
    knowledge = build_knowledge(vector_db, max_results=max_results)

    # Ingest documents
    ingest_content(knowledge, reader, docs, skip_if_exists=True)

    # Optional quick eval
    if eval_queries:
        quick_eval(
            knowledge,
            queries=eval_queries,
            title=f"Eval ({chunk} | {embedder_id} | {search})",
            max_results=max_results,
        )

    # Build agent + chat
    agent = build_agent(
        knowledge=knowledge,
        model_id=model_id,
        search_knowledge=True,
        markdown=True,
        debug_mode=debug_mode,
    )
    chat_loop(agent)


if __name__ == "__main__":
    app()
